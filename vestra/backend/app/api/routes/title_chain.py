"""
TitleChain API routes — immutable property title history endpoints.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.core.security import get_current_admin, get_current_user
from app.models.user import UserRole
from app.services.property_service import get_property_by_id
from app.services.title_chain import title_chain

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/title-chain", tags=["TitleChain"])


@router.get("/{property_id}")
async def get_title_chain(
    property_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return the full title chain for a property."""
    # Verify property exists
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    history = await title_chain.get_chain_history(db, property_id)
    return {
        "property_id": property_id,
        "blocks": history,
        "total_blocks": len(history),
    }


@router.post("/{property_id}/genesis", status_code=status.HTTP_201_CREATED)
async def create_genesis_block(
    property_id: int,
    owner_name: str,
    title_number: str,
    land_reference: str,
    county: str,
    size_sqft: float,
    current_user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Create the genesis (first) block in a property's title chain.
    Admin only — this records the original registration.
    """
    # Verify property exists
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    # Check if genesis already exists
    existing = await title_chain.get_latest_block(db, property_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Genesis block already exists for this property. Use /append for new blocks.",
        )

    block = await title_chain.create_genesis_block(
        db,
        property_id=property_id,
        owner_name=owner_name,
        title_number=title_number,
        land_reference=land_reference,
        county=county,
        size_sqft=size_sqft,
        created_by_id=current_user.id,
    )
    return {
        "message": "Genesis block created",
        "block_index": block.block_index,
        "block_hash": block.hash[:16],
        "chain_id": block.data.get("chain_id"),
        "timestamp": block.timestamp,
    }


@router.post("/{property_id}/append", status_code=status.HTTP_201_CREATED)
async def append_block(
    property_id: int,
    new_owner_name: str,
    transaction_type: str,
    transaction_amount: float,
    document_hash: str | None = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Append a new block to the property's title chain.
    Accessible to property owner (seller) or admin.
    """
    # Verify property exists
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    # Authorization: property owner, admin, or super_admin
    owner_id = prop.owner_id if hasattr(prop, 'owner_id') else prop.get("owner_id")
    is_owner = owner_id == current_user.id
    is_admin = current_user.role in (UserRole.admin, UserRole.super_admin)
    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the property owner or admin can append title chain blocks.",
        )

    try:
        block = await title_chain.append_block(
            db,
            property_id=property_id,
            new_owner_name=new_owner_name,
            transaction_type=transaction_type,
            transaction_amount=transaction_amount,
            created_by_id=current_user.id,
            document_hash=document_hash,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return {
        "message": "Block appended to title chain",
        "block_index": block.block_index,
        "block_hash": block.hash[:16],
        "previous_hash": block.previous_hash[:16],
        "timestamp": block.timestamp,
    }


@router.get("/{property_id}/validate")
async def validate_chain(
    property_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Validate the integrity of a property's title chain."""
    result = await title_chain.validate_chain(db, property_id)

    if not result["valid"]:
        return {
            "valid": False,
            "blocks": result["blocks"],
            "first_broken_link": result["first_broken_link"],
            "message": (
                f"Chain integrity BROKEN at block {result['first_broken_link']}."
                if result["first_broken_link"] is not None
                else "No chain exists."
            ),
        }

    return {
        "valid": True,
        "blocks": result["blocks"],
        "first_broken_link": None,
        "message": (
            "Chain integrity verified — all blocks intact and cryptographically linked."
        ),
    }
