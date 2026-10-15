from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db
from models.user import User
from models.vehicle import Vehicle
from models.booking import Booking


business_bp = Blueprint(
    "business",
    __name__,
    url_prefix="/admin/business-insights"
)


@business_bp.route("/")
@login_required
def business_dashboard():

    # Restrict this dashboard to administrators.
    if current_user.role != "admin":
        abort(403)

    # Live business statistics.
    total_users = (
        db.session.query(func.count(User.user_id)).scalar() or 0
    )

    total_vehicles = (
        db.session.query(func.count(Vehicle.vehicle_id)).scalar() or 0
    )

    total_bookings = (
        db.session.query(func.count(Booking.booking_id)).scalar() or 0
    )

    # Count bookings by status.
    status_results = (
        db.session.query(
            Booking.status,
            func.count(Booking.booking_id)
        )
        .group_by(Booking.status)
        .all()
    )

    booking_status = {
        (status or "Unspecified"): count
        for status, count in status_results
    }

    completed_bookings = booking_status.get("Completed", 0)
    pending_bookings = booking_status.get("Pending", 0)
    confirmed_bookings = booking_status.get("Confirmed", 0)
    cancelled_bookings = booking_status.get("Cancelled", 0)

    # Most frequently booked services.
    service_results = (
        db.session.query(
            Booking.service_type,
            func.count(Booking.booking_id).label("booking_count")
        )
        .group_by(Booking.service_type)
        .order_by(func.count(Booking.booking_id).desc())
        .limit(5)
        .all()
    )

    popular_services = [
        {
            "service": service or "Unspecified",
            "count": count
        }
        for service, count in service_results
    ]

    # Customers with the most bookings.
    customer_results = (
        db.session.query(
            User.full_name,
            func.count(Booking.booking_id).label("booking_count")
        )
        .join(Booking, Booking.user_id == User.user_id)
        .group_by(User.user_id, User.full_name)
        .order_by(func.count(Booking.booking_id).desc())
        .limit(5)
        .all()
    )

    frequent_customers = [
        {
            "name": name,
            "booking_count": count
        }
        for name, count in customer_results
    ]

    # Simple, explainable business recommendations.
    recommendations = []

    if pending_bookings > 0:
        recommendations.append({
            "title": "Review pending bookings",
            "message": (
                f"There are {pending_bookings} pending bookings. "
                "Review them and update their status where appropriate."
            ),
            "type": "warning"
        })

    if cancelled_bookings > 0:
        recommendations.append({
            "title": "Review cancellations",
            "message": (
                f"{cancelled_bookings} bookings are cancelled. "
                "Investigate the reasons to identify possible improvements."
            ),
            "type": "info"
        })

    if popular_services:
        top_service = popular_services[0]

        recommendations.append({
            "title": "Most popular service",
            "message": (
                f"{top_service['service']} has the highest booking count, "
                f"with {top_service['count']} bookings in the available records."
            ),
            "type": "success"
        })

    if not recommendations:
        recommendations.append({
            "title": "Business overview",
            "message": (
                "Review booking activity and service demand regularly "
                "to monitor business performance."
            ),
            "type": "info"
        })

    return render_template(
        "business_dashboard.html",
        total_users=total_users,
        total_vehicles=total_vehicles,
        total_bookings=total_bookings,
        completed_bookings=completed_bookings,
        pending_bookings=pending_bookings,
        confirmed_bookings=confirmed_bookings,
        cancelled_bookings=cancelled_bookings,
        popular_services=popular_services,
        frequent_customers=frequent_customers,
        recommendations=recommendations
    )