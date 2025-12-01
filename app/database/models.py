from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Date, Time, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Date, Time, Text, Enum, ForeignKeyConstraint


Base = declarative_base()


class AircraftStatus(enum.Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class MaintenanceStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MaintenanceType(enum.Enum):
    ROUTINE = "routine"
    INSPECTION = "inspection"
    REPAIR = "repair"
    OVERHAUL = "overhaul"


class Airport(Base):
    __tablename__ = "airports"

    airport_code = Column(String(3), primary_key=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100))
    country = Column(String(100), nullable=False)
    airport_name = Column(String(200), nullable=False)


class Route(Base):
    __tablename__ = "routes"

    route_id = Column(Integer, primary_key=True, autoincrement=True)
    source_airport_code = Column(String(3), ForeignKey("airports.airport_code"), nullable=False)
    destination_airport_code = Column(String(3), ForeignKey("airports.airport_code"), nullable=False)
    approved_capacity = Column(Integer, nullable=False)



class Aircraft(Base):
    __tablename__ = "aircraft"

    registration_number = Column(String(20), primary_key=True)
    aircraft_company = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(Enum(AircraftStatus), nullable=False, default=AircraftStatus.ACTIVE)


class Flight(Base):
    __tablename__ = "flights"

    flight_number = Column(String(10), primary_key=True)
    date = Column(Date, primary_key=True)

    route_id = Column(Integer, ForeignKey("routes.route_id"), nullable=False)
    scheduled_departure_time = Column(Time, nullable=False)
    scheduled_arrival_time = Column(Time, nullable=False)
    aircraft_registration = Column(
        String(20), ForeignKey("aircraft.registration_number"), nullable=False
    )

    # optional, but nice: relationship back to crew schedules
    crew_schedules = relationship(
        "CrewSchedule",
        back_populates="flight",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CrewSchedule(Base):
    __tablename__ = "crew_schedules"

    flight_number = Column(String(10), primary_key=True)
    date = Column(Date, primary_key=True)

    scheduled_departure_time = Column(Time, primary_key=True)
    email_id = Column(
        String(255),
        ForeignKey("crew.email_id"),
        primary_key=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["flight_number", "date"],
            ["flights.flight_number", "flights.date"],
            onupdate="CASCADE",      # <<< THIS is the key bit
            ondelete="RESTRICT",     # or "CASCADE" if you want deletes to cascade too
            name="crew_schedules_ibfk_1",  # optional, but matches your error message
        ),
    )

    # relationship back to Flight
    flight = relationship("Flight", back_populates="crew_schedules")



class Crew(Base):
    __tablename__ = "crew"

    email_id = Column(String(255), primary_key=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(20))
    password_hash = Column(String(255), nullable=False)
    last_login = Column(DateTime)
    is_pilot = Column(Boolean, nullable=False, default=False)



class Engineer(Base):
    __tablename__ = "engineers"

    email_id = Column(String(255), primary_key=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(20))
    password_hash = Column(String(255), nullable=False)
    last_login = Column(DateTime)


class Scheduler(Base):
    __tablename__ = "schedulers"

    email_id = Column(String(255), primary_key=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(20))
    password_hash = Column(String(255), nullable=False)
    last_login = Column(DateTime)


class Admin(Base):
    __tablename__ = "admins"

    email_id = Column(String(255), primary_key=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(20))
    password_hash = Column(String(255), nullable=False)
    last_login = Column(DateTime)


class MaintenanceHistory(Base):
    __tablename__ = "maintenance_history"

    job_id = Column(Integer, primary_key=True, autoincrement=True)
    checkin_date = Column(DateTime, nullable=False)
    checkout_date = Column(DateTime)
    status = Column(Enum(MaintenanceStatus), nullable=False, default=MaintenanceStatus.PENDING)
    remarks = Column(Text)
    registration_number = Column(String(20), ForeignKey("aircraft.registration_number"), nullable=False)
    type = Column(Enum(MaintenanceType), nullable=False)



class EngineerMaintenance(Base):
    __tablename__ = "engineer_maintenances"

    job_id = Column(Integer, ForeignKey("maintenance_history.job_id"), primary_key=True)
    engineer_email_id = Column(String(255), ForeignKey("engineers.email_id"), primary_key=True)
    assigned_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    role = Column(String(100))



class AircraftPart(Base):
    __tablename__ = "aircraft_parts"

    part_number = Column(String(100), primary_key=True)
    part_manufacturer = Column(String(200), nullable=False)
    model = Column(String(100), nullable=False)
    manufacturing_date = Column(Date, nullable=False)
    aircraft_registration = Column(String(20), ForeignKey("aircraft.registration_number"), nullable=False)


