from flask import Blueprint, request, jsonify
from app.models import Level, db, Admin, User
from app.schemas import UserCreateSchema
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError
from app.models import User_transaction, Investment, Message
from datetime import datetime, timedelta
from sqlalchemy import and_

admin = Blueprint('admin', __name__)

@admin.route('/register', methods=["POST"])
def register():
    data = request.get_json()
    data = UserCreateSchema(**data)
    username = data.username
    password = data.password

    if Admin.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 400

    last_date_log = datetime.utcnow().date()
    new_admin = Admin(username=username, password=password, last_date_log=last_date_log)

    db.session.add(new_admin)
    db.session.commit()

    access_token = create_access_token(identity=new_admin.id)
    return jsonify({"msg": "Admin created successfully", "access_token": access_token}), 201


@admin.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    data = UserCreateSchema(**data)
    username = data.username
    password = data.password

    admin = Admin.query.filter_by(username=username).first()

    if admin and admin.check_password(password):
        access_token = create_access_token(identity=admin.id)
        return jsonify({"msg": "Login successful", "access_token": access_token}), 200

    return jsonify({"msg": "Invalid username or password"}), 401


def verify_admin_token():
    try:
        verify_jwt_in_request()
        admin_id = get_jwt_identity()
        admin = Admin.query.filter_by(id=admin_id).first()
        
        if not admin:
            return jsonify({"msg": "Admin not found or invalid token"}), 401
        
        return admin

    except NoAuthorizationError:
        return jsonify({"msg": "Missing or invalid token"}), 401


@admin.route('/users', methods=['GET'])
@jwt_required()
def admin_users():
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin

    username = request.args.get('username')
    user_id = request.args.get('user_id')
    current_time = datetime.utcnow()

    query = User.query
    if username:
        query = query.filter(User.username.ilike(f'%{username}%'))
    if user_id:
        query = query.filter(User.id == user_id)

    users = query.all()
    users_data = []

    for user in users:
        # Fetch investments and calculate total invested amount and profit
        investments = Investment.query.filter_by(user_id=user.id).all()
        total_amount_of_investments = sum([investment.amount for investment in investments])
        total_profit_less_than_30_days = 0
        total_profit_more_than_30_days = 0

        for investment in investments:
            days_active = (current_time - investment.start_time).days
            profit_data = investment.get_profit()
            if days_active < 30:
                total_profit_less_than_30_days += profit_data['locked_profit']
            else:
                total_profit_more_than_30_days += profit_data['profit']

        # Count referred users with investment > 100
        active_users_count = 0
        for referred_user in user.referred_users_rel:
            # Sum the confirmed investments of the referred user
            referred_user_investments = Investment.query.filter_by(user_id=referred_user.id, is_confirmed=True).all()
            total_referred_investment = sum([inv.amount for inv in referred_user_investments])

            # Check if total investment is more than 100
            if total_referred_investment > 100:
                active_users_count += 1

        # Prepare user data
        user_data = {
            "id": user.id,
            "username": user.username,
            "referral_code": user.referral_code,
            "referred_by": user.referred_by,
            "referral_bonus": user.referral_bonus,
            "total_amount_invested": total_amount_of_investments,
            "total_profit_less_than_30_days": total_profit_less_than_30_days,
            "total_profit_more_than_30_days": total_profit_more_than_30_days,
            "active_users": active_users_count  # Add the count of active referred users
        }
        users_data.append(user_data)

    return jsonify({"users": users_data}), 200


@admin.route('/users/<int:id>', methods=['GET'])
@jwt_required()
def get_user_by_id(id):
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin

    current_time = datetime.utcnow()
    user = User.query.filter_by(id=id).first()

    if not user:
        return jsonify({"msg": "User not found"}), 404

    investments = Investment.query.filter_by(user_id=user.id).all()
    total_amount_of_investments = sum([investment.amount for investment in investments])
    total_profit_less_than_30_days = 0
    total_profit_more_than_30_days = 0

    for investment in investments:
        days_active = (current_time - investment.start_time).days
        profit_data = investment.get_profit()
        if days_active < 30:
            total_profit_less_than_30_days += profit_data['profit']
        else:
            total_profit_more_than_30_days += profit_data['profit']

    user_data = {
        "id": user.id,
        "username": user.username,
        "total_amount_invested": total_amount_of_investments,
        "total_profit_less_than_30_days": total_profit_less_than_30_days,
        "total_profit_more_than_30_days": total_profit_more_than_30_days
    }

    return jsonify(user_data), 200


@admin.route('/users/<int:user_id>/deposits', methods=['GET'])
@jwt_required()
def get_user_deposits(user_id):
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin

    deposits = User_transaction.query.filter_by(user_id=user_id, type_tran='deposit').all()
    deposit_data = [{
        "id": deposit.id,
        "amount": deposit.amount,
        "description": deposit.description,
        "confirmed": deposit.confirmed,
        "confirm_date": deposit.confirm_date,
        "request_date": deposit.request_date
    } for deposit in deposits]

    return jsonify({"deposits": deposit_data}), 200


@admin.route('/users/<int:user_id>/withdraw', methods=['GET'])
@jwt_required()
def get_user_withdrawals(user_id):
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin

    withdrawals = User_transaction.query.filter_by(user_id=user_id, type_tran='withdraw').all()
    withdraw_data = [{
        "id": withdraw.id,
        "amount": withdraw.amount,
        "description": withdraw.description,
        "confirmed": withdraw.confirmed,
        "confirm_date": withdraw.confirm_date,
        "request_date": withdraw.request_date
    } for withdraw in withdrawals]

    return jsonify({"withdrawals": withdraw_data}), 200


@admin.route('/users/<int:user_id>/transactions', methods=['GET'])
@jwt_required()
def get_user_transactions(user_id):
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin

    transactions = User_transaction.query.filter_by(user_id=user_id).all()
    transaction_data = [{
        "id": transaction.id,
        "type": transaction.type_tran,
        "amount": transaction.amount,
        "description": transaction.description,
        "confirmed": transaction.confirmed,
        "confirm_date": transaction.confirm_date,
        "request_date": transaction.request_date
    } for transaction in transactions]

    return jsonify({"transactions": transaction_data}), 200


@admin.route('/levels', methods=['GET'])
@jwt_required()
def get_levels():
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin

    levels = Level.query.all()
    return jsonify([{
        "id": level.id,
        "min_active_users": level.min_active_users,
        "min_amount": level.min_amount,
        "profit_multiplier": level.profit_multiplier
    } for level in levels])


@admin.route('/levels', methods=['POST'])
@jwt_required()
def create_level():
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin

    data = request.get_json()
    new_level = Level(
        min_active_users=data['min_active_users'],
        min_amount=data['min_amount'],
        profit_multiplier=data['profit_multiplier']
    )
    db.session.add(new_level)
    db.session.commit()

    return jsonify({"msg": "Level created", "level_id": new_level.id}), 201


@admin.route('/unconfirmed-transactions', methods=['GET'])
@jwt_required()
def get_unconfirmed_transactions():
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin

    unconfirmed_transactions = User_transaction.query.filter_by(confirmed=False).all()
    transactions_data = [{
        "id": transaction.id,  
        "type": transaction.type_tran,
        "amount": transaction.amount,
        "description": transaction.description,
        "user_id": transaction.user_id,
        "request_date": transaction.request_date
    } for transaction in unconfirmed_transactions]

    return jsonify({"unconfirmed_transactions": transactions_data}), 200


@admin.route('/confirm-transaction', methods=['POST'])
@jwt_required()
def confirm_transaction():
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin

    data = request.get_json()
    transaction_id = data.get('transaction_id')
    confirm = data.get('confirm')

    if transaction_id is None or confirm is None:
        return jsonify({"msg": "Transaction ID and confirmation status are required"}), 400

    transaction = User_transaction.query.filter_by(id=transaction_id).first()

    if not transaction:
        return jsonify({"msg": "Transaction not found"}), 404

    if confirm:
        transaction.confirmed = True
        transaction.confirm_date = datetime.utcnow()
        transaction.admin_id = admin.id

        new_investment = Investment(
            user_id=transaction.user_id,
            amount=transaction.amount,
            start_time=datetime.utcnow(),
        )
@admin.route('/messages', methods=['GET'])
@jwt_required()
def get_messages():
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin

    # Retrieve all messages along with user information
    messages = Message.query.all()

    messages_data = []
    for message in messages:
        # Update the 'seen' attribute to True
        if not message.seen:
            message.seen = True  # Mark as seen
            db.session.add(message)  # Add to session for updating

        user = User.query.filter_by(id=message.user_id).first()  # Find the associated user

        # Prepare the message and user info if user exists
        if user:
            messages_data.append({
                "message_id": message.message_id,
                "user_id": message.user_id,
                "username": user.username,
                "content": message.content,
                "created_at": message.date
            })

    # Commit the changes to the database
    db.session.commit()

    return jsonify({"messages": messages_data}), 200

@admin.route('/messages/<int:parent_message_id>', methods=['POST'])
@jwt_required()
def reply_to_message(parent_message_id):
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin

    data = request.json
    content = data.get('content')

    # بررسی وجود پیام اصلی
    parent_message = Message.query.get_or_404(parent_message_id)

    # پیدا کردن کاربر مرتبط با پیام والد
    user_id = parent_message.user_id
  
    # ایجاد پیام جدید به عنوان پاسخ
    message = Message(
        user_id=user_id,  # ID کاربر
        admin_id=admin.id,  # ID ادمین
        content=content,
        parent_message_id=parent_message.message_id
    )
    
    db.session.add(message)
    db.session.commit()

    return jsonify({"message": "Reply sent successfully"}), 201


@admin.route('/messages/<int:message_id>', methods=['DELETE'])
@jwt_required()
def delete_message(message_id):
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin

    message = Message.query.filter_by(id=message_id).first()

    if not message:
        return jsonify({"msg": "Message not found"}), 404

    db.session.delete(message)
    db.session.commit()
    return jsonify({"msg": "Message deleted successfully"}), 200
