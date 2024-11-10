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
    current_level_id = db.Column(db.Integer, db.ForeignKey('level.id'), nullable=True)
    previous_level_id = db.Column(db.Integer, db.ForeignKey('level.id'), nullable=True) 
    
    current_level = db.relationship('Level', foreign_keys=[current_level_id], backref=db.backref('current_level_users', lazy=True))
    previous_level = db.relationship('Level', foreign_keys=[previous_level_id], backref=db.backref('previous_level_users', lazy=True))


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
            confirmed_investments = Investment.query.filter_by(user_id=referred_user.id).count()
            if confirmed_investments > 0:
                active_users += 1
        return active_users

    def calculate_level(self):
        active_users = self.get_active_referred_users()
        total_investment = sum(
            [investment.amount for investment in self.investments]
        )
        new_level = Level.query.filter(
            Level.min_active_users <= active_users,
            Level.min_amount <= total_investment
        ).order_by(Level.id.desc()).first()

        # Only update if the level changes
        if new_level and new_level != self.current_level:
            #NOTE current level is must be added in tabel?
            self.current_level = new_level
            db.session.commit()

        return self.current_level
    
    # def handle_level_change(self):
    #     # Get current level and calculate profits up to now
    #     current_level = self.calculate_level()
    #     current_time = datetime.utcnow()

    #     for investment in self.investments:
    #         if investment.is_cycle_complete():
    #             # Calculate profit based on the current level multiplier
    #             #NOTE to undo current_level.profit_multiplier
    #             profit = investment.get_profit()['profit'] * current_level.profit_multiplier

    #             # Add profit to the withdrawable amount
    #             investment.withdrawable_profit += profit
    #             investment.last_withdraw_time = current_time

    #     # Commit all changes
    #     db.session.commit()

    def handle_level_change(self):
        """
        Handle user level changes, applying a penalty if the level decreases.
        
        - If level goes up, profit is calculated with the new level for remaining days.
        - If level goes down, the entire cycle's profit is recalculated based on the lower level's profit rate.
        """
        # Get the user's current level and calculate level changes
        current_level = self.calculate_level()
        previous_level_id = self.previous_level_id  # Track previous level in user model
        current_time = datetime.utcnow()

        for investment in self.investments:
            # Calculate the number of days passed in the current cycle
            time_elapsed = current_time - investment.start_time
            days_passed = time_elapsed.days
            full_cycles_completed = days_passed // investment.cycle_length

            # Recalculate the profit if the level goes down
            if previous_level_id and self.current_level_id != previous_level_id:
                previous_level = Level.query.get(previous_level_id)
                if previous_level and current_level.id < previous_level.id:
                    # Apply penalty: Recalculate profit for the whole cycle based on current (lower) level
                    profit_rate = current_level.profit_multiplier
                    total_cycle_profit = investment.amount * profit_rate * investment.cycle_length
                    investment.withdrawable_profit = total_cycle_profit * full_cycles_completed
                    print(f"Penalty applied: Full cycle recalculated with level {current_level.id}'s profit rate.")

                elif previous_level and current_level.id > previous_level.id:
                    # Update profit calculation for remaining days
                    remaining_days = investment.cycle_length - days_passed
                    additional_profit = investment.amount * current_level.profit_multiplier * remaining_days
                    investment.withdrawable_profit += additional_profit
                    print(f"Profit updated for remaining days with level {current_level.id}'s profit rate.")

            # Update the user's previous level id to the current one
            self.previous_level_id = self.current_level_id
            db.session.commit()


    
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
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")
    
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
            current_time = datetime.utcnow()
            time_elapsed = current_time - self.start_time
            full_cycles_completed = time_elapsed.days // self.cycle_length

            # Get the user's current level and profit multiplier
            level = self.user.calculate_level()
            daily_profit_rate = 0.01  # Default daily profit rate

            if level:
                daily_profit_rate *= level.profit_multiplier

            # Calculate profit for full cycles based on the daily rate
            total_profit = full_cycles_completed * (self.amount * daily_profit_rate * self.cycle_length)
            withdrawable_profit = self.withdrawable_profit + total_profit

            # Calculate locked profit for days within the current cycle
            locked_days = time_elapsed.days % self.cycle_length
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
    hash_code = db.Column(db.String(100), nullable=True)
    user = db.relationship('User', backref=db.backref('user_transactions'))
    admin = db.relationship('Admin', backref=db.backref('user_transactions'))
class Message(db.Model):
    __tablename__ = 'message'  # مطمئن شوید که نام جدول صحیح است
    
    message_id = db.Column(db.Integer, primary_key=True)  # شناسه پیام
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # شناسه کاربر (نویسنده یا گیرنده)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)  # شناسه ادمین (نویسنده یا گیرنده)
    content = db.Column(db.Text, nullable=False)  # محتوای پیام
    seen = db.Column(db.Boolean, default=False)  # وضعیت خوانده شدن پیام
    date = db.Column(db.DateTime, default=datetime.utcnow)  # تاریخ و زمان ارسال پیام
    parent_message_id = db.Column(db.Integer, db.ForeignKey('message.message_id'), nullable=True)  # شناسه پیام اصلی (برای پاسخ‌ها)

    
    @classmethod
    def get_first_investment_amount(cls, user_id):
        """
        Fetch the first confirmed investment amount for the given user.

        Args:
            user_id (int): The ID of the user.

        Returns:
            float: The amount of the first confirmed investment, or 0.0 if not found.
        """
        first_investment = (
            cls.query
            .filter_by(user_id=user_id, type_tran='deposit', confirmed=True)
            .order_by(cls.confirm_date.asc())
            .first()
        )

        return first_investment.amount if first_investment else 0.0
    # ارتباطات
    parent_message = db.relationship('Message', remote_side=[message_id], backref='replies')  # ارتباط با پیام اصلی برای پاسخ‌ها
    user = db.relationship('User', backref=db.backref('messages', lazy=True))  # ارتباط با جدول کاربر
    admin = db.relationship('Admin', backref=db.backref('messages', lazy=True))  # ارتباط با جدول ادمین
