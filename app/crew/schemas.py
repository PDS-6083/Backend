# app/crew/schemas.py
from datetime import date, time
from typing import List, Optional

from pydantic import BaseModel


class CrewFlightSummary(BaseModel):
    """Short info about a flight for list views / dashboard."""
    flight_number: str
    date: date
    scheduled_departure_time: time
    scheduled_arrival_time: time
    duration_minutes: int
    aircraft_registration: str
    source_airport_code: str
    destination_airport_code: str

    class Config:
        from_attributes = True


class NextFlightInfo(BaseModel):
    """Info about the very next upcoming flight."""
    flight_number: str
    date: date
    scheduled_departure_time: time
    scheduled_arrival_time: time
    duration_minutes: int
    aircraft_registration: str
    source_airport_code: str
    destination_airport_code: str
    time_until_departure_minutes: int


class CrewDashboardStats(BaseModel):
    total_hours_completed: float  # in hours
    next_flight: Optional[NextFlightInfo]


class CrewDashboardResponse(BaseModel):
    upcoming_flights: List[CrewFlightSummary]
    stats: CrewDashboardStats


class CrewOnFlight(BaseModel):
    email_id: str
    name: str
    is_pilot: bool
    role: str  # "Pilot" or "Cabin" based on is_pilot


class CrewFlightDetail(BaseModel):
    """Detailed view for a single flight: used in 'Flight Details' page."""
    flight_number: str
    date: date
    scheduled_departure_time: time
    scheduled_arrival_time: time
    duration_minutes: int

    aircraft_registration: str
    aircraft_company: str
    model: str
    capacity: int

    source_airport_code: str
    destination_airport_code: str

    crew: List[CrewOnFlight]


class CrewAircraftSummary(BaseModel):
    """Aircraft that this crew member has flown or is scheduled to fly."""
    registration_number: str
    aircraft_company: str
    model: str
    capacity: int
    status: str  # "active", "maintenance", "retired"

    class Config:
        from_attributes = True
