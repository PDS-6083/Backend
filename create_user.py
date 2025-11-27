import argparse
from getpass import getpass

from passlib.context import CryptContext

from app.database.connection import SessionLocal  # type: ignore
from app.database import models  # type: ignore


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


USER_MODEL_MAP = {
    "admin": models.Admin,
    "crew": models.Crew,
    "scheduler": models.Scheduler,
    "engineer": models.Engineer,
}


def create_user(user_type: str, email: str, password: str, name: str | None = None) -> None:
    user_type = user_type.lower()
    if user_type not in USER_MODEL_MAP:
        raise ValueError(f"Invalid user_type '{user_type}'. Must be one of: {', '.join(USER_MODEL_MAP.keys())}")

    db = SessionLocal()
    try:
        model = USER_MODEL_MAP[user_type]

        # Check if user already exists
        existing = db.query(model).filter(model.email_id == email).first()
        if existing:
            raise ValueError(f"{user_type} with email '{email}' already exists")

        hashed_password = pwd_context.hash(password)

        if not name:
            name = email.split("@")[0]

        user = model(
            email_id=email,
            name=name,
            password_hash=hashed_password,
        )

        db.add(user)
        db.commit()

        print(f"Created {user_type} user with email '{email}'")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a user in the database")
    parser.add_argument("--user-type", required=True, help="User type: admin | crew | scheduler | engineer")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--password", help="User password (if omitted, will prompt securely)")
    parser.add_argument("--name", help="User name (optional)")

    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass("Password: ")
        confirm = getpass("Confirm password: ")
        if password != confirm:
            raise SystemExit("Passwords do not match")

    create_user(args.user_type, args.email, password, args.name)


if __name__ == "__main__":
    main()


