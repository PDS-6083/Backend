from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.auth.dependencies import get_current_user
from app.auth.schemas import UserInfo, UserType
from app.database.connection import get_db

from app.database.models import Aircraft, AircraftStatus, Route, Airport, Flight, Admin, Crew, Scheduler, Engineer
from app.admin.schemas import (
    AircraftCreateRequest, AircraftResponse, AircraftUpdateRequest, AircraftDeleteRequest,
    RouteCreateRequest, RouteResponse, RouteUpdateRequest, RouteDeleteRequest,
    AirportResponse, DashboardResponse, CrewUpdateRoleRequest, CrewResponse, PopularRouteResponse, UserCreateRequest, UserCreateResponse
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_PASSWORD = "password123"


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




@router.post("/route", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
async def add_route(
    route_data: RouteCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Add a new route to the database.
    Only administrators can perform this action.
    """

    source_airport = db.query(Airport).filter(
        Airport.airport_code == route_data.source_airport_code.upper()
    ).first()
    
    if not source_airport:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source airport with code '{route_data.source_airport_code}' does not exist",
        )
    
    destination_airport = db.query(Airport).filter(
        Airport.airport_code == route_data.destination_airport_code.upper()
    ).first()
    
    if not destination_airport:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Destination airport with code '{route_data.destination_airport_code}' does not exist",
        )
    

    if route_data.source_airport_code.upper() == route_data.destination_airport_code.upper():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination airports cannot be the same",
        )
    
    existing_route = db.query(Route).filter(
        Route.source_airport_code == route_data.source_airport_code.upper(),
        Route.destination_airport_code == route_data.destination_airport_code.upper()
    ).first()
    
    if existing_route:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Route from '{route_data.source_airport_code}' to '{route_data.destination_airport_code}' already exists",
        )
    
    new_route = Route(
        source_airport_code=route_data.source_airport_code.upper(),
        destination_airport_code=route_data.destination_airport_code.upper(),
        approved_capacity=route_data.approved_capacity,
    )
    
    db.add(new_route)
    db.commit()
    db.refresh(new_route)
    
    return RouteResponse(
        route_id=new_route.route_id,
        source_airport_code=new_route.source_airport_code,
        destination_airport_code=new_route.destination_airport_code,
        approved_capacity=new_route.approved_capacity,
    )


@router.get("/route", response_model=List[RouteResponse])
async def get_all_routes(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Get all routes from the database.
    Only administrators can access this endpoint.
    """
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


@router.get("/route/{route_id}", response_model=RouteResponse)
async def get_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Get a specific route by route_id.
    Only administrators can access this endpoint.
    """
    route = db.query(Route).filter(Route.route_id == route_id).first()
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route with ID '{route_id}' not found",
        )
    
    return RouteResponse(
        route_id=route.route_id,
        source_airport_code=route.source_airport_code,
        destination_airport_code=route.destination_airport_code,
        approved_capacity=route.approved_capacity,
    )


@router.post("/route/update", response_model=RouteResponse)
async def update_route(
    route_data: RouteUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Update an existing route in the database.
    Only administrators can perform this action.
    All fields except route_id are optional - only provided fields will be updated.
    """
    route = db.query(Route).filter(Route.route_id == route_data.route_id).first()
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route with ID '{route_data.route_id}' not found",
        )
    
    if route_data.source_airport_code is not None:
        source_airport = db.query(Airport).filter(
            Airport.airport_code == route_data.source_airport_code.upper()
        ).first()
        
        if not source_airport:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Source airport with code '{route_data.source_airport_code}' does not exist",
            )
    
    if route_data.destination_airport_code is not None:
        destination_airport = db.query(Airport).filter(
            Airport.airport_code == route_data.destination_airport_code.upper()
        ).first()
        
        if not destination_airport:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Destination airport with code '{route_data.destination_airport_code}' does not exist",
            )
    
    source = route_data.source_airport_code.upper() if route_data.source_airport_code else route.source_airport_code
    destination = route_data.destination_airport_code.upper() if route_data.destination_airport_code else route.destination_airport_code
    
    if source == destination:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination airports cannot be the same",
        )
    
    if route_data.source_airport_code is not None or route_data.destination_airport_code is not None:
        existing_route = db.query(Route).filter(
            Route.source_airport_code == source,
            Route.destination_airport_code == destination,
            Route.route_id != route_data.route_id
        ).first()
        
        if existing_route:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Route from '{source}' to '{destination}' already exists",
            )
    
    if route_data.source_airport_code is not None:
        route.source_airport_code = route_data.source_airport_code.upper()
    
    if route_data.destination_airport_code is not None:
        route.destination_airport_code = route_data.destination_airport_code.upper()
    
    if route_data.approved_capacity is not None:
        route.approved_capacity = route_data.approved_capacity
    
    db.commit()
    db.refresh(route)
    
    return RouteResponse(
        route_id=route.route_id,
        source_airport_code=route.source_airport_code,
        destination_airport_code=route.destination_airport_code,
        approved_capacity=route.approved_capacity,
    )


@router.post("/route/delete")
async def delete_route(
    route_data: RouteDeleteRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Delete a route from the database.
    Only administrators can perform this action.
    """
    route = db.query(Route).filter(Route.route_id == route_data.route_id).first()
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route with ID '{route_data.route_id}' not found",
        )
    
    db.delete(route)
    db.commit()
    
    return {
        "success": True,
        "message": f"Route with ID '{route_data.route_id}' has been deleted"
    }




@router.get("/airport", response_model=List[AirportResponse])
async def get_all_airports(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Get all airports from the database.
    Only administrators can access this endpoint.
    """
    airports = db.query(Airport).all()
    return [
        AirportResponse(
            airport_code=airport.airport_code,
            city=airport.city,
            state=airport.state,
            country=airport.country,
            airport_name=airport.airport_name,
        )
        for airport in airports
    ]


@router.get("/airport/{airport_code}", response_model=AirportResponse)
async def get_airport_by_code(
    airport_code: str,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Get a specific airport by airport code.
    Only administrators can access this endpoint.
    """
    airport = db.query(Airport).filter(
        Airport.airport_code == airport_code.upper()
    ).first()
    
    if not airport:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Airport with code '{airport_code}' not found",
        )
    
    return AirportResponse(
        airport_code=airport.airport_code,
        city=airport.city,
        state=airport.state,
        country=airport.country,
        airport_name=airport.airport_name,
    )


@router.get("/airport-codes", response_model=List[str])
async def get_all_airport_codes(
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Get all airport codes from the database.
    Only administrators can access this endpoint.
    Returns a list of airport codes only.
    """
    airports = db.query(Airport).all()
    return [airport.airport_code for airport in airports]


@router.patch("/crew/{email_id}/role", response_model=CrewResponse)
async def update_crew_role(
    email_id: str,
    payload: CrewUpdateRoleRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Admin sets whether a crew member is a pilot (is_pilot=true) or cabin crew (is_pilot=false).
    """

    crew = db.query(Crew).filter(Crew.email_id == email_id).first()
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crew member not found.",
        )

    crew.is_pilot = payload.is_pilot
    db.commit()
    db.refresh(crew)

    return CrewResponse(
        email_id=crew.email_id,
        name=crew.name,
        phone=crew.phone,
        is_pilot=crew.is_pilot,
    )

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(db: Session = Depends(get_db),current_user: UserInfo = Depends(require_admin),):
    """
    Get dashboard data for administrators.
    Returns:
    - 7 most popular routes (sorted by approved capacity)
    - Count of flights in air (flights scheduled for today or future)
    - Count of aircraft in maintenance
    Only administrators can access this endpoint.
    """

    popular_routes = db.query(Route).order_by(desc(Route.approved_capacity)).limit(7).all()
    
    most_popular_routes = [
        PopularRouteResponse(
            route_id=route.route_id,
            source_airport_code=route.source_airport_code,
            destination_airport_code=route.destination_airport_code,
            approved_capacity=route.approved_capacity,
        )
        for route in popular_routes
    ]
    

    today = date.today()
    flights_in_air = db.query(Aircraft).filter(Aircraft.status == AircraftStatus.ACTIVE).count()
    
    aircraft_in_maintenance = db.query(Aircraft).filter(
        Aircraft.status == AircraftStatus.MAINTENANCE
    ).count()
    
    return DashboardResponse(
        most_popular_routes=most_popular_routes,
        flights_in_air=flights_in_air,
        aircraft_in_maintenance=aircraft_in_maintenance,
    )


@router.post("/user", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(require_admin),
):
    """
    Create a new user with a default password.
    Only administrators can perform this action.
    For crew users, is_pilot field is required to differentiate between pilots and cabin crew.
    """
    user_type = user_data.user_type.lower()
    
    # Validate user type
    valid_user_types = ["admin", "crew", "scheduler", "engineer"]
    if user_type not in valid_user_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user_type. Must be one of: {', '.join(valid_user_types)}",
        )
    
    # For crew, is_pilot is required
    if user_type == "crew" and user_data.is_pilot is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="is_pilot field is required for crew users",
        )
    
    # For non-crew users, is_pilot should not be provided
    if user_type != "crew" and user_data.is_pilot is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="is_pilot field is only valid for crew users",
        )
    
    # Map user type to model
    model_map = {
        "admin": Admin,
        "crew": Crew,
        "scheduler": Scheduler,
        "engineer": Engineer,
    }
    model = model_map[user_type]
    
    # Check if user already exists
    existing_user = db.query(model).filter(model.email_id == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{user_type} with email '{user_data.email}' already exists",
        )
    
    # Hash the default password
    hashed_password = pwd_context.hash(DEFAULT_PASSWORD)
    
    # Create user based on type
    if user_type == "crew":
        new_user = model(
            email_id=user_data.email,
            name=user_data.name,
            phone=user_data.phone,
            password_hash=hashed_password,
            is_pilot=user_data.is_pilot,
        )
    else:
        new_user = model(
            email_id=user_data.email,
            name=user_data.name,
            phone=user_data.phone,
            password_hash=hashed_password,
        )
    
    db.add(new_user)
    db.commit()
    
    return UserCreateResponse(
        success=True,
        message=f"{user_type} user created successfully",
        email=user_data.email,
        user_type=user_type,
        default_password=DEFAULT_PASSWORD,
    )


