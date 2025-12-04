from datetime import date, time
from typing import Optional, List

from pydantic import BaseModel, constr


class FlightBase(BaseModel):
    flight_number: constr(max_length=10)
    route_id: int
    date: date
    scheduled_departure_time: time
    scheduled_arrival_time: time
    aircraft_registration: constr(max_length=20)


class FlightCreateRequest(FlightBase):
    """Data needed for creating a new flight."""
    pass


class FlightUpdateRequest(BaseModel):
    route_id: Optional[int] = None
    date:date
    scheduled_departure_time: Optional[time] = None
    scheduled_arrival_time: Optional[time] = None
    aircraft_registration: Optional[str] = None

class FlightResponse(FlightBase):
    class Config:
        from_attributes = True


class DashboardFlightSummary(BaseModel):
    flight_number: str
    route_id: int
    source_airport_code: str
    destination_airport_code: str
    approved_capacity: int
    date: date
    scheduled_departure_time: time
    scheduled_arrival_time: time
    aircraft_registration: str

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    flights_in_air: int
    weekly_flights: int
    utilization_rate: float
    aircrafts_on_ground: int
    maintenance_aircrafts: int


class DashboardResponse(BaseModel):
    recent_flights: List[DashboardFlightSummary]
    stats: DashboardStats


class CrewSummary(BaseModel):
    email_id: str
    name: str
    phone: Optional[str]
    is_pilot: bool

    class Config:
        from_attributes = True


class CrewAssignmentRequest(BaseModel):
    crew_emails: List[str]


class CrewAssignmentResponse(BaseModel):
    flight_number: str
    crew: List[CrewSummary]

class CrewBasicInfo(BaseModel):
    email_id: str
    name: str
