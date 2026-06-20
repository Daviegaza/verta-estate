import os
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.core.config import settings
from app.schemas.verification import VerificationRequest, VerificationResponse
from app.models.document import DocumentType, VerificationStatus
from app.models.payment import PaymentPurpose, PaymentStatus
from app.services.verification_service import (
    create_verification_request, run_ai_verification,
    get_verification_by_id, get_verifications_for_property,
    admin_review_verification
)
from app.services.payment_service import (
    initiate_mpesa_payment, get_payment_by_id, VERIFICATION_REPORT_PRICE
)
from app.services.property_service import get_property_by_id

router = APIRouter(prefix="/verify", tags=["Verification"])


@router.post("/request", response_model=dict)
async def request_verification(
    data: VerificationRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate property verification — triggers M-Pesa STK Push for payment.
    Verification runs after payment confirmation.
    """
    prop = await get_property_by_id(db, data.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    payment = await initiate_mpesa_payment(
        db=db,
        user_id=current_user.id,
        phone_number=data.phone_number,
        amount=VERIFICATION_REPORT_PRICE,
        purpose=PaymentPurpose.verification_report,
        reference_id=data.property_id,
        description="Vestra Verify",
    )

    return {
        "message": "STK Push sent. Check your phone and enter M-Pesa PIN.",
        "payment_id": payment.id,
        "amount": payment.amount,
        "currency": payment.currency,
        "checkout_request_id": payment.mpesa_checkout_request_id,
        "status": payment.status.value,
    }


@router.post("/run/{property_id}", response_model=VerificationResponse)
async def run_verification_now(
    property_id: int,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run AI verification directly (for demo / after confirmed payment).
    Runs synchronously so the AI results are immediately available.
    """
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    verification = await create_verification_request(db, property_id, current_user.id)

    # Run AI synchronously so results populate before returning
    try:
        verification = await run_ai_verification(db, verification.id)
    except Exception as e:
        import traceback
        traceback.print_exc()

    return verification


@router.get("/status/{verification_id}", response_model=VerificationResponse)
async def get_verification_status(
    verification_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    v = await get_verification_by_id(db, verification_id)
    if not v:
        raise HTTPException(status_code=404, detail="Verification not found")
    return v


@router.get("/property/{property_id}", response_model=list[VerificationResponse])
async def get_property_verifications(
    property_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all verification records for a property. Requires authentication."""
    # Only the property owner, an agent for the property, or an admin can view verifications
    from app.services.property_service import get_property_by_id
    prop = await get_property_by_id(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if (
        prop.owner_id != current_user.id
        and current_user.role not in ("admin", "super_admin")
        and not (
            hasattr(prop, "agent_id")
            and prop.agent_id == current_user.id
        )
    ):
        raise HTTPException(status_code=403, detail="Not authorized to view verifications for this property")
    return await get_verifications_for_property(db, property_id)


@router.post("/documents/upload")
async def upload_document(
    property_id: int = Form(...),
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document for a property."""
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 10MB.")

    allowed_types = {
        "application/pdf", "image/jpeg", "image/png",
        "image/jpg", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="File type not allowed")

    upload_dir = os.path.join(settings.UPLOAD_DIR, "documents", str(property_id))
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = f"{document_type.value}_{file.filename}".replace(" ", "_")
    file_path = os.path.join(upload_dir, safe_name)

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    from app.models.document import Document
    doc = Document(
        property_id=property_id,
        uploader_id=current_user.id,
        document_type=document_type,
        file_name=file.filename,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return {
        "id": doc.id,
        "file_name": doc.file_name,
        "document_type": doc.document_type.value,
        "file_size": doc.file_size,
        "message": "Document uploaded successfully",
    }


@router.put("/admin/review/{verification_id}", response_model=VerificationResponse)
async def admin_review(
    verification_id: int,
    status: VerificationStatus,
    notes: str = "",
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_review_verification(db, verification_id, admin.id, status, notes)
