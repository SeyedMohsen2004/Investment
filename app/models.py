from flask_sqlalchemy import SQLAlchemy
import bcrypt
import random
import string
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    referral_code = db.Column(db.String(50), unique=True, nullable=True)
    referred_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    referrer = db.relationship('User', remote_side=[id], backref=db.backref('referred_users_rel'))
    referral_bonus = db.Column(db.Float, default=0.0)  # Add this line for referral bonus

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())
    
    def generate_referral_code(self):
        while True:
            code = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            if not User.query.filter_by(referral_code=code).first():
                self.referral_code = code
                break

    def get_active_referred_users(self):
        active_users = 0
        for referred_user in self.referred_users_rel:
            confirmed_investments = Investment.query.filter_by(user_id=referred_user.id, is_confirmed=True).count()
            if confirmed_investments > 0:
                active_users += 1
        return active_users

    def calculate_level(self):
        active_users = self.get_active_referred_users()
        total_investment = sum([investment.amount for investment in self.investments if investment.is_confirmed])
        level = Level.query.filter(
            Level.min_active_users <= active_users,
            Level.min_amount <= total_investment
        ).order_by(Level.id.desc()).first()
        return level if level else None
    
    
class Admin(db.Model):
    __tablename__ = 'admin'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    last_date_log = db.Column(db.Date, nullable=False)
    
    def __init__(self, username, password, last_date_log):
        self.username = username
        self.set_password(password)
        self.last_date_log = last_date_log
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    
class Investment(db.Model):
    __tablename__ = 'investment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    start_time = db.Column(db.DateTime)
    withdrawable_profit = db.Column(db.Float, default=0)  # New column
    cycle_length = db.Column(db.Integer, default=30)
    last_withdraw_time = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship('User', backref=db.backref('investments'))  # Relationship intact


    def get_profit(self):
        # Define the daily profit rate (adjust as needed)
        daily_profit_rate = 0.01   # 01% daily

        # Calculate the number of full cycles completed
        current_time = datetime.utcnow()
        time_elapsed = current_time - self.start_time
        full_cycles_completed = time_elapsed.days // self.cycle_length

        # Calculate total profit earned from completed cycles
        total_profit = full_cycles_completed * (self.amount * daily_profit_rate * self.cycle_length)


        # Withdrawable profit is stored in the `withdrawable_profit` field
        withdrawable_profit = self.withdrawable_profit + total_profit

        locked_profit = 0
        locked_days = time_elapsed.days % self.cycle_length
        if locked_days > 0:
            locked_profit = locked_days * (self.amount * daily_profit_rate)

        return {
            'amount': self.amount,
            'profit': withdrawable_profit,
            'locked_profit': locked_profit
        }

    def is_cycle_complete(self):
        # Check if a full cycle has completed
        current_time = datetime.utcnow()
        time_elapsed = current_time - self.start_time
        full_cycles_completed = time_elapsed.days // self.cycle_length
        return full_cycles_completed > 0


    def calculate_withdrawable_profit(self, full_cycles_completed):
        # Example: calculate based on daily profit of 0.001%
        daily_rate = 0.01 
        profit_per_cycle = self.amount * daily_rate * self.cycle_length  # Profit for one full cycle
        return profit_per_cycle * full_cycles_completed


class Level(db.Model):
    __tablename__ = 'level'
    id = db.Column(db.Integer, primary_key=True)
    min_active_users = db.Column(db.Integer, nullable=False)
    min_amount = db.Column(db.Float, nullable=False)
    profit_multiplier = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<Level {self.id}>"
    

class User_transaction(db.Model):  # Fix class name and add db.Model inheritance
    __tablename__ = 'user_transaction'
    id = db.Column(db.Integer, primary_key=True)
    type_tran=db.Column(db.String)
    amount = db.Column(db.Float, nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
    confirm_date = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'))
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('user_transactions'))
    admin = db.relationship('Admin', backref=db.backref('user_transactions'))

