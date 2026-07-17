from extensions import db, login_manager
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(15))
    role = db.Column(db.String(20), default="customer")
    created_at = db.Column(db.DateTime)
    vehicles = db.relationship(
    "Vehicle",
    backref="owner",
    lazy=True,
    cascade="all, delete"
)
    bookings = db.relationship(
    "Booking",
    backref="user",
    lazy=True
)

    def get_id(self):
        return str(self.user_id)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))