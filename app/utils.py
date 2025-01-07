from app.models import ReferralProfit

def get_total_referral_profit(user_id):
    """Calculates the total referral profit for a user."""
    total_profit = sum(profit.profit_amount for profit in ReferralProfit.query.filter_by(referrer_id=user_id))
    return float(total_profit)


def get_referral_profit_history(user_id):
    """Fetches the referral profit history for a user."""
    profit_history = [
        {
            'referred_user': profit.referred_user.username,
            'profit_amount': profit.profit_amount,
            'timestamp': profit.timestamp
        }
        for profit in ReferralProfit.query.filter_by(referrer_id=user_id)
    ]
    return profit_history