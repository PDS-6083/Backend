# app/engineer/schemas.py
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


# ----------------------------
# Dashboard
# ----------------------------

class DashboardAircraftItem(BaseModel):
    registration_number: str
    status: str  # "active", "maintenance", "retired"


class DashboardAssignedJobItem(BaseModel):
    job_id: int
    aircraft_registration: str
    role: str
    checkin_date: datetime


class EngineerDashboardStats(BaseModel):
    monthly_completed_jobs: int


class EngineerDashboardResponse(BaseModel):
    aircrafts: List[DashboardAircraftItem]
    assigned_jobs: List[DashboardAssignedJobItem]
    stats: EngineerDashboardStats


# ----------------------------
# Maintenance jobs list
# ----------------------------

class MaintenanceJobSummary(BaseModel):
    job_id: int
    aircraft_registration: str
    role: str
    checkin_date: datetime
    checkout_date: Optional[datetime]
    status: str   # pending / in_progress / completed / cancelled
    type: str     # routine / inspection / repair / overhaul

    class Config:
        from_attributes = True


# ----------------------------
# Maintenance job detail
# ----------------------------

class EngineerInfo(BaseModel):
    email_id: str
    name: str
    role: str


class JobPartInfo(BaseModel):
    part_number: str
    part_manufacturer: str
    model: str
    manufacturing_date: date


class MaintenanceJobDetail(BaseModel):
    job_id: int
    aircraft_registration: str
    checkin_date: datetime
    checkout_date: Optional[datetime]
    status: str
    type: str
    remarks: Optional[str]

    engineers: List[EngineerInfo]
    parts: List[JobPartInfo]


# ----------------------------
# Aircraft list + detail
# ----------------------------

class EngineerAircraftSummary(BaseModel):
    registration_number: str
    aircraft_company: str
    model: str
    capacity: int
    status: str  # active / maintenance / retired


class MaintenanceHistoryItem(BaseModel):
    job_id: int
    checkin_date: datetime
    checkout_date: Optional[datetime]
    type: str
    status: str


class AircraftPartListItem(BaseModel):
    part_number: str
    part_manufacturer: str
    model: str
    manufacturing_date: date


class AircraftDetail(BaseModel):
    registration_number: str
    aircraft_company: str
    model: str
    capacity: int
    status: str

    maintenance_history: List[MaintenanceHistoryItem]
    parts: List[AircraftPartListItem]
