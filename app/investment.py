from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Investment, db
from datetime import datetime
from app.models import User


investment = Blueprint('investment', __name__)

@investment.route('/create', methods=['POST'])
@jwt_required()
def create_investment():
    data = request.get_json()
    amount = data.get('amount')

    if not amount or amount <= 0:
        return jsonify({"msg": "Invalid investment amount"}), 400

    current_user_id = get_jwt_identity()
    new_investment = Investment(user_id=current_user_id, amount=amount)
    db.session.add(new_investment)
    db.session.commit()

    return jsonify({"msg": "Investment created successfully", "investment_id": new_investment.id}), 201

@investment.route('/profit', methods=['GET'])
@jwt_required()
def get_total_profit():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    # Fetch all confirmed investments for the current user
    confirmed_investments = Investment.query.filter_by(user_id=current_user_id, is_confirmed=True).all()

    if not confirmed_investments:
        return jsonify({"msg": "No confirmed investments found"}), 404

    total_profit = 0
    total_amount = 0
    locked_profit = 0

    for investment in confirmed_investments:
        if investment.is_cycle_complete():
            # Cycle complete, profit can be withdrawn
            result = investment.get_profit()
            total_profit += result['profit']
            total_amount += result['amount']
        else:
            # Cycle not complete, profit is locked
            locked_profit += investment.get_profit()['profit']

    return jsonify({
        "total_amount": total_amount,
        "withdrawable_profit": total_profit,
        "locked_profit": locked_profit,
        "total_investments": len(confirmed_investments)
    }), 200
