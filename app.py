from models.user import User
from flask import Flask, render_template, request
from config import Config
from extensions import db

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        phone = request.form["phone"]

        user = User(
            full_name=full_name,
            email=email,
            password=password,
            phone=phone
        )

        db.session.add(user)
        db.session.commit()

        return "User Registered Successfully!"

    return render_template("register.html")

with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)