from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import UserInfo, UserType
from app.database.connection import get_db
from app.database.models import (
    Flight,
    Route,
    Aircraft,
    AircraftStatus,
    Crew,
    CrewSchedule,
)
from app.admin.schemas import AircraftResponse, RouteResponse
from app.scheduler.schemas import (
    FlightCreateRequest,
    FlightUpdateRequest,
    FlightResponse,
    DashboardResponse,
    DashboardStats,
    DashboardFlightSummary,
    CrewSummary,
    CrewAssignmentRequest,
    CrewAssignmentResponse,
)

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


def require_scheduler(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Ensure the current user is a scheduler."""
    if current_user.user_type != UserType.SCHEDULER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only scheduler users can access this endpoint.",
        )
    return current_user


# ---------------------------------------------------------------------------
# Helper lookup endpoints (dropdown data)
# ---------------------------------------------------------------------------


@router.get("/routes", response_model=List[RouteResponse])
def list_routes(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_scheduler),
):
    """Return all routes for scheduler dropdowns."""
    routes = db.query(Route).all()
    return [
        RouteResponse(
            route_id=route.route_id,
            source_airport_code=route.source_airport_code,
            destination_airport_code=route.destination_airport_code,
            approved_capacity=route.approved_capacity,
        )
        for route in routes
    ]


@router.get("/aircrafts", response_model=List[AircraftResponse])
def list_active_aircrafts(
    only_active: bool = True,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_scheduler),
):
    """Return aircraft for scheduler dropdowns (by default only ACTIVE ones)."""
    query = db.query(Aircraft)
    if only_active:
        query = query.filter(Aircraft.status == AircraftStatus.ACTIVE)

    aircrafts = query.all()
    return [
        AircraftResponse(
            registration_number=a.registration_number,
            aircraft_company=a.aircraft_company,
            model=a.model,
            capacity=a.capacity,
            status=a.status.value,
        )
        for a in aircrafts
    ]


@router.get("/crew", response_model=List[CrewSummary])
def list_crew(
    is_pilot: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_scheduler),
):
    """Return crew members; optionally filter by pilot/non-pilot."""
    query = db.query(Crew)
    if is_pilot is not None:
        query = query.filter(Crew.is_pilot == is_pilot)
    crew_members = query.order_by(Crew.name).all()
    return [
        CrewSummary(
            email_id=c.email_id,
            name=c.name,
            phone=c.phone,
            is_pilot=c.is_pilot,
        )
        for c in crew_members
    ]


# ---------------------------------------------------------------------------
# Flight CRUD for scheduler
# ---------------------------------------------------------------------------


@router.post("/flights", response_model=FlightResponse, status_code=status.HTTP_201_CREATED)
def create_flight(
    flight_data: FlightCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_scheduler),
):
    """Create a new flight."""

        # Ensure (flight_number, date) pair is unique
    existing = (
        db.query(Flight)
        .filter(
            Flight.flight_number == flight_data.flight_number,
            Flight.date == flight_data.date,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Flight {flight_data.flight_number} on {flight_data.date} "
                "already exists."
            ),
        )


    # Validate route
    route = db.query(Route).filter(Route.route_id == flight_data.route_id).first()
    if not route:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Route with id {flight_data.route_id} does not exist.",
        )

    # Validate aircraft
    aircraft = db.query(Aircraft).filter(
        Aircraft.registration_number == flight_data.aircraft_registration
    ).first()
    if not aircraft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Aircraft {flight_data.aircraft_registration} does not exist.",
        )

    flight = Flight(
        flight_number=flight_data.flight_number,
        route_id=flight_data.route_id,
        date=flight_data.date,
        scheduled_departure_time=flight_data.scheduled_departure_time,
        scheduled_arrival_time=flight_data.scheduled_arrival_time,
        aircraft_registration=flight_data.aircraft_registration,
    )

    db.add(flight)
    db.commit()
    db.refresh(flight)

    return flight


@router.get("/flights", response_model=List[FlightResponse])
def list_flights(
    date_filter: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_scheduler),
):
    """List flights. Optionally filter by exact date."""
    query = db.query(Flight)
    if date_filter is not None:
        query = query.filter(Flight.date == date_filter)

    flights = query.order_by(Flight.date, Flight.scheduled_departure_time).all()
    return flights


@router.get("/flights/{flight_number}", response_model=FlightResponse)
def get_flight(
    flight_number: str,
    flight_date: date,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_scheduler),
):
    """Get a single flight by flight number."""
    flight = (
        db.query(Flight)
        .filter(
            Flight.flight_number == flight_number,
            Flight.date == flight_date,
        )
        .first()
    )
    if not flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flight {flight_number} not found.",
        )
    return flight

from fastapi import Query
from sqlalchemy.exc import IntegrityError

@router.put("/flights/{flight_number}", response_model=FlightResponse)
def update_flight(
    flight_number: str,
    flight_date: date = Query(..., description="Date of the flight"),
    flight_update: FlightUpdateRequest = ...,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_scheduler),
):
    # 1. Find the existing flight
    flight = (
        db.query(Flight)
        .filter(
            Flight.flight_number == flight_number,
            Flight.date == flight_date,
        )
        .first()
    )
    if not flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flight {flight_number} on {flight_date} not found.",
        )

    # 2. If body has a different date, check for conflicts and then update
    if flight_update.date is not None and flight_update.date != flight.date:
        conflict = (
            db.query(Flight)
            .filter(
                Flight.flight_number == flight.flight_number,
                Flight.date == flight_update.date,
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot change date: flight {flight.flight_number} on "
                    f"{flight_update.date} already exists."
                ),
            )

        # This triggers ON UPDATE CASCADE in MySQL for crew_schedules
        flight.date = flight_update.date

    # 3. Update other fields if present
    if flight_update.route_id is not None:
        flight.route_id = flight_update.route_id

    if flight_update.scheduled_departure_time is not None:
        flight.scheduled_departure_time = flight_update.scheduled_departure_time

    if flight_update.scheduled_arrival_time is not None:
        flight.scheduled_arrival_time = flight_update.scheduled_arrival_time

    if flight_update.aircraft_registration is not None:
        flight.aircraft_registration = flight_update.aircraft_registration

    # 4. Commit safely
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Database constraint error while updating flight: {str(e.orig)}",
        )

    db.refresh(flight)
    return flight


@router.delete("/flights/{flight_number}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flight(
    flight_number: str,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_scheduler),
):
    """Delete a flight (and its crew assignments)."""
    flight = db.query(Flight).filter(Flight.flight_number == flight_number).first()
    if not flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flight {flight_number} not found.",
        )

    db.query(CrewSchedule).filter(
        CrewSchedule.flight_number == flight.flight_number
    ).delete()
    db.delete(flight)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Assign crew to a flight
# ---------------------------------------------------------------------------


@router.post("/flights/{flight_number}/crew", response_model=CrewAssignmentResponse)
def assign_crew_to_flight(
    flight_number: str,
    flight_date: date,  # NEW
    payload: CrewAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_scheduler),
):
    """Assign a list of crew members (by email) to a flight.

    Current behaviour: replaces any existing crew assignments for this flight.
    """

    flight = (
        db.query(Flight)
        .filter(
            Flight.flight_number == flight_number,
            Flight.date == flight_date,
        )
        .first()
    )
    if not flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flight {flight_number} not found.",
        )

    if not payload.crew_emails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="crew_emails cannot be empty.",
        )

    # Fetch all crew objects; ensure they all exist
    crew_members = db.query(Crew).filter(Crew.email_id.in_(payload.crew_emails)).all()
    found_emails = {c.email_id for c in crew_members}
    missing = sorted(set(payload.crew_emails) - found_emails)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"These crew emails do not exist: {', '.join(missing)}",
        )

    # Clear previous assignments for this flight
    db.query(CrewSchedule).filter(
        CrewSchedule.flight_number == flight.flight_number,
        CrewSchedule.date == flight.date,
    ).delete()

    # Insert new assignments
    for c in crew_members:
        schedule = CrewSchedule(
            flight_number=flight.flight_number,
            date=flight.date,  # NEW
            scheduled_departure_time=flight.scheduled_departure_time,
            email_id=c.email_id,
        )
        db.add(schedule)


    db.commit()

    crew_summaries = [
        CrewSummary(
            email_id=c.email_id,
            name=c.name,
            phone=c.phone,
            is_pilot=c.is_pilot,
        )
        for c in crew_members
    ]

    return CrewAssignmentResponse(
        flight_number=flight.flight_number,
        crew=crew_summaries,
    )


@router.get("/flights/{flight_number}/crew", response_model=List[CrewSummary])
def get_flight_crew(
    flight_number: str,
    flight_date: date,  # NEW
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_scheduler),
):
    flight = (
        db.query(Flight)
        .filter(
            Flight.flight_number == flight_number,
            Flight.date == flight_date,
        )
        .first()
    )
    if not flight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flight {flight_number} on {flight_date} not found.",
        )

    schedules = db.query(CrewSchedule).filter(
        CrewSchedule.flight_number == flight.flight_number,
        CrewSchedule.date == flight.date,  # NEW
    ).all()

    if not schedules:
        return []

    crew_emails = [s.email_id for s in schedules]
    crew_members = db.query(Crew).filter(Crew.email_id.in_(crew_emails)).all()

    return [
        CrewSummary(
            email_id=c.email_id,
            name=c.name,
            phone=c.phone,
            is_pilot=c.is_pilot,
        )
        for c in crew_members
    ]


# ---------------------------------------------------------------------------
# Dashboard endpoint
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_model=DashboardResponse)
def scheduler_dashboard(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_scheduler),
):
    """Return data needed for the scheduler dashboard."""

    # 1) Recently scheduled flights (last 10 by date + departure time)
    recent_query = (
        db.query(Flight, Route)
        .join(Route, Flight.route_id == Route.route_id)
        .order_by(Flight.date.desc(), Flight.scheduled_departure_time.desc())
        .limit(10)
    )

    recent_flights: List[DashboardFlightSummary] = []
    for flight, route in recent_query.all():
        recent_flights.append(
            DashboardFlightSummary(
                flight_number=flight.flight_number,
                route_id=route.route_id,
                source_airport_code=route.source_airport_code,
                destination_airport_code=route.destination_airport_code,
                approved_capacity=route.approved_capacity,
                date=flight.date,
                scheduled_departure_time=flight.scheduled_departure_time,
                scheduled_arrival_time=flight.scheduled_arrival_time,
                aircraft_registration=flight.aircraft_registration,
            )
        )

    # 2) Time helpers
    now = datetime.utcnow()
    today = now.date()
    current_time = now.time()

    # 3) Flights in air (today, between departure and arrival time)
    flights_in_air_count = (
        db.query(func.count(Flight.flight_number))
        .filter(Flight.date == today)
        .filter(Flight.scheduled_departure_time <= current_time)
        .filter(Flight.scheduled_arrival_time >= current_time)
        .scalar()
        or 0
    )

    # Distinct aircraft currently in the air
    aircraft_in_air = (
        db.query(Flight.aircraft_registration)
        .filter(Flight.date == today)
        .filter(Flight.scheduled_departure_time <= current_time)
        .filter(Flight.scheduled_arrival_time >= current_time)
        .distinct()
        .all()
    )
    aircraft_in_air_set = {row[0] for row in aircraft_in_air}

    # 4) Weekly flights (Mon–Sun of current week)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=7)
    weekly_flights_count = (
        db.query(func.count(Flight.flight_number))
        .filter(Flight.date >= start_of_week)
        .filter(Flight.date < end_of_week)
        .scalar()
        or 0
    )

    # 5) Utilization rate:
    #    fraction of ACTIVE aircraft that are used at least once this week.
    active_aircraft_query = db.query(Aircraft).filter(
        Aircraft.status == AircraftStatus.ACTIVE
    )
    total_active_aircraft = active_aircraft_query.count()

    aircraft_used_this_week = (
        db.query(Flight.aircraft_registration)
        .filter(Flight.date >= start_of_week)
        .filter(Flight.date < end_of_week)
        .distinct()
        .all()
    )
    used_aircraft_set = {row[0] for row in aircraft_used_this_week}

    utilization_rate = 0.0
    if total_active_aircraft > 0:
        utilization_rate = len(used_aircraft_set) / float(total_active_aircraft)

    # 6) Aircrafts on ground (ACTIVE but not currently in-air)
    aircrafts_on_ground = max(
        total_active_aircraft - len(aircraft_in_air_set), 0
    )

    # 7) Maintenance aircrafts (status = MAINTENANCE)
    maintenance_aircrafts_count = (
        db.query(func.count(Aircraft.registration_number))
        .filter(Aircraft.status == AircraftStatus.MAINTENANCE)
        .scalar()
        or 0
    )

    stats = DashboardStats(
        flights_in_air=flights_in_air_count,
        weekly_flights=weekly_flights_count,
        utilization_rate=utilization_rate,
        aircrafts_on_ground=aircrafts_on_ground,
        maintenance_aircrafts=maintenance_aircrafts_count,
    )

    return DashboardResponse(
        recent_flights=recent_flights,
        stats=stats,
    )