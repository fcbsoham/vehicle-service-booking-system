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
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)
bcrypt.init_app(app)

@app.route("/")
def home():
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
            login_user(user)
            return redirect(url_for("dashboard"))

        return "Invalid Email or Password"

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

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

    users = User.query.all()
    vehicles = Vehicle.query.all()
    bookings = Booking.query.all()

    return render_template(
        "admin_dashboard.html",
        users=users,
        vehicles=vehicles,
        bookings=bookings
    )

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)