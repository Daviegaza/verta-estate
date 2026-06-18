"""
VESTRA TitleChain™ — Blockchain-Verified Property Title History
================================================================
Immutable, cryptographically-verified chain of custody for every property.
Each title event (registration, transfer, verification, encumbrance) is hashed
and linked to the previous event, creating a tamper-proof audit trail.

No actual cryptocurrency needed — uses SHA-256 chaining with public verification.
This is what makes Vestra the world's most trusted property platform.

Problem solved: In Kenya (and many countries), title deeds can be fake,
land can be double-sold, and registry officials can tamper with records.
TitleChain makes every property's history immutable and publicly verifiable.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.redis import cache_get, cache_set

logger = logging.getLogger("vestra")


@dataclass
class TitleBlock:
    """A single block in the title chain — represents one event in a property's history."""
    block_index: int
    timestamp: str
    event_type: str          # registration, transfer, verification, encumbrance, lien, discharge
    property_id: int
    data: dict               # Event-specific data (owner, document refs, etc.)
    previous_hash: str
    hash: str = ""
    validator: str = "VESTRA_AI"  # Who/what validated this event

    def compute_hash(self) -> str:
        """SHA-256 hash of the entire block."""
        raw = json.dumps({
            "index": self.block_index,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "property_id": self.property_id,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "validator": self.validator,
        }, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()


class TitleChain:
    """
    Manages the immutable chain of title for each property.
    The chain lives in the database (title_chain_blocks table) and is cached in Redis.
    """

    GENESIS_HASH = "0" * 64  # All chains start from this

    async def create_genesis_block(
        self, db: AsyncSession, property_id: int, owner_name: str,
        title_deed_number: str, registration_date: str, land_registry_ref: str = "",
    ) -> TitleBlock:
        """Create the first block in a property's title chain — the original registration."""
        block = TitleBlock(
            block_index=0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="registration",
            property_id=property_id,
            data={
                "owner_name": owner_name,
                "title_deed_number": title_deed_number,
                "registration_date": registration_date,
                "land_registry_ref": land_registry_ref,
                "chain_id": f"VTC-{property_id}-{hashlib.sha256(str(property_id).encode()).hexdigest()[:12]}",
            },
            previous_hash=self.GENESIS_HASH,
            validator="LAND_REGISTRY",
        )
        block.hash = block.compute_hash()
        await self._save_block(db, block)
        logger.info('{"event":"title_chain_genesis","property_id":%d,"chain_id":"%s"}',
                    property_id, block.data["chain_id"])
        return block

    async def add_block(
        self, db: AsyncSession, property_id: int, event_type: str,
        data: dict, validator: str = "VESTRA_AI",
    ) -> TitleBlock:
        """Add a new block to a property's title chain."""
        # Get the last block
        last_block = await self.get_latest_block(db, property_id)
        if not last_block:
            raise ValueError(f"No title chain exists for property {property_id}. Create genesis block first.")

        block = TitleBlock(
            block_index=last_block.block_index + 1,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            property_id=property_id,
            data=data,
            previous_hash=last_block.hash,
            validator=validator,
        )
        block.hash = block.compute_hash()
        await self._save_block(db, block)

        # Invalidate Redis cache
        await cache_get(f"vestra:titlechain:{property_id}")  # Force refresh
        await cache_set(
            f"vestra:titlechain:{property_id}:latest",
            {"block_index": block.block_index, "hash": block.hash, "event": event_type},
            ttl=86400,
        )

        logger.info('{"event":"title_chain_block","property_id":%d,"type":"%s","index":%d}',
                    property_id, event_type, block.block_index)
        return block

    async def verify_chain(self, db: AsyncSession, property_id: int) -> dict:
        """
        Verify the entire chain is intact — no blocks tampered with.
        Returns verification status for public display.
        """
        blocks = await self._load_chain(db, property_id)
        if not blocks:
            return {"valid": False, "reason": "No title chain exists", "blocks": 0}

        for i, block in enumerate(blocks):
            # Verify hash
            computed = block.compute_hash()
            if computed != block.hash:
                return {
                    "valid": False,
                    "reason": f"Block {i} hash mismatch — possible tampering",
                    "block_index": i,
                    "expected_hash": computed[:16],
                    "stored_hash": block.hash[:16],
                    "blocks": len(blocks),
                }
            # Verify chain linking
            if i > 0 and block.previous_hash != blocks[i - 1].hash:
                return {
                    "valid": False,
                    "reason": f"Chain broken at block {i} — previous hash doesn't match",
                    "block_index": i,
                    "blocks": len(blocks),
                }

        return {
            "valid": True,
            "reason": "Chain integrity verified — all blocks intact",
            "blocks": len(blocks),
            "last_block_hash": blocks[-1].hash[:16],
            "chain_id": blocks[0].data.get("chain_id", "unknown"),
            "established": blocks[0].timestamp,
            "last_updated": blocks[-1].timestamp,
        }

    async def get_chain_history(self, db: AsyncSession, property_id: int) -> list[dict]:
        """Get the full title chain history for public display."""
        blocks = await self._load_chain(db, property_id)
        return [
            {
                "block": b.block_index,
                "timestamp": b.timestamp,
                "event": b.event_type,
                "data": b.data,
                "hash": b.hash[:16],
                "previous_hash": b.previous_hash[:16],
                "validator": b.validator,
            }
            for b in blocks
        ]

    async def get_latest_block(self, db: AsyncSession, property_id: int) -> Optional[TitleBlock]:
        """Get the latest block in the chain."""
        blocks = await self._load_chain(db, property_id)
        return blocks[-1] if blocks else None

    # ── Database Operations ──────────────────────────────────────────────────

    async def _save_block(self, db: AsyncSession, block: TitleBlock):
        """Persist a block to the database."""
        from app.models.title_chain import TitleChainBlock
        db_block = TitleChainBlock(
            property_id=block.property_id,
            block_index=block.block_index,
            timestamp=block.timestamp,
            event_type=block.event_type,
            data=block.data,
            previous_hash=block.previous_hash,
            block_hash=block.hash,
            validator=block.validator,
        )
        db.add(db_block)
        await db.commit()

    async def _load_chain(self, db: AsyncSession, property_id: int) -> list[TitleBlock]:
        """Load the entire chain for a property from the database."""
        from app.models.title_chain import TitleChainBlock
        result = await db.execute(
            select(TitleChainBlock)
            .where(TitleChainBlock.property_id == property_id)
            .order_by(TitleChainBlock.block_index)
        )
        rows = result.scalars().all()
        return [
            TitleBlock(
                block_index=r.block_index,
                timestamp=r.timestamp,
                event_type=r.event_type,
                property_id=r.property_id,
                data=r.data or {},
                previous_hash=r.previous_hash,
                hash=r.block_hash,
                validator=r.validator or "VESTRA_AI",
            )
            for r in rows
        ]


# Singleton
title_chain = TitleChain()
