from flask import Blueprint, request, jsonify
from app.models import Level, db, Admin
from app.schemas import UserCreateSchema
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import datetime
from flask_jwt_extended.exceptions import NoAuthorizationError
from app.models import User_transaction

admin = Blueprint('admin', __name__)

@admin.route('/register', methods=["POST"])
def register():
    data = request.get_json()
    data = UserCreateSchema(**data)
    username = data.username
    password = data.password

    if Admin.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 400

    last_date_log = datetime.utcnow().date()  # Set a default or use appropriate value
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
        # Check for token in the request header
        verify_jwt_in_request()
        admin_id = get_jwt_identity()
        # Retrieve the admin from the database
        admin = Admin.query.filter_by(id=admin_id).first()
        
        if not admin:
            return jsonify({"msg": "Admin not found or invalid token"}), 401
        
        return admin  # Return the admin object if valid

    except NoAuthorizationError:
        return jsonify({"msg": "Missing or invalid token"}), 401



@admin.route('/levels', methods=['GET'])
def get_levels():
    # Verify if the token is from a valid admin
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin  # This means an error occurred, and we return the error response

    # Proceed with the request if the admin is valid
    levels = Level.query.all()
    return jsonify([{
        "id": level.id,
        "min_active_users": level.min_active_users,
        "min_amount": level.min_amount,
        "profit_multiplier": level.profit_multiplier
    } for level in levels])


@admin.route('/levels', methods=['POST'])
def create_level():
    # Verify if the token is from a valid admin
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin  # Return the error response if token verification failed

    # Get the data from the request body
    data = request.get_json()
    
    # Create a new level entry
    new_level = Level(
        min_active_users=data['min_active_users'],
        min_amount=data['min_amount'],
        profit_multiplier=data['profit_multiplier']
    )
    db.session.add(new_level)
    db.session.commit()

    return jsonify({"msg": "Level created", "level_id": new_level.id}), 201

@admin.route('/unconfirmed-transactions', methods=['GET'])
def get_unconfirmed_transactions():
    # Verify if the token is from a valid admin
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin  # Return the error response if token verification failed

    # Query to get all unconfirmed transactions
    unconfirmed_transactions = User_transaction.query.filter_by(confirmed=False).all()

    # Prepare the response data
    transactions_data = [{
        "id": transaction.id,  
        "type": transaction.type_tran,
        "amount": transaction.amount,
        "description": transaction.description,
        "user_id": transaction.user_id,
        "request_date": transaction.request_date
    } for transaction in unconfirmed_transactions]

    return jsonify({"unconfirmed_transactions": transactions_data}), 200
