import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
import requests

app = Flask(__name__)

# 1. DATABASE SETUP (To remember who paid)
app.config['SQLALCHEMY_DATABASE_PATH'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    expiry_date = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# 2. AI SETUP
genai.configure(api_key="AIzaSyC9PW7CWbv-cLM7Z7lEq7OJAGQY9M1SjFs")
model = genai.GenerativeModel("gemini-1.5-flash")

# 3. CAMPAY/PAYMENT CONFIG (Get these from campay.net)
CAMPAY_TOKEN = "YOUR_CAMPAY_TOKEN" 

def get_payment_link(phone):
    # This function asks Campay for a payment link
    # For now, we will just send instructions to the user
    return "https://www.campay.net/pay/your-unique-link"

# 4. THE MAIN BOT LOGIC
@app.route("/bot", methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body', '').lower()
    from_number = request.values.get('From', '') # e.g. 'whatsapp:+237670000000'
    
    resp = MessagingResponse()
    msg = resp.message()

    # Find user in database
    user = User.query.filter_by(phone_number=from_number).first()

    # Check if user is new or expired
    if not user or user.expiry_date < datetime.utcnow():
        if not user:
            new_user = User(phone_number=from_number)
            db.session.add(new_user)
            db.session.commit()
        
        pay_link = get_payment_link(from_number)
        msg.body(f"Welcome to GCE Master Tutor! 🎓\n\nTo access 'A' grade explanations, please pay 500frs for 7 days access.\n\nClick here to pay with MTN/Orange: {pay_link}\n\nAfter paying, type 'DONE'.")
        return str(resp)

    # If they are paid, give them the AI answer
    try:
        chat = model.start_chat(history=[])
        ai_response = chat.send_message(incoming_msg)
        msg.body(ai_response.text)
    except Exception as e:
        msg.body("Ashia! Small network problem. Try again, mbanya!")

    return str(resp)

# 5. PAYMENT CONFIRMATION (Webhook)
@app.route("/payment-success", methods=['POST'])
def payment_success():
    # This is where Campay tells your bot "The student has paid!"
    data = request.json
    phone = data.get('external_reference') # You set this during payment
    
    user = User.query.filter_by(phone_number=phone).first()
    if user:
        user.expiry_date = datetime.utcnow() + timedelta(days=7)
        db.session.commit()
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)