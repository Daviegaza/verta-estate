"""
Audit log retention and cleanup — configurable retention per event type,
automatic cleanup, cold-storage archiving, and GDPR-compliant purging.

All operations are best-effort and never raise — audit cleanup must never
block the main request path.

Usage:
    from app.services.audit_retention import (
        RetentionConfig,
        AuditRetentionManager,
        run_cleanup_cycle,
    )

    # Configure retention periods
    manager = AuditRetentionManager()
    manager.set_retention("user.*", days=365)   # Keep user events for 1 year
    manager.set_retention("payment.*", days=730) # Keep payments for 2 years
    manager.set_retention("admin.*", days=1825)  # Keep admin actions for 5 years

    # Run cleanup (scheduled via background task):
    await run_cleanup_cycle()
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete, select, text

from app.core.config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("vestra.audit_retention")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_RETENTION_DAYS = 365  # 1 year default
MAX_BATCH_SIZE = 1000          # Max rows to delete per query (prevents locks)
ARCHIVE_BATCH_SIZE = 500       # Max rows per archive file
GDPR_PURGE_EXEMPT_EVENTS: set[str] = {
    "payment.completed",
    "payment.initiated",
    "escrow.completed",
    "dispute.filed",
    "payout.processed",
}

# ---------------------------------------------------------------------------
# Retention configuration
# ---------------------------------------------------------------------------


@dataclass
class RetentionRule:
    """Retention rule for a specific event pattern."""

    pattern: str
    """Glob-style pattern matching audit event types (e.g. 'user.*', 'payment.*')."""

    days: int
    """Number of days to retain audit logs."""

    archive: bool = False
    """If True, archive to cold storage before deletion instead of directly deleting."""

    gdpr_purge: bool = False
    """If True, purge PII from the audit log instead of deleting the entire row."""

    def matches(self, event_type: str) -> bool:
        """Check if this rule matches an event type (simple glob)."""
        pattern = self.pattern
        if pattern.endswith(".*"):
            return event_type.startswith(pattern[:-1])
        if pattern.endswith("*"):
            return event_type.startswith(pattern[:-1])
        return event_type == pattern

    @property
    def cutoff(self) -> datetime:
        """Return the cutoff datetime for this rule."""
        return datetime.now(UTC) - timedelta(days=self.days)


@dataclass
class PendingGDPRDeletion:
    """Tracks a GDPR purging request for a specific user."""

    user_id: int
    requested_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed: bool = False
    preserved_event_types: list[str] = field(default_factory=lambda: list(GDPR_PURGE_EXEMPT_EVENTS))


# ---------------------------------------------------------------------------
# Retention manager
# ---------------------------------------------------------------------------


class AuditRetentionManager:
    """
    Manages audit log retention, cleanup, archiving, and GDPR purging.

    Uses a set of RetentionRule objects to determine how long each event
    type is kept. Cleanup runs are batched to avoid long-running transactions.
    """

    def __init__(self):
        self._rules: list[RetentionRule] = []
        self._gdpr_queue: dict[int, PendingGDPRDeletion] = {}
        self._default_rule = RetentionRule("*", DEFAULT_RETENTION_DAYS)

        # Register sensible defaults
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default retention rules."""
        self._rules = [
            # Critical financial/legal data — longest retention
            RetentionRule("payment.*", days=730, archive=True),
            RetentionRule("escrow.*", days=1825, archive=True),
            RetentionRule("payout.*", days=1825, archive=True),
            RetentionRule("dispute.*", days=1825, archive=True),
            # Security events
            RetentionRule("user.login", days=365),
            RetentionRule("user.logout", days=90),
            RetentionRule("admin.*", days=1825, archive=True),
            # User activity — shorter retention
            RetentionRule("property.*", days=365),
            RetentionRule("subscription.*", days=730),
            RetentionRule("referral.*", days=730),
            RetentionRule("verification.*", days=365),
            # GDPR — purge PII after 90 days for non-critical events
            RetentionRule("user.created", days=90, gdpr_purge=True),
            RetentionRule("user.updated", days=90, gdpr_purge=True),
        ]

    def set_retention(self, pattern: str, days: int, archive: bool = False,
                      gdpr_purge: bool = False) -> None:
        """Add or update a retention rule for an event pattern."""
        # Remove existing rule for this pattern
        self._rules = [r for r in self._rules if r.pattern != pattern]
        self._rules.append(RetentionRule(pattern, days, archive=archive, gdpr_purge=gdpr_purge))
        logger.info(
            '{"event":"retention_rule_set","pattern":"%s","days":%d,"archive":%s,"gdpr_purge":%s}',
            pattern, days, archive, gdpr_purge,
        )

    def get_rule(self, event_type: str) -> RetentionRule:
        """Find the best-matching rule for an event type."""
        for rule in self._rules:
            if rule.matches(event_type):
                return rule
        return self._default_rule

    # -- Cleanup ------------------------------------------------------------

    async def run_cleanup(self, db: AsyncSession) -> dict[str, int]:
        """
        Run a single cleanup cycle — deletes expired audit logs in batches.
        Returns a summary dict: {"deleted": N, "archived": N, "gdpr_purged": N}.
        """
        summary: dict[str, int] = {"deleted": 0, "archived": 0, "gdpr_purged": 0}

        for rule in self._rules:
            if rule.archive:
                archived = await self._archive_and_delete(db, rule)
                summary["archived"] += archived
            elif rule.gdpr_purge:
                purged = await self._gdpr_purge(db, rule)
                summary["gdpr_purged"] += purged
            else:
                deleted = await self._delete_expired(db, rule)
                summary["deleted"] += deleted

        # Process pending GDPR deletion requests
        gdpr_count = await self._process_gdpr_queue(db)
        summary["gdpr_purged"] += gdpr_count

        if sum(summary.values()) > 0:
            logger.info(
                '{"event":"audit_cleanup_complete","deleted":%d,"archived":%d,"gdpr_purged":%d}',
                summary["deleted"], summary["archived"], summary["gdpr_purged"],
            )

        return summary

    async def _delete_expired(self, db: AsyncSession, rule: RetentionRule) -> int:
        """Delete expired audit logs matching a rule. Returns count deleted."""
        total = 0
        cutoff = rule.cutoff

        while True:
            # Build a pattern-matched query using LIKE for prefix patterns
            like_pattern = rule.pattern.replace("*", "%")

            stmt = (
                delete(type("AuditLog", (), {"__tablename__": "audit_logs"}))
                .where(
                    text("action LIKE :pattern"),
                    text("created_at < :cutoff"),
                )
                .execution_options(synchronize_session="fetch")
                .limit(MAX_BATCH_SIZE)
            )

            try:
                result = await db.execute(
                    stmt,
                    {"pattern": like_pattern, "cutoff": cutoff.isoformat()},
                )
                await db.commit()
                deleted = result.rowcount
                total += deleted
                if deleted < MAX_BATCH_SIZE:
                    break
            except Exception as e:
                logger.warning(
                    '{"event":"audit_cleanup_error","pattern":"%s","error":"%s"}',
                    rule.pattern, str(e)[:200],
                )
                await db.rollback()
                break

        if total > 0:
            logger.debug(
                '{"event":"audit_cleanup_deleted","pattern":"%s","count":%d}',
                rule.pattern, total,
            )
        return total

    async def _archive_and_delete(self, db: AsyncSession, rule: RetentionRule) -> int:
        """
        Archive expired audit logs to cold storage (JSON file), then delete.
        Returns count archived+deleted.

        In production, replace the file-based archive with S3/GCS upload:
            import boto3
            s3 = boto3.client('s3')
            s3.upload_file(local_path, 'vestra-audit-archive', key)
        """
        cutoff = rule.cutoff
        like_pattern = rule.pattern.replace("*", "%")
        total = 0

        try:
            while True:
                # Fetch a batch for archiving
                stmt = (
                    select(
                        text("id, user_id, action, resource_type, resource_id, "
                             "details, ip_address, user_agent, correlation_id, created_at")
                    )
                    .select_from(text("audit_logs"))
                    .where(
                        text("action LIKE :pattern AND created_at < :cutoff")
                    )
                    .limit(ARCHIVE_BATCH_SIZE)
                )

                rows = await db.execute(stmt, {"pattern": like_pattern, "cutoff": cutoff.isoformat()})
                batch = rows.mappings().all()
                if not batch:
                    break

                # Archive to local file (production: upload to S3/GCS)
                timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                archive_dir = getattr(settings, "UPLOAD_DIR", "./uploads") + "/audit_archive"
                archive_path = f"{archive_dir}/{rule.pattern}_{timestamp}.jsonl"

                import os
                os.makedirs(archive_dir, exist_ok=True)

                with open(archive_path, "a", encoding="utf-8") as f:
                    for row in batch:
                        f.write(json.dumps(dict(row), default=str) + "\n")

                # Delete the archived rows
                ids = [row["id"] for row in batch]
                delete_stmt = (
                    delete(text("audit_logs"))
                    .where(text("id = ANY(:ids)"))
                )
                await db.execute(delete_stmt, {"ids": ids})
                await db.commit()

                total += len(batch)

                # Small sleep to prevent lock contention
                if len(batch) == ARCHIVE_BATCH_SIZE:
                    await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(
                '{"event":"audit_archive_error","pattern":"%s","error":"%s"}',
                rule.pattern, str(e)[:200],
            )
            await db.rollback()

        if total > 0:
            logger.info(
                '{"event":"audit_archive_completed","pattern":"%s","count":%d}',
                rule.pattern, total,
            )
        return total

    async def _gdpr_purge(self, db: AsyncSession, rule: RetentionRule) -> int:
        """
        GDPR-compliant purging: anonymize PII in audit logs instead of
        deleting the rows entirely (preserves the audit trail without
        personally identifiable information).
        """
        cutoff = rule.cutoff
        like_pattern = rule.pattern.replace("*", "%")
        total = 0

        while True:
            try:
                # Anonymize details (which may contain PII) and set user_id to null
                stmt = text("""
                    UPDATE audit_logs
                    SET details = jsonb_set(
                        COALESCE(details, '{}'::jsonb),
                        '{_gdpr_purged}',
                        'true'::jsonb
                    ) - 'email' - 'phone' - 'name' - 'address' - 'id_number'
                        - 'first_name' - 'last_name' - 'username',
                        user_id = NULL,
                        ip_address = '0.0.0.0',
                        user_agent = '[GDPR PURGED]'
                    WHERE action LIKE :pattern
                      AND created_at < :cutoff
                      AND (details IS NULL OR details->>'_gdpr_purged' IS NULL)
                    LIMIT :limit
                """)
                result = await db.execute(
                    stmt,
                    {"pattern": like_pattern, "cutoff": cutoff.isoformat(), "limit": MAX_BATCH_SIZE},
                )
                await db.commit()
                purged = result.rowcount
                total += purged
                if purged < MAX_BATCH_SIZE:
                    break
            except Exception as e:
                logger.warning(
                    '{"event":"gdpr_purge_error","pattern":"%s","error":"%s"}',
                    rule.pattern, str(e)[:200],
                )
                await db.rollback()
                break

        return total

    # -- GDPR deletion requests ---------------------------------------------

    async def request_gdpr_deletion(self, user_id: int) -> None:
        """Queue a GDPR deletion request for a user (async, best-effort)."""
        if user_id not in self._gdpr_queue:
            self._gdpr_queue[user_id] = PendingGDPRDeletion(user_id=user_id)
            logger.info(
                '{"event":"gdpr_deletion_queued","user_id":%d}',
                user_id,
            )

    async def _process_gdpr_queue(self, db: AsyncSession) -> int:
        """
        Process pending GDPR deletion requests — anonymize audit log entries
        for the specified user, except those in the exempt list.
        """
        total = 0
        processed_users = []

        for user_id, request in list(self._gdpr_queue.items()):
            if request.completed:
                continue

            try:
                # Anonymize non-exempt audit entries for this user
                stmt = text("""
                    UPDATE audit_logs
                    SET details = jsonb_set(
                        COALESCE(details, '{}'::jsonb),
                        '{_gdpr_purged}',
                        'true'::jsonb
                    ) - 'email' - 'phone' - 'name' - 'address' - 'id_number'
                        - 'first_name' - 'last_name' - 'username',
                        ip_address = '0.0.0.0',
                        user_agent = '[GDPR PURGED]'
                    WHERE user_id = :user_id
                      AND action NOT IN :exempt_actions
                      AND (details IS NULL OR details->>'_gdpr_purged' IS NULL)
                """)
                result = await db.execute(
                    stmt,
                    {
                        "user_id": user_id,
                        "exempt_actions": tuple(GDPR_PURGE_EXEMPT_EVENTS),
                    },
                )
                await db.commit()
                total += result.rowcount
                request.completed = True
                processed_users.append(user_id)
                logger.info(
                    '{"event":"gdpr_deletion_completed","user_id":%d,"purged":%d}',
                    user_id, result.rowcount,
                )
            except Exception as e:
                logger.warning(
                    '{"event":"gdpr_deletion_error","user_id":%d,"error":"%s"}',
                    user_id, str(e)[:200],
                )
                await db.rollback()

        # Remove completed requests from the queue
        for uid in processed_users:
            self._gdpr_queue.pop(uid, None)

        return total

    # -- Stats --------------------------------------------------------------

    async def get_retention_stats(self, db: AsyncSession) -> dict:
        """Return retention statistics for the admin dashboard."""
        stats = {}
        for rule in self._rules:
            like_pattern = rule.pattern.replace("*", "%")
            try:
                result = await db.execute(
                    text("""
                        SELECT COUNT(*) as total,
                               MIN(created_at) as oldest,
                               MAX(created_at) as newest
                        FROM audit_logs
                        WHERE action LIKE :pattern
                    """),
                    {"pattern": like_pattern},
                )
                row = result.mappings().first()
                stats[rule.pattern] = {
                    "retention_days": rule.days,
                    "cutoff": rule.cutoff.isoformat(),
                    "total_records": row["total"] if row else 0,
                    "oldest_record": str(row["oldest"]) if row and row["oldest"] else None,
                    "newest_record": str(row["newest"]) if row and row["newest"] else None,
                    "archive": rule.archive,
                    "gdpr_purge": rule.gdpr_purge,
                }
            except Exception:
                stats[rule.pattern] = {"error": "query_failed"}
        return stats


# ---------------------------------------------------------------------------
# Singleton + background task
# ---------------------------------------------------------------------------

_manager: AuditRetentionManager | None = None


def get_retention_manager() -> AuditRetentionManager:
    """Return the application-wide AuditRetentionManager singleton."""
    global _manager
    if _manager is None:
        _manager = AuditRetentionManager()
    return _manager


async def run_cleanup_cycle(db: AsyncSession | None = None) -> dict[str, int]:
    """
    Run a single cleanup cycle. Acquires its own DB session if one is not
    provided. Returns a summary dict.
    """
    manager = get_retention_manager()

    if db is not None:
        return await manager.run_cleanup(db)

    # Create our own session
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        return await manager.run_cleanup(session)


async def scheduled_cleanup(interval_hours: int = 24) -> None:
    """
    Background coroutine that runs cleanup on a schedule.
    Run as a standalone asyncio task at startup:

        asyncio.create_task(scheduled_cleanup(interval_hours=24))
    """
    logger.info(
        '{"event":"audit_cleanup_scheduler_started","interval_hours":%d}',
        interval_hours,
    )
    while True:
        await asyncio.sleep(interval_hours * 3600)
        try:
            result = await run_cleanup_cycle()
            total = sum(result.values())
            if total > 0:
                logger.info(
                    '{"event":"audit_cleanup_scheduled","deleted":%d,"archived":%d,"gdpr_purged":%d}',
                    result.get("deleted", 0), result.get("archived", 0), result.get("gdpr_purged", 0),
                )
        except Exception as e:
            logger.error(
                '{"event":"audit_cleanup_scheduled_error","error":"%s"}',
                str(e)[:200],
            )
