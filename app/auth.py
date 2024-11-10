# Seyed Mohsen Moosavi & Ali Amri
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import User, db , User_transaction
from app.schemas import UserCreateSchema

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['POST'])
def register():

    data = request.get_json()
    data_re=request.get_json()
    data=UserCreateSchema(**data)
    username = data.username
    password = data.password
    referral_code = data_re.get('referral_code')  # Accept referral code from request

    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 400

    # Check if referral code exists and is valid
    referrer = None
    if referral_code:
        print(referral_code)
        referrer = User.query.filter_by(referral_code=referral_code).first()
        if not referrer:
            return jsonify({"msg": "Invalid referral code"}), 400

    new_user = User(username=username)
    new_user.set_password(password)
    new_user.generate_referral_code()

    # If referral code is valid, link new user to referrer
    if referrer:
        new_user.referred_by = referrer.id
        print(new_user.referred_by)

    db.session.add(new_user)
    db.session.commit()

    access_token = create_access_token(identity=new_user.id)
    return jsonify({"msg": "User created successfully","access_token":access_token}), 201


@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user_data = UserCreateSchema(**data)

    user = User.query.filter_by(username=user_data.username).first()

    if user and user.check_password(user_data.password):
        access_token = create_access_token(identity=user.id)
        return jsonify({"msg": "User logged in successfully", "access_token": access_token}), 200
    return jsonify({"msg": "Invalid credentials"}), 401


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
    referred_users = [{'id': u.id, 'username': u.username} for u in user.referred_users_rel] if user.referred_users_rel else []

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
