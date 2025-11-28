# app/crew/routes.py
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import UserInfo, UserType
from app.database.connection import get_db
from app.database.models import (
    Flight,
    Route,
    Aircraft,
    Crew,
    CrewSchedule,
    AircraftStatus,
)
from app.crew.schemas import (
    CrewFlightSummary,
    CrewDashboardResponse,
    CrewDashboardStats,
    NextFlightInfo,
    CrewFlightDetail,
    CrewOnFlight,
    CrewAircraftSummary,
)

router = APIRouter(prefix="/api/crew", tags=["crew"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def require_crew(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Ensure the current user is a crew member."""
    if current_user.user_type != UserType.CREW:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only crew users can access this endpoint.",
        )
    return current_user


def _compute_duration_minutes(flight_date, dep_time, arr_time) -> int:
    """
    Compute duration in minutes between dep and arr.
    If arrival is 'before' departure, assume arrival is next day.
    """
    start = datetime.combine(flight_date, dep_time)
    end = datetime.combine(flight_date, arr_time)
    if end <= start:
        end += timedelta(days=1)
    return int((end - start).total_seconds() // 60)
    

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_model=CrewDashboardResponse)
def crew_dashboard(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_crew),
):
    """
    Crew dashboard:
    - upcoming flights (short list)
    - total hours completed
    - next flight info (for the right tile)
    """
    email = current_user.email
    now = datetime.utcnow()
    today = now.date()
    time_now = now.time()

    # Base query: all flights for this crew (join CrewSchedule -> Flight -> Route)
    base_query = (
        db.query(Flight, Route)
        .join(CrewSchedule, CrewSchedule.flight_number == Flight.flight_number)
        .join(Route, Flight.route_id == Route.route_id)
        .filter(CrewSchedule.email_id == email)
    )

    # Upcoming flights: today (depart >= now) or any future date
    upcoming_query = base_query.filter(
        or_(
            Flight.date > today,
            and_(Flight.date == today, Flight.scheduled_departure_time >= time_now),
        )
    ).order_by(Flight.date, Flight.scheduled_departure_time)

    upcoming_rows = upcoming_query.limit(5).all()

    upcoming_flights: List[CrewFlightSummary] = []
    for flight, route in upcoming_rows:
        duration_minutes = _compute_duration_minutes(
            flight.date,
            flight.scheduled_departure_time,
            flight.scheduled_arrival_time,
        )
        upcoming_flights.append(
            CrewFlightSummary(
                flight_number=flight.flight_number,
                date=flight.date,
                scheduled_departure_time=flight.scheduled_departure_time,
                scheduled_arrival_time=flight.scheduled_arrival_time,
                duration_minutes=duration_minutes,
                aircraft_registration=flight.aircraft_registration,
                source_airport_code=route.source_airport_code,
                destination_airport_code=route.destination_airport_code,
            )
        )

    # Total hours completed = sum of durations for all *past* flights
    past_query = base_query.filter(
        or_(
            Flight.date < today,
            and_(Flight.date == today, Flight.scheduled_arrival_time < time_now),
        )
    )

    total_minutes = 0
    for flight, _route in past_query.all():
        total_minutes += _compute_duration_minutes(
            flight.date,
            flight.scheduled_departure_time,
            flight.scheduled_arrival_time,
        )
    total_hours_completed = total_minutes / 60.0

    # Next flight = earliest upcoming
    next_flight_obj: Optional[NextFlightInfo] = None
    next_row = upcoming_query.first()
    if next_row:
        flight, route = next_row
        duration_minutes = _compute_duration_minutes(
            flight.date,
            flight.scheduled_departure_time,
            flight.scheduled_arrival_time,
        )
        dep_dt = datetime.combine(flight.date, flight.scheduled_departure_time)
        delta_minutes = max(int((dep_dt - now).total_seconds() // 60), 0)

        next_flight_obj = NextFlightInfo(
            flight_number=flight.flight_number,
            date=flight.date,
            scheduled_departure_time=flight.scheduled_departure_time,
            scheduled_arrival_time=flight.scheduled_arrival_time,
            duration_minutes=duration_minutes,
            aircraft_registration=flight.aircraft_registration,
            source_airport_code=route.source_airport_code,
            destination_airport_code=route.destination_airport_code,
            time_until_departure_minutes=delta_minutes,
        )

    stats = CrewDashboardStats(
        total_hours_completed=total_hours_completed,
        next_flight=next_flight_obj,
    )

    return CrewDashboardResponse(
        upcoming_flights=upcoming_flights,
        stats=stats,
    )


# ---------------------------------------------------------------------------
# My Flights list
# ---------------------------------------------------------------------------


@router.get("/my-flights", response_model=List[CrewFlightSummary])
def get_my_flights(
    upcoming_only: bool = True,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_crew),
):
    """
    List flights assigned to the current crew member.
    - upcoming_only=true (default): only future / today upcoming flights
    - upcoming_only=false: all flights (past and future)
    """
    email = current_user.email
    now = datetime.utcnow()
    today = now.date()
    time_now = now.time()

    query = (
        db.query(Flight, Route)
        .join(CrewSchedule, CrewSchedule.flight_number == Flight.flight_number)
        .join(Route, Flight.route_id == Route.route_id)
        .filter(CrewSchedule.email_id == email)
    )

    if upcoming_only:
        query = query.filter(
            or_(
                Flight.date > today,
                and_(
                    Flight.date == today,
                    Flight.scheduled_departure_time >= time_now,
                ),
            )
        )

    rows = query.order_by(Flight.date, Flight.scheduled_departure_time).all()

    results: List[CrewFlightSummary] = []
    for flight, route in rows:
        duration_minutes = _compute_duration_minutes(
            flight.date,
            flight.scheduled_departure_time,
            flight.scheduled_arrival_time,
        )
        results.append(
            CrewFlightSummary(
                flight_number=flight.flight_number,
                date=flight.date,
                scheduled_departure_time=flight.scheduled_departure_time,
                scheduled_arrival_time=flight.scheduled_arrival_time,
                duration_minutes=duration_minutes,
                aircraft_registration=flight.aircraft_registration,
                source_airport_code=route.source_airport_code,
                destination_airport_code=route.destination_airport_code,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Flight details for a crew member
# ---------------------------------------------------------------------------


@router.get("/my-flights/{flight_number}", response_model=CrewFlightDetail)
def get_my_flight_detail(
    flight_number: str,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_crew),
):
    """
    Detailed info about a specific flight that this crew member is assigned to.
    If the crew is not assigned to the flight -> 404.
    """
    email = current_user.email

    row = (
        db.query(Flight, Route, Aircraft)
        .join(Route, Flight.route_id == Route.route_id)
        .join(Aircraft, Flight.aircraft_registration == Aircraft.registration_number)
        .join(CrewSchedule, CrewSchedule.flight_number == Flight.flight_number)
        .filter(CrewSchedule.email_id == email)
        .filter(Flight.flight_number == flight_number)
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flight not found for this crew member.",
        )

    flight, route, aircraft = row

    duration_minutes = _compute_duration_minutes(
        flight.date,
        flight.scheduled_departure_time,
        flight.scheduled_arrival_time,
    )

    # Get all crew on this flight
    schedules = (
        db.query(CrewSchedule)
        .filter(CrewSchedule.flight_number == flight.flight_number)
        .all()
    )
    crew_emails = [s.email_id for s in schedules]

    crew_members = []
    if crew_emails:
        crew_members = (
            db.query(Crew)
            .filter(Crew.email_id.in_(crew_emails))
            .order_by(Crew.name)
            .all()
        )

    crew_list: List[CrewOnFlight] = []
    for c in crew_members:
        role = "Pilot" if c.is_pilot else "Cabin"
        crew_list.append(
            CrewOnFlight(
                email_id=c.email_id,
                name=c.name,
                is_pilot=c.is_pilot,
                role=role,
            )
        )

    return CrewFlightDetail(
        flight_number=flight.flight_number,
        date=flight.date,
        scheduled_departure_time=flight.scheduled_departure_time,
        scheduled_arrival_time=flight.scheduled_arrival_time,
        duration_minutes=duration_minutes,
        aircraft_registration=flight.aircraft_registration,
        aircraft_company=aircraft.aircraft_company,
        model=aircraft.model,
        capacity=aircraft.capacity,
        source_airport_code=route.source_airport_code,
        destination_airport_code=route.destination_airport_code,
        crew=crew_list,
    )


# ---------------------------------------------------------------------------
# Aircrafts used by this crew member
# ---------------------------------------------------------------------------


@router.get("/my-aircrafts", response_model=List[CrewAircraftSummary])
def get_my_aircrafts(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_crew),
):
    """
    Return distinct aircraft that this crew member has flown / will fly.
    Useful for the 'Aircrafts' tab.
    """
    email = current_user.email

    rows = (
        db.query(Aircraft)
        .join(Flight, Flight.aircraft_registration == Aircraft.registration_number)
        .join(CrewSchedule, CrewSchedule.flight_number == Flight.flight_number)
        .filter(CrewSchedule.email_id == email)
        .distinct()
        .all()
    )

    result: List[CrewAircraftSummary] = []
    for a in rows:
        result.append(
            CrewAircraftSummary(
                registration_number=a.registration_number,
                aircraft_company=a.aircraft_company,
                model=a.model,
                capacity=a.capacity,
                status=a.status.value if isinstance(a.status, AircraftStatus) else str(a.status),
            )
        )

    return result
