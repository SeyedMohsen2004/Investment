# Seyed Mohsen Moosavi & Ali Amri
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Investment, User_transaction, db, Level
from app.scheduler import update_referral_profits
from app.utils import get_total_referral_profit, get_referral_profit_history
from datetime import datetime
from app.models import User

investment = Blueprint('investment', __name__)

def generate_wallet_address():
    return "TYkKWFnNBsKLsqopLktWfKY9PQm7vE5SJw"  # Placeholder for generated wallet address


# Route to create an investment
@investment.route('/create', methods=['POST'])
@jwt_required()
def create_investment():
    data = request.get_json()
    amount = data.get('amount')

    if not amount or amount <= 0:
        return jsonify({"msg": "Invalid investment amount"}), 400

    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    # Check if this is the user's first confirmed investment
    first_investment_amount = User_transaction.get_first_investment_amount(current_user_id)

    # If no previous confirmed investment is found, this is the first investment
    is_first_investment = first_investment_amount == 0.0

    # Enforce a minimum amount of 100 Tether only if it is the first investment
    if is_first_investment and amount < 100:
        return jsonify({"msg": "Minimum investment amount is 100 Tether for the first investment"}), 400

    # Generate a wallet address for the transaction
    wallet_address = generate_wallet_address()

    # Log the deposit request in User_transaction table
    new_transaction = User_transaction(
        user_id=current_user_id,
        type_tran="deposit",
        amount=amount,
        description="Deposit request",
    )
    db.session.add(new_transaction)
    db.session.commit()

    # Handle user level change if necessary
    # user.handle_level_change()

    return jsonify({
        "msg": "Deposit request logged successfully",
        "transaction_id": new_transaction.id,
        "wallet_address": wallet_address
    }), 201


@investment.route('/submit_hash', methods=['POST'])
@jwt_required()
def submit_hash():
    data = request.get_json()
    hash_code = data.get('hash_code')
    transaction_id = data.get('transaction_id')

    if not hash_code or not transaction_id:
        return jsonify({"msg": "Missing hash code or transaction ID"}), 400

    # Retrieve the transaction
    transaction = User_transaction.query.get(transaction_id)
    
    if not transaction:
        return jsonify({"msg": "Transaction not found"}), 404

    # Update the transaction with the hash code (without confirming it yet)
    transaction.hash_code = hash_code
    db.session.commit()

    return jsonify({"msg": "Hash code submitted successfully", "transaction_id": transaction.id}), 200


@investment.route('/transactions', methods=['GET'])
@jwt_required()
def get_transaction_history():
    current_user_id = get_jwt_identity()
    transactions = User_transaction.query.filter_by(user_id=current_user_id).all()

    # Prepare a response with a list of transactions
    transaction_list = [
        {
            'id': transaction.id,
            'type': transaction.type_tran,
            'amount': transaction.amount,
            'confirmed': transaction.confirmed,
            'confirm_date': transaction.confirm_date,
            'description': transaction.description,
            'request_date': transaction.request_date
        }
        for transaction in transactions
    ]

    return jsonify(transaction_list), 200

# Route to get total profit
@investment.route('/profit', methods=['GET'])
@jwt_required()
def get_total_profit():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    # Fetch all investments for the current user
    investments = Investment.query.filter_by(user_id=current_user_id).all()

    if not investments: 
        return jsonify({"msg": "No investments found"}), 404

    total_profit = 0
    total_amount = 0
    locked_profit = 0

    for investment in investments:
        # Check if the cycle is complete
        for investment in investments:
            result = investment.get_profit()
            
            # Accumulate profits and amounts
            total_profit += result['profit']
            locked_profit += result['locked_profit']
            total_amount += result['amount']
            
    referral_profit = get_total_referral_profit(current_user_id)

    return jsonify({
        "total_amount": total_amount,
        "withdrawable_profit": total_profit,
        "locked_profit": locked_profit,
        "referral_profit": referral_profit,
        "total_investments": len(investments)
    }), 200




@investment.route('/levels', methods=['GET'])
def get_levels():
    # Query all levels from the database
    levels = Level.query.all()

    # Format the response data
    levels_data = []
    for level in levels:
        level_info = {
            "id": level.id,
            "min_amount": level.min_amount,
            "min_referred_users": level.min_active_users,
            "profit_multiplier": level.profit_multiplier,
        }
        levels_data.append(level_info)

    # Send JSON response with level details
    return jsonify({"levels": levels_data}), 200

# Route to handle withdrawals
@investment.route('/withdraw', methods=['POST'])
@jwt_required()
def withdraw():
    user_id = get_jwt_identity()
    amount = request.json.get('amount')

    if not user_id or not amount:
        return jsonify({"msg": "Missing user ID or amount"}), 400

    # # Call the withdraw_profit function
    # result = withdraw_profit(user_id, amount)
    # return jsonify(result)

    new_transaction = User_transaction(
        user_id=user_id,
        type_tran="withdraw",
        amount=amount,
        description="Withdrawal request"
    )
    db.session.add(new_transaction)
    db.session.commit()

    return jsonify({
        "msg": "Withdrawal request logged successfully. Awaiting admin confirmation.",
        "transaction_id": new_transaction.id
    }), 201

#NOTE in the update we can have this route
@investment.route('/referral-profit', methods=['GET'])
@jwt_required()
def get_referral_profit():
    current_user_id = get_jwt_identity()

    # Fetch total referral profit
    total_profit = get_total_referral_profit(current_user_id)

    # Fetch referral profit history
    profit_history = get_referral_profit_history(current_user_id)

    return jsonify({
        'total_referral_profit': total_profit,
        'profit_history': profit_history
    }), 200

#this is for updating the referral profit tabele
@investment.route('/test-update-referral-profits', methods=['GET'])
@jwt_required()
def test_update_referral_profits():
    try:
        update_referral_profits()  # Manually call the background function
        return jsonify({"msg": "Referral profits updated successfully"}), 200
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500



