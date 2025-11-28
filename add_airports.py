from app.database.connection import SessionLocal
from app.database import models


# List of airports to add
AIRPORTS = [
    {
        "airport_code": "JFK",
        "city": "New York",
        "state": "New York",
        "country": "United States",
        "airport_name": "John F. Kennedy International Airport",
    },
    {
        "airport_code": "LAX",
        "city": "Los Angeles",
        "state": "California",
        "country": "United States",
        "airport_name": "Los Angeles International Airport",
    },
    {
        "airport_code": "ORD",
        "city": "Chicago",
        "state": "Illinois",
        "country": "United States",
        "airport_name": "Chicago O'Hare International Airport",
    },
    {
        "airport_code": "ATL",
        "city": "Atlanta",
        "state": "Georgia",
        "country": "United States",
        "airport_name": "Hartsfield-Jackson Atlanta International Airport",
    },
    {
        "airport_code": "DFW",
        "city": "Dallas",
        "state": "Texas",
        "country": "United States",
        "airport_name": "Dallas/Fort Worth International Airport",
    },
    {
        "airport_code": "DEN",
        "city": "Denver",
        "state": "Colorado",
        "country": "United States",
        "airport_name": "Denver International Airport",
    },
    {
        "airport_code": "SFO",
        "city": "San Francisco",
        "state": "California",
        "country": "United States",
        "airport_name": "San Francisco International Airport",
    },
    {
        "airport_code": "MIA",
        "city": "Miami",
        "state": "Florida",
        "country": "United States",
        "airport_name": "Miami International Airport",
    },
    {
        "airport_code": "SEA",
        "city": "Seattle",
        "state": "Washington",
        "country": "United States",
        "airport_name": "Seattle-Tacoma International Airport",
    },
    {
        "airport_code": "IAD",
        "city": "Washington",
        "state": "Virginia",
        "country": "United States",
        "airport_name": "Washington Dulles International Airport",
    },
    {
        "airport_code": "BOS",
        "city": "Boston",
        "state": "Massachusetts",
        "country": "United States",
        "airport_name": "Logan International Airport",
    },
    {
        "airport_code": "IAH",
        "city": "Houston",
        "state": "Texas",
        "country": "United States",
        "airport_name": "George Bush Intercontinental Airport",
    },
    {
        "airport_code": "LHR",
        "city": "London",
        "country": "United Kingdom",
        "airport_name": "London Heathrow Airport",
    },
    {
        "airport_code": "CDG",
        "city": "Paris",
        "country": "France",
        "airport_name": "Charles de Gaulle Airport",
    },
    {
        "airport_code": "DXB",
        "city": "Dubai",
        "country": "United Arab Emirates",
        "airport_name": "Dubai International Airport",
    },
    {
        "airport_code": "SIN",
        "city": "Singapore",
        "country": "Singapore",
        "airport_name": "Singapore Changi Airport",
    },
    {
        "airport_code": "HKG",
        "city": "Hong Kong",
        "country": "Hong Kong",
        "airport_name": "Hong Kong International Airport",
    },
    {
        "airport_code": "NRT",
        "city": "Tokyo",
        "country": "Japan",
        "airport_name": "Narita International Airport",
    },
    {
        "airport_code": "SYD",
        "city": "Sydney",
        "country": "Australia",
        "airport_name": "Sydney Kingsford Smith Airport",
    },
    {
        "airport_code": "FRA",
        "city": "Frankfurt",
        "country": "Germany",
        "airport_name": "Frankfurt Airport",
    },
    {
        "airport_code": "AMS",
        "city": "Amsterdam",
        "country": "Netherlands",
        "airport_name": "Amsterdam Airport Schiphol",
    },
    {
        "airport_code": "MAD",
        "city": "Madrid",
        "country": "Spain",
        "airport_name": "Madrid-Barajas Airport",
    },
    {
        "airport_code": "IST",
        "city": "Istanbul",
        "country": "Turkey",
        "airport_name": "Istanbul Airport",
    },
    {
        "airport_code": "BOM",
        "city": "Mumbai",
        "country": "India",
        "airport_name": "Chhatrapati Shivaji Maharaj International Airport",
    },
    {
        "airport_code": "PEK",
        "city": "Beijing",
        "country": "China",
        "airport_name": "Beijing Capital International Airport",
    },
]


def add_airports() -> None:
    """
    Add all airports from the AIRPORTS list to the database.
    Skips airports that already exist.
    """
    db = SessionLocal()
    added_count = 0
    skipped_count = 0

    try:
        for airport_data in AIRPORTS:
            airport_code = airport_data["airport_code"].upper()

            # Check if airport already exists
            existing = db.query(models.Airport).filter(
                models.Airport.airport_code == airport_code
            ).first()

            if existing:
                print(f"⏭️  Skipped '{airport_data['airport_name']}' ({airport_code}) - already exists")
                skipped_count += 1
                continue

            airport = models.Airport(
                airport_code=airport_code,
                city=airport_data["city"],
                state=airport_data.get("state"),
                country=airport_data["country"],
                airport_name=airport_data["airport_name"],
            )

            db.add(airport)
            print(f"✅ Added '{airport_data['airport_name']}' ({airport_code})")

        db.commit()
        added_count = len(AIRPORTS) - skipped_count

        print(f"\n📊 Summary: {added_count} airports added, {skipped_count} skipped")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🌍 Adding airports to the database...\n")
    add_airports()
    print("\n✨ Done!")

