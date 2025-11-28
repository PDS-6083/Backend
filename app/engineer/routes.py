# app/engineer/routes.py
from datetime import datetime, date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import UserInfo, UserType
from app.database.connection import get_db
from app.database.models import (
    Aircraft,
    AircraftStatus,
    Engineer,
    EngineerMaintenance,
    MaintenanceHistory,
    MaintenanceStatus,
    MaintenanceType,
    AircraftPart,
)

from app.engineer.schemas import (
    EngineerDashboardResponse,
    DashboardAircraftItem,
    DashboardAssignedJobItem,
    EngineerDashboardStats,
    MaintenanceJobSummary,
    MaintenanceJobDetail,
    EngineerInfo,
    JobPartInfo,
    EngineerAircraftSummary,
    MaintenanceHistoryItem,
    AircraftDetail,
    AircraftPartListItem,
)

router = APIRouter(prefix="/api/engineer", tags=["engineer"])


# ----------------------
# RBAC helper
# ----------------------

def require_engineer(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    if current_user.user_type != UserType.ENGINEER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Engineer role required.",
        )
    return current_user


# ----------------------
# Dashboard
# ----------------------

@router.get("/dashboard", response_model=EngineerDashboardResponse)
def engineer_dashboard(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_engineer),
):
    email = current_user.email
    now = datetime.utcnow()
    month_start = date(now.year, now.month, 1)

    # All aircrafts
    aircrafts = db.query(Aircraft).all()
    aircraft_items = [
        DashboardAircraftItem(
            registration_number=a.registration_number,
            status=a.status.value if isinstance(a.status, AircraftStatus) else str(a.status),
        )
        for a in aircrafts
    ]

    # Jobs assigned to this engineer
    assigned_rows = (
        db.query(MaintenanceHistory, EngineerMaintenance)
        .join(EngineerMaintenance, EngineerMaintenance.job_id == MaintenanceHistory.job_id)
        .filter(EngineerMaintenance.engineer_email_id == email)
        .order_by(MaintenanceHistory.checkin_date.desc())
        .all()
    )

    assigned_jobs = [
        DashboardAssignedJobItem(
            job_id=mh.job_id,
            aircraft_registration=mh.registration_number,
            role=em.role,
            checkin_date=mh.checkin_date,
        )
        for mh, em in assigned_rows
    ]

    # Monthly completed jobs (anyone, not just this engineer – matches UI "Monthly Complete Jobs")
    monthly_completed = (
        db.query(MaintenanceHistory)
        .filter(MaintenanceHistory.checkout_date != None)
        .filter(MaintenanceHistory.checkout_date >= month_start)
        .filter(MaintenanceHistory.status == MaintenanceStatus.COMPLETED)
        .count()
    )

    stats = EngineerDashboardStats(monthly_completed_jobs=monthly_completed)

    return EngineerDashboardResponse(
        aircrafts=aircraft_items,
        assigned_jobs=assigned_jobs,
        stats=stats,
    )


# ----------------------
# Maintenance jobs list
# ----------------------

@router.get("/jobs", response_model=List[MaintenanceJobSummary])
def list_my_jobs(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_engineer),
):
    email = current_user.email

    rows = (
        db.query(MaintenanceHistory, EngineerMaintenance)
        .join(EngineerMaintenance, EngineerMaintenance.job_id == MaintenanceHistory.job_id)
        .filter(EngineerMaintenance.engineer_email_id == email)
        .order_by(MaintenanceHistory.checkin_date.desc())
        .all()
    )

    results: List[MaintenanceJobSummary] = []
    for mh, em in rows:
        results.append(
            MaintenanceJobSummary(
                job_id=mh.job_id,
                aircraft_registration=mh.registration_number,
                role=em.role,
                checkin_date=mh.checkin_date,
                checkout_date=mh.checkout_date,
                status=mh.status.value if isinstance(mh.status, MaintenanceStatus) else str(mh.status),
                type=mh.type.value if isinstance(mh.type, MaintenanceType) else str(mh.type),
            )
        )

    return results


# ----------------------
# Maintenance job detail
# ----------------------

@router.get("/jobs/{job_id}", response_model=MaintenanceJobDetail)
def job_detail(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_engineer),
):
    mh = db.query(MaintenanceHistory).filter(MaintenanceHistory.job_id == job_id).first()
    if not mh:
        raise HTTPException(status_code=404, detail="Maintenance job not found.")

    # (Optional) You could also enforce that this engineer is assigned to the job
    # by checking EngineerMaintenance for current_user.email

    # Engineers on this job
    eng_links = (
        db.query(EngineerMaintenance)
        .filter(EngineerMaintenance.job_id == job_id)
        .all()
    )

    engineers: List[EngineerInfo] = []
    for link in eng_links:
        eng = db.query(Engineer).filter(Engineer.email_id == link.engineer_email_id).first()
        if eng:
            engineers.append(
                EngineerInfo(
                    email_id=eng.email_id,
                    name=eng.name,
                    role=link.role,
                )
            )

    # Parts – with current schema, we only know aircraft parts, not job-specific parts.
    # So for now we show all parts for this aircraft.
    part_rows = (
        db.query(AircraftPart)
        .filter(AircraftPart.aircraft_registration == mh.registration_number)
        .all()
    )

    parts: List[JobPartInfo] = [
        JobPartInfo(
            part_number=p.part_number,
            part_manufacturer=p.part_manufacturer,
            model=p.model,
            manufacturing_date=p.manufacturing_date,
        )
        for p in part_rows
    ]

    return MaintenanceJobDetail(
        job_id=mh.job_id,
        aircraft_registration=mh.registration_number,
        checkin_date=mh.checkin_date,
        checkout_date=mh.checkout_date,
        status=mh.status.value if isinstance(mh.status, MaintenanceStatus) else str(mh.status),
        type=mh.type.value if isinstance(mh.type, MaintenanceType) else str(mh.type),
        remarks=mh.remarks,
        engineers=engineers,
        parts=parts,
    )


# ----------------------
# Aircraft list
# ----------------------

@router.get("/aircrafts", response_model=List[EngineerAircraftSummary])
def list_aircrafts(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_engineer),
):
    rows = db.query(Aircraft).all()
    return [
        EngineerAircraftSummary(
            registration_number=a.registration_number,
            aircraft_company=a.aircraft_company,
            model=a.model,
            capacity=a.capacity,
            status=a.status.value if isinstance(a.status, AircraftStatus) else str(a.status),
        )
        for a in rows
    ]


# ----------------------
# Aircraft detail
# ----------------------

@router.get("/aircrafts/{registration_number}", response_model=AircraftDetail)
def aircraft_detail(
    registration_number: str,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_engineer),
):
    a = (
        db.query(Aircraft)
        .filter(Aircraft.registration_number == registration_number)
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Aircraft not found.")

    history_rows = (
        db.query(MaintenanceHistory)
        .filter(MaintenanceHistory.registration_number == registration_number)
        .order_by(MaintenanceHistory.checkin_date.desc())
        .all()
    )

    maintenance_history: List[MaintenanceHistoryItem] = [
        MaintenanceHistoryItem(
            job_id=h.job_id,
            checkin_date=h.checkin_date,
            checkout_date=h.checkout_date,
            type=h.type.value if isinstance(h.type, MaintenanceType) else str(h.type),
            status=h.status.value if isinstance(h.status, MaintenanceStatus) else str(h.status),
        )
        for h in history_rows
    ]

    part_rows = (
        db.query(AircraftPart)
        .filter(AircraftPart.aircraft_registration == registration_number)
        .all()
    )

    parts: List[AircraftPartListItem] = [
        AircraftPartListItem(
            part_number=p.part_number,
            part_manufacturer=p.part_manufacturer,
            model=p.model,
            manufacturing_date=p.manufacturing_date,
        )
        for p in part_rows
    ]

    return AircraftDetail(
        registration_number=a.registration_number,
        aircraft_company=a.aircraft_company,
        model=a.model,
        capacity=a.capacity,
        status=a.status.value if isinstance(a.status, AircraftStatus) else str(a.status),
        maintenance_history=maintenance_history,
        parts=parts,
    )
