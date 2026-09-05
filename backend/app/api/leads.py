from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.models import Organization
from app.schemas.leads import OrganizationLeadResponse
from app.api.auth import get_current_user

router = APIRouter(prefix="/leads", tags=["Leads Management"])

@router.get("/{lead_id}", response_model=OrganizationLeadResponse)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Eager load relationships for clean serialization
    lead = db.query(Organization).filter(Organization.id == lead_id)\
        .options(
            joinedload(Organization.website),
            joinedload(Organization.phone_numbers),
            joinedload(Organization.email_addresses),
            joinedload(Organization.social_links)
        ).first()
        
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found."
        )
    return lead

@router.delete("/{lead_id}", status_code=status.HTTP_200_OK)
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    lead = db.query(Organization).filter(Organization.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with ID {lead_id} not found."
        )
        
    db.delete(lead)
    db.commit()
    return {"message": f"Lead '{lead.name}' successfully deleted."}
