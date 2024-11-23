# Seyed Mohsen Moosavi & Ali Amri
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import User, db , User_transaction
from app.schemas import UserCreateSchema
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['POST'])
def register():
    try:
        # Parse and validate incoming data
        data = request.get_json()
        user_data = UserCreateSchema(**data)  # Validate input using Pydantic schema

        username = user_data.username
        password = user_data.password
        referral_code = data.get('referral_code')  # Accept referral code from request

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            return jsonify({"msg": "Username already exists"}), 400

        # Check if referral code exists and is valid
        referrer = None
        if referral_code:
            referrer = User.query.filter_by(referral_code=referral_code).first()
            if not referrer:
                return jsonify({"msg": "Invalid referral code"}), 400

        # Create new user
        new_user = User(username=username)
        new_user.set_password(password)  # Make sure to securely store the password
        new_user.generate_referral_code()

        # If referral code is valid, link new user to referrer
        if referrer:
            new_user.referred_by = referrer.id

        db.session.add(new_user)
        db.session.commit()

        # Generate access token
        access_token = create_access_token(identity=new_user.id)
        return jsonify({"msg": "User created successfully", "access_token": access_token}), 201

    except ValidationError as e:
        # Handle Pydantic validation errors
        return jsonify({"msg": "Invalid data", "errors": e.errors()}), 400
    except BadRequest as e:
        # Handle bad request errors (e.g., malformed JSON)
        return jsonify({"msg": "Bad request", "error": str(e)}), 400
    except Exception as e:
        # Catch any other unforeseen errors
        return jsonify({"msg": "An error occurred", "error": str(e)}), 500


@auth.route('/login', methods=['POST'])
def login():
    try:
        # Parse and validate incoming data
        data = request.get_json()
        user_data = UserCreateSchema(**data)  # Validate input using Pydantic schema

        # Check if user exists
        user = User.query.filter_by(username=user_data.username).first()
        if user and user.check_password(user_data.password):
            access_token = create_access_token(identity=user.id)
            return jsonify({"msg": "User logged in successfully", "access_token": access_token}), 200
        else:
            return jsonify({"msg": "Invalid username or password"}), 401

    except ValidationError as e:
        # Handle Pydantic validation errors
        return jsonify({"msg": "Invalid data", "errors": e.errors()}), 400
    except BadRequest as e:
        # Handle bad request errors (e.g., malformed JSON)
        return jsonify({"msg": "Bad request", "error": str(e)}), 400
    except Exception as e:
        # Catch any other unforeseen errors
        return jsonify({"msg": "An error occurred", "error": str(e)}), 500


@auth.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"msg": "User not found"}), 404
    
    first_investment_amount = User_transaction.get_first_investment_amount(current_user_id)

    current_level = user.calculate_level()
    level_info = {
        "level_id": current_level.id,
        "profit_multiplier": current_level.profit_multiplier
    } if current_level else {"level_id": None, "profit_multiplier": 0}

    # Use referred_users_rel to get users referred by the current user
    referred_users = [{'id': u.id, 'username': u.username, 'current_level_id': u.current_level_id} for u in user.referred_users_rel] if user.referred_users_rel else []

    response = {
        
        "username": user.username,
        "referral_code": user.referral_code,
        "referred_users": referred_users,
        "referral_bonus": user.referral_bonus,
        "first_investment_amount": first_investment_amount,
        "level_info": level_info
        
    }
    return jsonify(response), 200



@auth.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    return jsonify(logged_in_as=current_user_id), 200
