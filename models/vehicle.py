from extensions import db
from datetime import datetime


class Vehicle(db.Model):
    __tablename__ = "vehicles"

    vehicle_id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False
    )

    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer)
    registration_number = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )
    fuel_type = db.Column(db.String(20))

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
    bookings = db.relationship(
    "Booking",
    backref="vehicle",
    lazy=True
)