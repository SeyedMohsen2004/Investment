from datetime import datetime, timedelta
import random
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(40), unique=True, nullable=False, default='')
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    register_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    admin = db.Column(db.Boolean(), default=False, nullable=False)  # New admin column
    referrer = db.relationship('User', remote_side=[id], backref='referred_users', foreign_keys=[referrer_id])

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        if not self.code:
            self.code = self.generate_unique_referral_code()

    def generate_unique_referral_code(self):
        while True:
            code = str(random.randint(10000, 99999))
            if not self.is_code_exists(code):
                return code

    @staticmethod
    def is_code_exists(code):
        exists = User.query.filter_by(code=code).first() is not None
        return exists

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.DECIMAL(precision=10, scale=5), nullable=False)
    confirm = db.Column(db.Boolean(), nullable=False, default=False)
    confirm_check_date = db.Column(db.DateTime(), nullable=True)  # Updated by admin confirmation
    profit = db.Column(db.DECIMAL(precision=10, scale=5), nullable=True, default=0.0)
    last_profit_date = db.Column(db.DateTime(), nullable=True)  # Tracks last profit calculation
    request_date = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)  # When the request was made

    user = db.relationship('User', backref='investments')

    def calculate_profit(self): 
        if not self.confirm_check_date or not self.confirm:
            return 0.0

        # If last_profit_date is None, set it to the confirm_check_date for the first calculation
        if not self.last_profit_date:
            self.last_profit_date = self.confirm_check_date

        # Ensure confirm_check_date and last_profit_date are datetime objects
        if isinstance(self.confirm_check_date, datetime):
            confirm_check_date = self.confirm_check_date
        else:
            confirm_check_date = datetime.combine(self.confirm_check_date, datetime.min.time())

        if isinstance(self.last_profit_date, datetime):
            last_profit_date = self.last_profit_date
        else:
            last_profit_date = datetime.combine(self.last_profit_date, datetime.min.time())

        current_time = datetime.utcnow()

        # Calculate the number of days since the last profit calculation
        days_since_last_profit = (current_time - last_profit_date).days

        if days_since_last_profit < 1:
            # If less than a day has passed, no new profit should be calculated
            return 0.0

        # Update last_profit_date to the current date
        self.last_profit_date = current_time

        # Calculate the number of days since the confirm_check_date
        days_since_confirm_check = (current_time - confirm_check_date).days

        # Get active users referred by this user
        active_users = self.get_active_referred_users()

        # Query the rate table to get the appropriate rate entry for the current investment
        rate_info = Rate.query.filter(
            Rate.min_amount <= self.amount,
            Rate.min_active_user <= active_users
        ).order_by(Rate.min_amount.desc(), Rate.min_active_user.desc()).first()

        if not rate_info:
            return 0.0

        # Use the rate entry's profit percentage
        profit_percentage = float(rate_info.rate)
        
        # Calculate profit based on days since the confirm_check_date
        profit_amount = days_since_confirm_check * (profit_percentage / 100) * float(self.amount)

        # Round profit amount to 5 decimal places
        profit_amount = round(profit_amount, 5)

        # Update the profit in the database
        self.profit = profit_amount

        # Commit changes to the database
        db.session.commit()

        return profit_amount


    def get_active_referred_users(self):
        #"""Count the number of active users referred by this user."""
        referred_users = User.query.filter_by(referrer_id=self.user_id).all()
        active_users_count = 0
        for user in referred_users:
            total_investment = Investment.get_total_investment_for_user(user.id)
            if total_investment > 0:
                active_users_count += 1
        return active_users_count

    @staticmethod
    def get_total_investment_for_user(user_id):
        """Get the total amount of investments for a specific user."""
        total_investment = db.session.query(func.sum(Investment.amount)).filter_by(user_id=user_id).scalar()
        return total_investment or 0.0


class Rate(db.Model):
    __tablename__ = 'rate'

    id = db.Column(db.Integer, primary_key=True)
    min_amount = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    min_active_user = db.Column(db.BigInteger, nullable=False)
    rate = db.Column(db.Numeric(precision=5, scale=2), nullable=False)
