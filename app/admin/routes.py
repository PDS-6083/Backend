from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import UserInfo, UserType
from app.database.connection import get_db
from app.database.models import Aircraft, AircraftStatus
from app.admin.schemas import AircraftCreateRequest, AircraftResponse, AircraftUpdateRequest, AircraftDeleteRequest

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """
    Dependency to ensure only administrators can access the endpoint.
    """
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform this action",
        )
    return current_user


@router.post("/aircraft", response_model=AircraftResponse, status_code=status.HTTP_201_CREATED)
async def add_aircraft(
    aircraft_data: AircraftCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Add a new aircraft to the database.
    Only administrators can perform this action.
    """
    # Check if aircraft with this registration number already exists
    existing_aircraft = db.query(Aircraft).filter(
        Aircraft.registration_number == aircraft_data.registration_number
    ).first()
    
    if existing_aircraft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Aircraft with registration number '{aircraft_data.registration_number}' already exists",
        )
    
    new_aircraft = Aircraft(
        registration_number=aircraft_data.registration_number,
        aircraft_company=aircraft_data.aircraft_company,
        model=aircraft_data.model,
        capacity=aircraft_data.capacity,
        status=AircraftStatus(aircraft_data.status.value),
    )
    
    db.add(new_aircraft)
    db.commit()
    db.refresh(new_aircraft)
    
    return AircraftResponse(
        registration_number=new_aircraft.registration_number,
        aircraft_company=new_aircraft.aircraft_company,
        model=new_aircraft.model,
        capacity=new_aircraft.capacity,
        status=new_aircraft.status.value,
    )


@router.get("/aircraft", response_model=List[AircraftResponse])
async def get_all_aircrafts(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Get all aircrafts from the database.
    Only administrators can access this endpoint.
    """
    aircrafts = db.query(Aircraft).all()
    return [
        AircraftResponse(
            registration_number=aircraft.registration_number,
            aircraft_company=aircraft.aircraft_company,
            model=aircraft.model,
            capacity=aircraft.capacity,
            status=aircraft.status.value,
        )
        for aircraft in aircrafts
    ]


@router.get("/aircraft/{registration_number}", response_model=AircraftResponse)
async def get_aircraft(
    registration_number: str,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Get a specific aircraft by registration number.
    Only administrators can access this endpoint.
    """
    aircraft = db.query(Aircraft).filter(
        Aircraft.registration_number == registration_number
    ).first()
    
    if not aircraft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aircraft with registration number '{registration_number}' not found",
        )
    
    return AircraftResponse(
        registration_number=aircraft.registration_number,
        aircraft_company=aircraft.aircraft_company,
        model=aircraft.model,
        capacity=aircraft.capacity,
        status=aircraft.status.value,
    )


@router.post("/aircraft/update", response_model=AircraftResponse)
async def update_aircraft(
    aircraft_data: AircraftUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Update an existing aircraft in the database.
    Only administrators can perform this action.
    All fields except registration_number are optional - only provided fields will be updated.
    """
    # Find the aircraft
    aircraft = db.query(Aircraft).filter(
        Aircraft.registration_number == aircraft_data.registration_number
    ).first()
    
    if not aircraft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aircraft with registration number '{aircraft_data.registration_number}' not found",
        )
    
    # Update only the fields that are provided
    if aircraft_data.aircraft_company is not None:
        aircraft.aircraft_company = aircraft_data.aircraft_company
    
    if aircraft_data.model is not None:
        aircraft.model = aircraft_data.model
    
    if aircraft_data.capacity is not None:
        aircraft.capacity = aircraft_data.capacity
    
    if aircraft_data.status is not None:
        aircraft.status = AircraftStatus(aircraft_data.status.value)
    
    db.commit()
    db.refresh(aircraft)
    
    return AircraftResponse(
        registration_number=aircraft.registration_number,
        aircraft_company=aircraft.aircraft_company,
        model=aircraft.model,
        capacity=aircraft.capacity,
        status=aircraft.status.value,
    )

#todo check any dependencies on this acft like flghts, creww, etc
@router.post("/aircraft/delete")
async def delete_aircraft(
    aircraft_data: AircraftDeleteRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Delete an aircraft from the database.
    Only administrators can perform this action.
    """
    # Find the aircraft
    aircraft = db.query(Aircraft).filter(
        Aircraft.registration_number == aircraft_data.registration_number
    ).first()
    
    if not aircraft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aircraft with registration number '{aircraft_data.registration_number}' not found",
        )
    
    db.delete(aircraft)
    db.commit()
    
    return {
        "success": True,
        "message": f"Aircraft with registration number '{aircraft_data.registration_number}' has been deleted"
    }

