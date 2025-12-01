from datetime import date, datetime, timedelta, timezone, time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func,  or_
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

def validate_flight_business_rules(
    db: Session,
    *,
    flight_number: str,
    flight_date: date,
    route_id: int,
    scheduled_departure_time: time,
    scheduled_arrival_time: time,
    aircraft_registration: str,
    ignore_existing_flight_pk: Optional[tuple[str, date]] = None,
) -> None:
    """
    Central place for flight validation rules used by both create and update.

    Raises HTTPException on any validation failure.
    """

    # Validate route exists ---
    route = db.query(Route).filter(Route.route_id == route_id).first()
    if not route:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Route with id {route_id} does not exist.",
        )

    # Validate aircraft exists and is ACTIVE ---
    aircraft = (
        db.query(Aircraft)
        .filter(Aircraft.registration_number == aircraft_registration)
        .first()
    )
    if not aircraft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Aircraft {aircraft_registration} does not exist.",
        )

    if aircraft.status != AircraftStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Aircraft {aircraft_registration} is not active.",
        )

    # Capacity rule: aircraft capacity vs route approved capacity ---
    if aircraft.capacity > route.approved_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Aircraft capacity ({aircraft.capacity}) exceeds approved "
                f"capacity for route {route.route_id} ({route.approved_capacity})."
            ),
        )

    # Time rules: no flights in the past, arrival after departure ---
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    departure_dt = datetime.combine(flight_date, scheduled_departure_time)
    arrival_dt = datetime.combine(flight_date, scheduled_arrival_time)
    if departure_dt.tzinfo is not None:
        departure_dt = departure_dt.replace(tzinfo=None)
    if arrival_dt.tzinfo is not None:
        arrival_dt = arrival_dt.replace(tzinfo=None)

    if departure_dt < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot schedule a flight whose departure time is in the past.",
        )

    if arrival_dt <= departure_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arrival time must be after departure time.",
        )

    # Aircraft double-booking (overlapping flights) ---
    overlap_query = (
        db.query(Flight)
        .filter(
            Flight.aircraft_registration == aircraft_registration,
            Flight.date == flight_date,
            Flight.scheduled_departure_time < scheduled_arrival_time,
            Flight.scheduled_arrival_time > scheduled_departure_time,
        )
    )

    # When updating an existing flight, ignore that same (flight_number, date)
    if ignore_existing_flight_pk is not None:
        ignore_number, ignore_date = ignore_existing_flight_pk
        overlap_query = overlap_query.filter(
            or_(
                Flight.flight_number != ignore_number,
                Flight.date != ignore_date,
            )
        )

    overlap = overlap_query.first()
    if overlap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Aircraft {aircraft_registration} is already scheduled for "
                f"flight {overlap.flight_number} on {overlap.date} in this time window."
            ),
        )


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
    validate_flight_business_rules(
        db=db,
        flight_number=flight_data.flight_number,
        flight_date=flight_data.date,
        route_id=flight_data.route_id,
        scheduled_departure_time=flight_data.scheduled_departure_time,
        scheduled_arrival_time=flight_data.scheduled_arrival_time,
        aircraft_registration=flight_data.aircraft_registration,
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

    # Compute new (effective) values after update
    new_date = flight_update.date if flight_update.date is not None else flight.date
    new_route_id = (
        flight_update.route_id if flight_update.route_id is not None else flight.route_id
    )
    new_dep_time = (
        flight_update.scheduled_departure_time
        if flight_update.scheduled_departure_time is not None
        else flight.scheduled_departure_time
    )
    new_arr_time = (
        flight_update.scheduled_arrival_time
        if flight_update.scheduled_arrival_time is not None
        else flight.scheduled_arrival_time
    )
    new_aircraft_reg = (
        flight_update.aircraft_registration
        if flight_update.aircraft_registration is not None
        else flight.aircraft_registration
    )

    # If body has a different date, check (flight_number, date) uniqueness
    if new_date != flight.date:
        conflict = (
            db.query(Flight)
            .filter(
                Flight.flight_number == flight.flight_number,
                Flight.date == new_date,
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot change date: flight {flight.flight_number} on "
                    f"{new_date} already exists."
                ),
            )

    # Run shared business-rule validation with the *new* values
    validate_flight_business_rules(
        db=db,
        flight_number=flight.flight_number,
        flight_date=new_date,
        route_id=new_route_id,
        scheduled_departure_time=new_dep_time,
        scheduled_arrival_time=new_arr_time,
        aircraft_registration=new_aircraft_reg,
        ignore_existing_flight_pk=(flight.flight_number, flight.date),
    )

    # If validation passes, apply changes to the entity
    if flight_update.date is not None and flight_update.date != flight.date:
        flight.date = flight_update.date

    if flight_update.route_id is not None:
        flight.route_id = flight_update.route_id

    if flight_update.scheduled_departure_time is not None:
        old_dep = flight.scheduled_departure_time
        new_dep = flight_update.scheduled_departure_time
        flight.scheduled_departure_time = new_dep

        db.query(CrewSchedule).filter(
            CrewSchedule.flight_number == flight.flight_number,
            CrewSchedule.date == flight.date,
            CrewSchedule.scheduled_departure_time == old_dep,
        ).update(
            {CrewSchedule.scheduled_departure_time: new_dep},
            synchronize_session=False,
        )


    if flight_update.scheduled_arrival_time is not None:
        flight.scheduled_arrival_time = flight_update.scheduled_arrival_time

    if flight_update.aircraft_registration is not None:
        flight.aircraft_registration = flight_update.aircraft_registration

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
    flight_date: date = Query(..., description="Date of the flight"),
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_scheduler),
):
    """Delete a flight (and let DB cascade delete its crew assignments)."""

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

    db.delete(flight)
    db.commit()

    return None


# ---------------------------------------------------------------------------
# Assign crew to a flight
# ---------------------------------------------------------------------------


@router.post("/flights/{flight_number}/crew", response_model=CrewAssignmentResponse)
def assign_crew_to_flight(
    flight_number: str,
    flight_date: date,
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
    now = datetime.utcnow()
    today = now.date()
    if flight.date < today or (
        flight.date == today and flight.scheduled_departure_time <= now.time()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign crew to flights in the past.",
        )

    # Fetch all crew objects; ensure they all exist
    unique_emails = sorted(set(payload.crew_emails))
    crew_members = db.query(Crew).filter(Crew.email_id.in_(unique_emails)).all()
    found_emails = {c.email_id for c in crew_members}
    missing = sorted(set(unique_emails) - found_emails)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"These crew emails do not exist: {', '.join(missing)}",
        )
    if not any(c.is_pilot for c in crew_members):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one pilot is required for each flight.",
        )
    for c in crew_members:
        overlap = (
            db.query(CrewSchedule)
            .join(Flight, (CrewSchedule.flight_number == Flight.flight_number)
                        & (CrewSchedule.date == Flight.date))
            .filter(
                CrewSchedule.email_id == c.email_id,
                Flight.date == flight.date,
                Flight.scheduled_departure_time < flight.scheduled_arrival_time,
                Flight.scheduled_arrival_time > flight.scheduled_departure_time,
                Flight.flight_number != flight.flight_number,
            )
            .first()
        )
        if overlap:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Crew member {c.email_id} is already assigned to another flight in this time window.",
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