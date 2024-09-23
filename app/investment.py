from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Investment, User_transaction, db
from datetime import datetime
from app.models import User

investment = Blueprint('investment', __name__)

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

    # Log the deposit request in the user_transactions table
    new_transaction = User_transaction(
        user_id=current_user_id,
        type_tran="deposit",
        amount=amount,
        description="Deposit request"
    )
    db.session.add(new_transaction)
    db.session.commit()


    #NOTE to send this on admin side to check it if every think is okey...
     # Check if the user was referred by someone and this is their first deposit
    # if user.referred_by and Investment.query.filter_by(user_id=current_user_id).count() == 0:
    #     # Award referral bonus to the referrer
    #     referrer = User.query.get(user.referred_by)
    #     if referrer:
    #         referrer.referral_bonus += 5  # Add the bonus to the referrer's referral bonus field
    #         db.session.commit()


    return jsonify({"msg": "Deposit request logged successfully", "transaction_id": new_transaction.id}), 201

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
        if investment.is_cycle_complete():
            # Add withdrawable profit for completed cycles
            result = investment.get_profit()
            total_profit += result['profit']
            total_amount += result['amount']
        else:
            # Add locked profit for incomplete cycles
            locked_profit += investment.get_profit()['locked_profit']
            total_amount += investment.get_profit()['amount']

    return jsonify({
        "total_amount": total_amount,
        "withdrawable_profit": total_profit,
        "locked_profit": locked_profit,
        "total_investments": len(investments)
    }), 200

# Route to handle withdrawals
@investment.route('/withdraw', methods=['POST'])
@jwt_required()
def withdraw():
    user_id = get_jwt_identity()
    amount = request.json.get('amount')

    if not user_id or not amount:
        return jsonify({"msg": "Missing user ID or amount"}), 400

    # Call the withdraw_profit function
    result = withdraw_profit(user_id, amount)
    return jsonify(result)

def withdraw_profit(user_id, amount_to_withdraw):
    # Fetch all investments for the user, ordered by start_time (oldest first)
    investments = Investment.query.filter(
        Investment.user_id == user_id
    ).order_by(Investment.start_time).all()

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

    return {
        "msg": "Withdrawal completed",
        "total_withdrawn": total_withdrawn,
        "remaining_amount_to_withdraw": remaining_amount if remaining_amount > 0 else 0,
        "transactions": transactions
    }
