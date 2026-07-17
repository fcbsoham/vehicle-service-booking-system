from extensions import db
from datetime import datetime


class Booking(db.Model):

    __tablename__ = "bookings"

    booking_id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False
    )

    vehicle_id = db.Column(
        db.Integer,
        db.ForeignKey("vehicles.vehicle_id"),
        nullable=False
    )

    service_type = db.Column(
        db.String(100),
        nullable=False
    )

    booking_date = db.Column(
        db.Date,
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    status = db.Column(
        db.String(20),
        default="Pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )