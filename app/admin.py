# Seyed Mohsen Moosavi & Ali Amri
from flask import Blueprint, request, jsonify
from app.models import Level, db, Admin, User
from app.schemas import UserCreateSchema
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError
from app.models import User_transaction, Investment, Message
from datetime import datetime , timedelta
from flask_cors import CORS  # Import CORS
from pydantic import ValidationError

# Initialize Blueprint
admin = Blueprint('admin', __name__)
CORS(admin)  # Enable CORS for this blueprint

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


@admin.route('/register', methods=["POST"])
def register():
    try:
        # Parse and validate the input data using Pydantic schema
        data = request.get_json()
        data = UserCreateSchema(**data)
        username = data.username
        password = data.password

        # Check if username already exists
        if Admin.query.filter_by(username=username).first():
            return jsonify({"msg": "Username already exists"}), 400

        # Create a new admin
        last_date_log = datetime.utcnow().date()  # Set the default value
        new_admin = Admin(username=username, password=password, last_date_log=last_date_log)

        # Add and commit the new admin to the database
        db.session.add(new_admin)
        db.session.commit()

        # Generate an access token
        access_token = create_access_token(identity=new_admin.id)
        return jsonify({"msg": "Admin created successfully", "access_token": access_token}), 201

    except ValidationError as ve:
        # Handle Pydantic validation errors
        return jsonify({"msg": "Validation Error", "errors": ve.errors()}), 422

    except Exception as e:
        # Catch all other exceptions
        return jsonify({"msg": "An error occurred", "error": str(e)}), 500


@admin.route('/login', methods=['POST'])
def login():
    try:
        # Parse and validate the input data using Pydantic schema
        data = request.get_json()
        data = UserCreateSchema(**data)
        username = data.username
        password = data.password

        # Fetch the admin from the database
        admin = Admin.query.filter_by(username=username).first()

        # Validate password and generate token if successful
        if admin and admin.check_password(password):
            access_token = create_access_token(identity=admin.id)
            return jsonify({"msg": "Login successful", "access_token": access_token}), 200

        # Invalid credentials
        return jsonify({"msg": "Invalid username or password"}), 401

    except ValidationError as ve:
        # Handle Pydantic validation errors
        return jsonify({"msg": "Validation Error", "errors": ve.errors()}), 422

    except Exception as e:
        # Catch all other exceptions
        return jsonify({"msg": "An error occurred", "error": str(e)}), 500


@admin.route('/users', methods=['GET'])
@jwt_required()
def admin_users():
    # Verify if the token is from a valid admin
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin  # Return the error response if token verification failed

    # Get the query parameters for filtering
    username = request.args.get('username')
    user_id = request.args.get('user_id')

    # Get the current time and calculate the 30-day threshold
    current_time = datetime.utcnow()

    # Build the query based on filters
    query = User.query

    # Apply filters if provided
    if username:
        query = query.filter(User.username.ilike(f'%{username}%'))  # Search by username (case-insensitive)
    
    if user_id:
        query = query.filter(User.id == user_id)  # Search by user_id

    # Execute the query to get the filtered users
    users = query.all()

    # Prepare the list to hold user data with investment information
    users_data = []

    # Loop through each user and calculate their investments and profits
    for user in users:
        # Query all investments for this user
        investments = Investment.query.filter_by(user_id=user.id).all()

        # Initialize variables for investment amounts and profits
        total_amount_of_investments = sum([investment.amount for investment in investments])
        total_profit_less_than_30_days = 0
        total_profit_more_than_30_days = 0

        # Loop through the user's investments and calculate profits
        for investment in investments:
            # Get the number of days the investment has been active
            days_active = (current_time - investment.start_time).days


# Calculate the profits based on the duration of the investment
            profit_data = investment.get_profit()
            if days_active < 30:
                total_profit_less_than_30_days += profit_data['profit']
            else:
                total_profit_more_than_30_days += profit_data['profit']

        # Prepare the user data with investment and profit details
        user_data = {
            "id": user.id,
            "username": user.username,
            "referral_code": user.referral_code,
            "referred_by": user.referred_by,
            "referral_bonus": user.referral_bonus,
            "total_amount_invested": total_amount_of_investments,  # Sum of all investments for the user
            "total_profit_less_than_30_days": total_profit_less_than_30_days,  # Profits for investments < 30 days
            "total_profit_more_than_30_days": total_profit_more_than_30_days  # Profits for investments >= 30 days
        }

        # Add the user data to the list
        users_data.append(user_data)

    # Return the response with the user data
    return jsonify({
        "users": users_data
    }), 200


@admin.route('/users/<int:id>', methods=['GET'])
@jwt_required()
def get_user_by_id(id):
    # Verify if the token is from a valid admin
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin  # Return the error response if token verification failed

    # Get the current time and calculate the 30-day threshold
    current_time = datetime.utcnow()
    thirty_days_ago = current_time - timedelta(days=30)

    # Query the user by ID
    user = User.query.filter_by(id=id).first()

    if not user:
        return jsonify({"msg": "User not found"}), 404

    # Query all investments for the user
    investments = Investment.query.filter_by(user_id=user.id).all()

    # Initialize variables for investment amounts and profits
    total_amount_of_investments = sum([investment.amount for investment in investments])
    total_profit_less_than_30_days = 0
    total_profit_more_than_30_days = 0

    # Loop through the user's investments and calculate profits
    for investment in investments:
        # Get the number of days the investment has been active
        days_active = (current_time - investment.start_time).days

        # Calculate the profits based on the duration of the investment
        profit_data = investment.get_profit()
        if days_active < 30:
            total_profit_less_than_30_days += profit_data['profit']
        else:
            total_profit_more_than_30_days += profit_data['profit']

    # Prepare the response data for the user's profile
    user_data = {
        "id": user.id,
        "username": user.username,
        # "password_hash": user.password_hash,  # It's advisable not to show passwords in plain text.
        "total_amount_invested": total_amount_of_investments,
        "total_profit_less_than_30_days": total_profit_less_than_30_days,
        "total_profit_more_than_30_days": total_profit_more_than_30_days
    }

    # Return the user's profile and investment information
    return jsonify(user_data), 200



@admin.route('/users/<int:user_id>/deposits', methods=['GET'])
@jwt_required()
def get_user_deposits(user_id):
    # Verify if the token is from a valid admin
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin  # Return the error response if token verification failed

    # Query to get all deposit transactions for the specified user
    deposits = User_transaction.query.filter_by(user_id=user_id, type_tran='deposit').all()

    # Prepare the response data
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
    # Verify if the token is from a valid admin
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin  # Return the error response if token verification failed

    # Query to get all withdrawal transactions for the specified user
    withdrawals = User_transaction.query.filter_by(user_id=user_id, type_tran='withdraw').all()

    # Prepare the response data
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
    # Verify if the token is from a valid admin
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin  # Return the error response if token verification failed

    # Query to get all transactions for the specified user
    transactions = User_transaction.query.filter_by(user_id=user_id).all()

    # Prepare the response data
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

@admin.route('/levels/<int:level_id>', methods=['PUT'])
@jwt_required()
def update_level(level_id):
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin  

    level = Level.query.get(level_id)
    if not level:
        return jsonify({"msg": "Level not found"}), 404

    data = request.get_json()

    level.min_active_users = data.get('min_active_users', level.min_active_users)
    level.min_amount = data.get('min_amount', level.min_amount)
    level.profit_multiplier = data.get('profit_multiplier', level.profit_multiplier)

    db.session.commit()

    return jsonify({"msg": "Level updated successfully", "level_id": level.id}), 200


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
        "request_date": transaction.request_date,
        "hash_code": transaction.hash_code 
    } for transaction in unconfirmed_transactions]

    return jsonify({"unconfirmed_transactions": transactions_data}), 200


@admin.route('/confirm-transaction', methods=['POST'])
@jwt_required()  # Ensure only authenticated admins can access this route
def confirm_transaction():
    # Verify if the token is from a valid admin
    admin = verify_admin_token()
    if isinstance(admin, tuple):
        return admin  # Return the error response if token verification failed

    # Get the data from the request
    data = request.get_json()
    transaction_id = data.get('transaction_id')
    confirm = data.get('confirm')

    # Validate the input
    if transaction_id is None or confirm is None:
        return jsonify({"msg": "Transaction ID and confirmation status are required"}), 400

    # Find the transaction by ID
    transaction = User_transaction.query.filter_by(id=transaction_id).first()

    if not transaction:
        return jsonify({"msg": "Transaction not found"}), 404

    # Fetch the user associated with the transaction
    user = User.query.get(transaction.user_id)

    # If confirm is true, update the confirmation status, confirm_date, and admin_id
    if confirm:
            
        transaction.confirmed = True
        transaction.confirm_date = datetime.utcnow()  # Set confirmation date to current time
        transaction.admin_id = admin.id  # Set the admin who confirmed the transaction

        if transaction.type_tran == "deposit":
            
            # Create a new Investment entry based on the transaction details
            new_investment = Investment(
                user_id=transaction.user_id,
                amount=transaction.amount,
                start_time=datetime.utcnow(),  # Set the start time to now or a specific time
            )

            # Add the new investment to the session
            db.session.add(new_investment)

            # Check if the user's level needs to change and call `handle_level_change`
            if user:
                user.handle_level_change()
            else:
                return jsonify({"msg": "User associated with transaction not found"}), 404

        elif transaction.type_tran == "withdraw":
            result = withdraw_profit(transaction.user_id, transaction.amount)
            return jsonify(result)        

    else:
        transaction.confirmed = False  # Set confirmation to False if not confirmed

    db.session.commit()

    # Handle referral bonus logic if applicable
    if user and user.referred_by and Investment.query.filter_by(user_id=transaction.user_id).count() == 1:
        # Award referral bonus to the referrer
        referrer = User.query.get(user.referred_by)
        if referrer:
            referrer.referral_bonus += 5  # Add the bonus to the referrer's referral bonus field
            db.session.commit()

    return jsonify({
        "msg": f"Transaction {'confirmed' if confirm else 'not confirmed'} successfully",
        "transaction_id": transaction.id,
        "confirmed": transaction.confirmed,
        "confirm_date": transaction.confirm_date,
        "admin_id": transaction.admin_id  # Return the admin ID who confirmed the transaction
    }), 200


def withdraw_profit(user_id, amount_to_withdraw):
    # Fetch all investments for the user, ordered by start_time (oldest first)
    investments = Investment.query.filter(
        Investment.user_id == user_id
    ).order_by(Investment.start_time).all()

    user = User.query.get(user_id)

    total_withdrawn = 0
    remaining_amount = amount_to_withdraw
    transactions = []  # To store transaction history

    current_time = datetime.utcnow()

    for investment in investments:
        if remaining_amount <= 0:
            break  # Stop if requested amount has been withdrawn

        # Check if a cycle is complete and calculate the profit for that cycle
        if investment.is_cycle_complete():
            # Calculate profit since last withdrawal time or start time
            last_time = investment.last_withdraw_time or investment.start_time
            full_days_passed = (current_time - last_time).days
            new_cycles = full_days_passed // investment.cycle_length
            new_cycle_profit = investment.calculate_withdrawable_profit(new_cycles)
            
            # Update the withdrawable profit
            investment.withdrawable_profit += new_cycle_profit
            investment.last_withdraw_time = current_time  # Update last withdrawal time

        # Withdrawable profit now includes new cycle profit
        withdrawable_profit = investment.withdrawable_profit

        if withdrawable_profit > 0:
            # Determine how much can be withdrawn from this investment's withdrawable profit
            withdrawable_from_investment = min(remaining_amount, withdrawable_profit)
            
            # Withdraw the calculated amount
            remaining_amount -= withdrawable_from_investment
            total_withdrawn += withdrawable_from_investment

            # Reduce withdrawable profit and log transaction
            investment.withdrawable_profit -= withdrawable_from_investment
            transactions.append({
                'investment_id': investment.id,
                'withdrawn_profit': withdrawable_from_investment
            })

            # Update last withdrawal time and partial cycle reset if remaining profit exists
            if investment.withdrawable_profit == 0:
                investment.start_time = current_time  # Reset start_time only if all profit is withdrawn

        # Commit updates after each investment is processed
        db.session.commit()

    # If the requested withdrawal exceeds withdrawable profit, handle principal withdrawal
    if remaining_amount > 0:
        for investment in investments:
            if remaining_amount <= 0:
                break

            if investment.amount > 0:
                # Withdraw from the principal
                withdrawable_from_principal = min(remaining_amount, investment.amount)
                investment.amount -= withdrawable_from_principal
                remaining_amount -= withdrawable_from_principal
                total_withdrawn += withdrawable_from_principal

                # Log principal withdrawal transaction
                transactions.append({
                    'investment_id': investment.id,
                    'withdrawn_from_principal': withdrawable_from_principal
                })

                db.session.commit()
    
    #NOTE the admin side sould handel this
    #check if the user level is needed to be change
    user.handle_level_change()
    return {
        "msg": "Withdrawal completed",
        "total_withdrawn": total_withdrawn,
        "remaining_amount_to_withdraw": remaining_amount if remaining_amount > 0 else 0,
        "transactions": transactions
    }




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

        if user:
            messages_data.append({
                "message_id": message.message_id,
                "user_id": message.user_id,
                "username": user.username,
                "content": message.content,
                "created_at": message.date
            })

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

    parent_message = Message.query.get_or_404(parent_message_id)

    user_id = parent_message.user_id
  
    message = Message(
        user_id=user_id,  
        admin_id=admin.id,  
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

@admin.route('/investments', methods=['GET'])
@jwt_required()
def get_all_investments():
    admin = verify_admin_token()
    if isinstance(admin, dict):  
        return admin
    
    investments = Investment.query.all()
    
    investments_data = []
    for investment in investments:
        investments_data.append({
            "id": investment.id,
            "user_id": investment.user_id,
            "amount": investment.amount,
            "start_time": investment.start_time,
            "withdrawable_profit": investment.withdrawable_profit,
            "cycle_length": investment.cycle_length,
            "last_withdraw_time": investment.last_withdraw_time,
        })

    return jsonify({"investments": investments_data}), 200


@admin.route('/investment/update', methods=['PUT'])
@jwt_required()
def update_investment():
    admin = verify_admin_token()
    if isinstance(admin, dict):  
        return admin
    
    data = request.get_json()
    investment_id = data.get('id')
    new_amount = data.get('amount')
    
    investment = Investment.query.get(investment_id)
    if not investment:
        return jsonify({"msg": "Investment not found"}), 404

    investment.amount = new_amount
    investment.start_time = datetime.utcnow()
    
    db.session.commit()

    return jsonify({"msg": "Investment updated successfully"}), 200
