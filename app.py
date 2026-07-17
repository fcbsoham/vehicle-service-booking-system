from models.user import User
from flask import Flask, render_template, request
from config import Config
from extensions import db, login_manager, bcrypt
from flask_login import login_user
from flask_login import login_required, current_user, logout_user
from flask import redirect, url_for


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

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)