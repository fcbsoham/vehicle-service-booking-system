import pandas as pd
from models.user import User
from flask import Flask, render_template, request
from config import Config
from extensions import db, login_manager, bcrypt
from flask_login import login_user
from flask_login import login_required, current_user, logout_user
from flask import redirect, url_for
from models.vehicle import Vehicle
from flask_login import current_user
from models.vehicle import Vehicle
from models.booking import Booking
from flask import session
from datetime import datetime
from data_mining.dashboard import data_mining_bp
from data_mining.business_dashboard import business_bp
from flask import make_response
from flask_login import current_user
from flask import request, redirect, url_for, flash
from flask_login import login_required, current_user

app = Flask(__name__)
app.config.from_object(Config)

@app.after_request
def prevent_authenticated_page_caching(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response



print("SECRET_KEY configured:", bool(app.config.get("SECRET_KEY")))

db.init_app(app)
login_manager.init_app(app)
bcrypt.init_app(app)
app.register_blueprint(data_mining_bp)
app.register_blueprint(business_bp)

@app.route("/")
def home():
    print("\n--- HOME ROUTE REACHED ---")
    print("Authenticated:", current_user.is_authenticated)
    print("Session keys:", list(session.keys()))

    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        phone = request.form["phone"]

        user = User(
            full_name=full_name,
            email=email,
            password=hashed_password,
            phone=phone
        )

        db.session.add(user)
        db.session.commit()

        return "User Registered Successfully!"
    

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            remember = request.form.get("remember") == "on"
            login_user(user, remember=remember)
            return redirect(url_for("dashboard"))

        return "Invalid Email or Password"

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    total_vehicles = Vehicle.query.count()
    total_bookings = Booking.query.count()

    pending_bookings = Booking.query.filter(
        db.func.lower(Booking.status) == "pending"
    ).count()

    completed_bookings = Booking.query.filter(
        db.func.lower(Booking.status).in_(["completed", "done"])
    ).count()

    recent_bookings = Booking.query.order_by(
        Booking.created_at.desc()
    ).limit(5).all()

    return render_template(
        "dashboard.html",
        total_vehicles=total_vehicles,
        total_bookings=total_bookings,
        pending_bookings=pending_bookings,
        completed_bookings=completed_bookings,
        recent_bookings=recent_bookings
    )

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

@app.route("/add_vehicle", methods=["GET", "POST"])
@login_required
def add_vehicle():

    if request.method == "POST":

        vehicle = Vehicle(
            user_id=current_user.user_id,
            brand=request.form["brand"],
            model=request.form["model"],
            year=request.form["year"],
            registration_number=request.form["registration_number"],
            fuel_type=request.form["fuel_type"]
        )

        db.session.add(vehicle)
        db.session.commit()

        return "Vehicle Added Successfully!"

    return render_template("add_vehicle.html")

@app.route("/my_vehicles")
@login_required
def my_vehicles():

    vehicles = Vehicle.query.filter_by(
        user_id=current_user.user_id
    ).all()

    return render_template(
        "my_vehicles.html",
        vehicles=vehicles
    )

@app.route("/edit_vehicle/<int:vehicle_id>", methods=["GET", "POST"])
@login_required
def edit_vehicle(vehicle_id):

    vehicle = Vehicle.query.filter_by(
        vehicle_id=vehicle_id,
        user_id=current_user.user_id
    ).first_or_404()

    if request.method == "POST":

        vehicle.brand = request.form["brand"]
        vehicle.model = request.form["model"]
        vehicle.year = request.form["year"]
        vehicle.registration_number = request.form["registration_number"]
        vehicle.fuel_type = request.form["fuel_type"]

        db.session.commit()

        return redirect(url_for("my_vehicles"))

    return render_template(
        "edit_vehicle.html",
        vehicle=vehicle
    )

@app.route("/delete_vehicle/<int:vehicle_id>")
@login_required
def delete_vehicle(vehicle_id):

    vehicle = Vehicle.query.filter_by(
        vehicle_id=vehicle_id,
        user_id=current_user.user_id
    ).first_or_404()

    db.session.delete(vehicle)
    db.session.commit()

    return redirect(url_for("my_vehicles"))

@app.route("/book_service", methods=["GET", "POST"])
@login_required
def book_service():

    vehicles = Vehicle.query.filter_by(
        user_id=current_user.user_id
    ).all()


    if request.method == "POST":

        booking = Booking(

            user_id=current_user.user_id,

            vehicle_id=request.form["vehicle_id"],

            service_type=request.form["service_type"],

            booking_date=datetime.strptime(
                request.form["booking_date"],
                "%Y-%m-%d"
            ),

            description=request.form["description"]

        )


        db.session.add(booking)

        db.session.commit()


        return "Service booked successfully!"


    return render_template(
        "book_service.html",
        vehicles=vehicles
    )

@app.route("/my_bookings")
@login_required
def my_bookings():

    bookings = Booking.query.filter_by(
        user_id=current_user.user_id
    ).all()


    return render_template(
        "my_bookings.html",
        bookings=bookings
    )

@app.route("/admin")
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        return "Access Denied", 403

    users = User.query.order_by(User.created_at.desc()).all()

    vehicles = Vehicle.query.order_by(
        Vehicle.created_at.desc()
    ).all()

    bookings = Booking.query.order_by(
        Booking.created_at.desc()
    ).all()

    total_users = User.query.count()
    total_vehicles = Vehicle.query.count()
    total_bookings = Booking.query.count()

    pending_bookings = Booking.query.filter(
        db.func.lower(Booking.status) == "pending"
    ).count()

    completed_bookings = Booking.query.filter(
        db.func.lower(Booking.status).in_(["completed", "done"])
    ).count()

    return render_template(
        "admin_dashboard.html",
        users=users,
        vehicles=vehicles,
        bookings=bookings,
        total_users=total_users,
        total_vehicles=total_vehicles,
        total_bookings=total_bookings,
        pending_bookings=pending_bookings,
        completed_bookings=completed_bookings
    )

@app.route("/admin/update-booking-status/[int:booking_id](int:booking_id)", methods=["POST"])
@login_required
def update_booking_status(booking_id):
    if current_user.role != "admin":
        return "Access Denied", 403

    booking = db.session.get(Booking, booking_id)

    if booking is None:
        return "Booking not found", 404

    new_status = request.form.get("status", "").strip().title()

    allowed_transitions = {
        "Pending": ["Confirmed", "Cancelled"],
        "Confirmed": ["Completed", "Cancelled"],
    }

    current_status = (booking.status or "").strip().title()

    if new_status not in allowed_transitions.get(current_status, []):
        return "Invalid booking status change", 400

    booking.status = new_status
    db.session.commit()

    flash(
        f"Booking #{booking.booking_id} status updated to {new_status}.",
        "success"
    )

    return redirect(url_for("admin_dashboard"))


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)