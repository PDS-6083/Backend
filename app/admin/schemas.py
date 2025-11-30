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


class AircraftUpdateRequest(BaseModel):
    registration_number: str
    aircraft_company: str | None = None
    model: str | None = None
    capacity: int | None = None
    status: AircraftStatus | None = None


class AircraftDeleteRequest(BaseModel):
    registration_number: str


class AircraftResponse(BaseModel):
    registration_number: str
    aircraft_company: str
    model: str
    capacity: int
    status: str

    class Config:
        from_attributes = True


class RouteCreateRequest(BaseModel):
    source_airport_code: str
    destination_airport_code: str
    approved_capacity: int


class RouteUpdateRequest(BaseModel):
    route_id: int
    source_airport_code: str | None = None
    destination_airport_code: str | None = None
    approved_capacity: int | None = None


class RouteDeleteRequest(BaseModel):
    route_id: int


class RouteResponse(BaseModel):
    route_id: int
    source_airport_code: str
    destination_airport_code: str
    approved_capacity: int

    class Config:
        from_attributes = True


class AirportResponse(BaseModel):
    airport_code: str
    city: str
    state: str | None
    country: str
    airport_name: str

    class Config:
        from_attributes = True

class CrewUpdateRoleRequest(BaseModel):
    is_pilot: bool


class CrewResponse(BaseModel):
    email_id: str
    name: str
    phone: str | None
    is_pilot: bool

    class Config:
        from_attributes = True
