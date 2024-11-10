# Seyed Mohsen Moosavi & Ali Amri
# app/userMessage.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Message

user_messages = Blueprint('user_messages', __name__)

# API برای دریافت پیام‌های کاربر
@user_messages.route('/messages', methods=['GET'])  # تغییر مسیر به /messages
@jwt_required()
def get_user_messages():
    current_user_id = get_jwt_identity()  # دریافت ID کاربر از توکن
    messages = Message.query.filter_by(user_id=current_user_id).all()
    
    message_data = [{
        'message_id': msg.message_id,
        'content': msg.content,
        'date': msg.date,
        'seen': msg.seen,
        'parent_message_id': msg.parent_message_id
    } for msg in messages]

    return jsonify(message_data), 200

# API برای ارسال پیام توسط کاربر
@user_messages.route('/messages', methods=['POST'])  # تغییر مسیر به /messages
@jwt_required()
def send_user_message():
    current_user_id = get_jwt_identity()  # دریافت ID کاربر از توکن
    data = request.json
    content = data.get('content')

    if not content:
        return jsonify({"msg": "Content cannot be empty"}), 400  # بررسی محتوای خالی

    message = Message(
        user_id=current_user_id,  # استفاده از ID کاربر
        admin_id=None,  # چون پیام از طرف کاربر ارسال می‌شود، admin_id خالی می‌ماند
        content=content,
        seen=False
    )
    
    db.session.add(message)
    db.session.commit()

    return jsonify({"msg": "Message sent successfully"}), 201
