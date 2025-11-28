import argparse

from app.database.connection import SessionLocal
from app.database import models


def create_airport(
    airport_code: str,
    city: str,
    country: str,
    airport_name: str,
    state: str | None = None,
) -> None:
    """
    Create a new airport in the database.
    """
    if len(airport_code) != 3:
        raise ValueError("Airport code must be exactly 3 characters")

    airport_code = airport_code.upper()

    db = SessionLocal()
    try:
        # Check if airport already exists
        existing = db.query(models.Airport).filter(
            models.Airport.airport_code == airport_code
        ).first()
        if existing:
            raise ValueError(f"Airport with code '{airport_code}' already exists")

        airport = models.Airport(
            airport_code=airport_code,
            city=city,
            state=state,
            country=country,
            airport_name=airport_name,
        )

        db.add(airport)
        db.commit()

        print(f"Created airport '{airport_name}' with code '{airport_code}'")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an airport in the database")
    parser.add_argument("--code", required=True, help="Airport code (3 characters, e.g., JFK)")
    parser.add_argument("--city", required=True, help="City name")
    parser.add_argument("--country", required=True, help="Country name")
    parser.add_argument("--name", required=True, help="Airport name")
    parser.add_argument("--state", help="State/Province (optional)")

    args = parser.parse_args()

    create_airport(
        airport_code=args.code,
        city=args.city,
        country=args.country,
        airport_name=args.name,
        state=args.state,
    )


if __name__ == "__main__":
    main()

