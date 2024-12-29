from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from app.models import Investment, User, ReferralProfit, db


def update_referral_profits():
    from datetime import datetime

    users = User.query.all()  # Get all users
    for user in users:
        if user.referred_by:  # Check if the user was referred by someone
            referrer = User.query.get(user.referred_by)
            if not referrer:
                continue

            # Calculate total profit (locked + withdrawable) for the referred user
            investments = Investment.query.filter_by(user_id=user.id).all()
            total_profit = sum(
                inv.get_profit()['profit'] + inv.get_profit()['locked_profit']
                for inv in investments
            )

            # Calculate the 1% referral profit
            referral_profit = total_profit * 0.01

            # Check if there is already an entry in the ReferralProfit table for this referrer and referred user
            existing_referral = ReferralProfit.query.filter_by(
                referrer_id=referrer.id, referred_user_id=user.id
            ).first()

            if existing_referral:
                # Update the existing referral profit
                existing_referral.profit_amount = referral_profit
                existing_referral.timestamp = datetime.utcnow()
            else:
                # Add a new referral profit entry if it doesn't exist
                new_referral_profit = ReferralProfit(
                    referrer_id=referrer.id,
                    referred_user_id=user.id,
                    profit_amount=referral_profit,
                    timestamp=datetime.utcnow(),
                )
                db.session.add(new_referral_profit)

    db.session.commit()  # Commit the changes to the database
def start_scheduler():
    """Starts the scheduler to run tasks at regular intervals."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=update_referral_profits, trigger="interval", days=1)
    scheduler.start()