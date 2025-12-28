import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai

app = Flask(__name__)

# 1. DATABASE SETUP - Fixed the key name here
# This will create a file called users.db on Render
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(30), unique=True, nullable=False)
    expiry_date = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()

# 2. AI SETUP - Reading from Environment Variables (Safer!)
GOOGLE_API_KEY = os.environ.get("GOOGLE_AI_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

SYSTEM_INSTRUCTION = "You are the Cameroon GCE Master Tutor. Use 'Mboko' slang, be encouraging, and use Cameroonian examples."
model = genai.GenerativeModel(
    "gemini-1.5-flash", system_instruction=SYSTEM_INSTRUCTION)

# 3. BOT LOGIC


@app.route("/bot", methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body', '').lower()
    from_number = request.values.get('From', '')

    resp = MessagingResponse()

    # Check User Payment Status
    user = User.query.filter_by(phone_number=from_number).first()

    # FOR TESTING: If user is new, give them 1 day free access
    if not user:
        user = User(phone_number=from_number,
                    expiry_date=datetime.utcnow() + timedelta(days=1))
        db.session.add(user)
        db.session.commit()

    if user.expiry_date < datetime.utcnow():
        resp.message(
            "Ashia mbanya! Your access has expired. Please pay 500frs to continue. [Payment Link Here]")
        return str(resp)

    try:
        response = model.generate_content(incoming_msg)
        resp.message(response.text)
    except Exception as e:
        resp.message("A-yi-ee! I had a small glitch. Try again!")

    return str(resp)


# 4. THE PORT FIX - This is why it 'exited early'
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
