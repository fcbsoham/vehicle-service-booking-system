import random
from datetime import datetime, date, timedelta

from app import app
from extensions import db, bcrypt
from models.user import User
from models.vehicle import Vehicle
from models.booking import Booking


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

TARGET_USERS = 100
TARGET_VEHICLES = 150
TARGET_BOOKINGS = 500

DEMO_EMAIL_PREFIX = "demo_user_"
DEMO_EMAIL_DOMAIN = "@demo.example.com"
DEMO_REGISTRATION_PREFIX = "DEMO-"
DEMO_BOOKING_MARKER = "[DEMO DATA]"

DEMO_PASSWORD = "DemoPass123!"

random.seed(42)


# --------------------------------------------------
# SAMPLE DATA
# --------------------------------------------------

FIRST_NAMES = [
    "Aarav", "Aditya", "Arjun", "Ishaan", "Kabir",
    "Rahul", "Rohan", "Vikram", "Aanya", "Ananya",
    "Diya", "Isha", "Kavya", "Meera", "Priya",
    "Riya", "Saanvi", "Sneha", "Tanvi", "Zoya"
]

LAST_NAMES = [
    "Sharma", "Patel", "Deshmukh", "Kulkarni", "Joshi",
    "Mehta", "Shah", "Verma", "Gupta", "Reddy",
    "Nair", "Iyer", "Khan", "Singh", "Rao"
]

VEHICLES = [
    ("Maruti Suzuki", "Swift", "Petrol"),
    ("Maruti Suzuki", "Baleno", "Petrol"),
    ("Maruti Suzuki", "Brezza", "Petrol"),
    ("Hyundai", "i20", "Petrol"),
    ("Hyundai", "Creta", "Diesel"),
    ("Hyundai", "Venue", "Petrol"),
    ("Tata", "Nexon", "Petrol"),
    ("Tata", "Punch", "Petrol"),
    ("Tata", "Nexon EV", "Electric"),
    ("Mahindra", "Scorpio", "Diesel"),
    ("Mahindra", "XUV700", "Diesel"),
    ("Honda", "City", "Petrol"),
    ("Honda", "Amaze", "Petrol"),
    ("Toyota", "Innova", "Diesel"),
    ("Toyota", "Hyryder", "Hybrid"),
    ("Kia", "Seltos", "Petrol"),
    ("Kia", "Sonet", "Diesel"),
    ("Renault", "Kwid", "Petrol"),
    ("Volkswagen", "Polo", "Petrol"),
    ("Skoda", "Slavia", "Petrol"),
]

SERVICE_TYPES = [
    "General Service",
    "Oil Change",
    "Brake Inspection",
    "Tyre Replacement",
    "Battery Check",
    "AC Service",
    "Engine Diagnostics",
    "Wheel Alignment",
    "Clutch Inspection",
    "Car Wash",
]

BOOKING_STATUSES = [
    "Pending",
    "Confirmed",
    "Completed",
    "Cancelled",
]


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def demo_email(number):
    return (
        f"{DEMO_EMAIL_PREFIX}{number:03d}"
        f"{DEMO_EMAIL_DOMAIN}"
    )


def create_demo_users():
    """Create missing demo customers without deleting existing users."""

    existing_users = {
        user.email: user
        for user in User.query.filter(
            User.email.like(
                f"{DEMO_EMAIL_PREFIX}%{DEMO_EMAIL_DOMAIN}"
            )
        ).all()
    }

    password_hash = bcrypt.generate_password_hash(
        DEMO_PASSWORD
    ).decode("utf-8")

    created = 0

    for number in range(1, TARGET_USERS + 1):
        email = demo_email(number)

        if email in existing_users:
            continue

        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)

        user = User(
            full_name=f"{first_name} {last_name}",
            email=email,
            password=password_hash,
            phone=f"90000{number:05d}",
            role="customer",
            created_at=datetime.utcnow()
            - timedelta(days=random.randint(30, 900)),
        )

        db.session.add(user)
        created += 1

    db.session.flush()

    print(f"New demo customers created: {created}")


def get_demo_users():
    """Return demo users in a stable order."""

    return (
        User.query
        .filter(
            User.email.like(
                f"{DEMO_EMAIL_PREFIX}%{DEMO_EMAIL_DOMAIN}"
            )
        )
        .order_by(User.email)
        .all()
    )


def create_demo_vehicles():
    """Create missing demo vehicles for demo customers."""

    demo_users = get_demo_users()

    if not demo_users:
        raise RuntimeError(
            "No demo customers found. Create demo users first."
        )

    existing_registrations = {
        vehicle.registration_number
        for vehicle in Vehicle.query.filter(
            Vehicle.registration_number.like(
                f"{DEMO_REGISTRATION_PREFIX}%"
            )
        ).all()
    }

    created = 0

    for number in range(1, TARGET_VEHICLES + 1):
        registration = f"DEMO-{number:04d}"

        if registration in existing_registrations:
            continue

        user = demo_users[(number - 1) % len(demo_users)]

        brand, model, fuel_type = random.choice(VEHICLES)

        vehicle = Vehicle(
            user_id=user.user_id,
            brand=brand,
            model=model,
            year=random.randint(2015, 2026),
            registration_number=registration,
            fuel_type=fuel_type,
            created_at=datetime.utcnow()
            - timedelta(days=random.randint(10, 700)),
        )

        db.session.add(vehicle)
        created += 1

    db.session.flush()

    print(f"New demo vehicles created: {created}")


def create_demo_bookings():
    """Create missing demo bookings with valid customer-vehicle links."""

    demo_vehicles = (
        Vehicle.query
        .join(User, Vehicle.user_id == User.user_id)
        .filter(
            User.email.like(
                f"{DEMO_EMAIL_PREFIX}%{DEMO_EMAIL_DOMAIN}"
            )
        )
        .order_by(Vehicle.vehicle_id)
        .all()
    )

    if not demo_vehicles:
        raise RuntimeError(
            "No demo vehicles found. Create demo vehicles first."
        )

    existing_demo_booking_count = Booking.query.filter(
        Booking.description.contains(DEMO_BOOKING_MARKER)
    ).count()

    missing = max(
        0,
        TARGET_BOOKINGS - existing_demo_booking_count
    )

    created = 0

    for _ in range(missing):
        vehicle = random.choice(demo_vehicles)

        # The booking owner is always the selected vehicle's owner.
        user_id = vehicle.user_id

        booking_date = date.today() - timedelta(
            days=random.randint(0, 730)
        )

        service_type = random.choice(SERVICE_TYPES)
        status = random.choices(
            BOOKING_STATUSES,
            weights=[20, 20, 50, 10],
            k=1,
        )[0]

        description = (
            f"{DEMO_BOOKING_MARKER} "
            f"Sample request for {service_type.lower()}."
        )

        booking = Booking(
            user_id=user_id,
            vehicle_id=vehicle.vehicle_id,
            service_type=service_type,
            booking_date=booking_date,
            description=description,
            status=status,
            created_at=datetime.combine(
                booking_date, datetime.min.time()
            ) + timedelta(
                hours=random.randint(8, 18),
                minutes=random.choice([0, 15, 30, 45]),
            ),
        )

        db.session.add(booking)
        created += 1

    db.session.flush()

    print(f"New demo bookings created: {created}")


# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------

def main():
    with app.app_context():
        try:
            print("\n===================================")
            print(" VEHICLE SERVICE DEMO DATA GENERATOR")
            print("===================================\n")

            # Report existing data before inserting anything.
            print("Existing database records:")
            print(f"Users: {User.query.count()}")
            print(f"Vehicles: {Vehicle.query.count()}")
            print(f"Bookings: {Booking.query.count()}")

            # Create records in foreign-key dependency order.
            create_demo_users()
            create_demo_vehicles()
            create_demo_bookings()

            # Commit all additions together.
            db.session.commit()

            print("\nDemo data generation completed.")
            print("\nFinal database totals:")
            print(f"Users: {User.query.count()}")
            print(f"Vehicles: {Vehicle.query.count()}")
            print(f"Bookings: {Booking.query.count()}")

            print("\nDemo accounts:")
            print(f"Email format: {DEMO_EMAIL_PREFIX}001"
                  f"{DEMO_EMAIL_DOMAIN}")
            print(f"Password: {DEMO_PASSWORD}")

            print(
                "\nNote: These credentials are for synthetic "
                "demo accounts only."
            )

        except Exception:
            db.session.rollback()
            print(
                "\nAn error occurred. The current transaction "
                "has been rolled back."
            )
            raise


if __name__ == "__main__":
    main()