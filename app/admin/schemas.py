from enum import Enum
from pydantic import BaseModel


class AircraftStatus(str, Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class AircraftCreateRequest(BaseModel):
    registration_number: str
    aircraft_company: str
    model: str
    capacity: int
    status: AircraftStatus = AircraftStatus.ACTIVE


class AircraftResponse(BaseModel):
    registration_number: str
    aircraft_company: str
    model: str
    capacity: int
    status: str

    class Config:
        from_attributes = True

