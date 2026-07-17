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
        return "Registration received!"

    return render_template("register.html")


if __name__ == "__main__":
    app.run(debug=True)