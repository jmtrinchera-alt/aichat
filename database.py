import os
import pymongo
from datetime import datetime
import uuid
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Connect to MongoDB
# We use @st.cache_resource so we don't reconnect on every rerun
@st.cache_resource
def get_db():
    # This looks for the "MONGO_URI" inside your secrets
    client = pymongo.MongoClient(st.secrets["MONGO_URI"])
    return client["skypay_support"]

def init_db():
    # MongoDB is schemaless, so we don't need to create tables manually.
    pass

def generate_ticket_id():
    db = get_db()
    # Count documents to generate a sequential ID
    count = db.conversations.count_documents({}) + 1
    date_str = datetime.now().strftime("%Y%m%d")
    return f"SKY-{date_str}-{count:04d}"

def create_conversation():
    db = get_db()
    cid = str(uuid.uuid4())
    tid = generate_ticket_id()
    
    doc = {
        "id": cid,
        "ticket_id": tid,
        "status": "onboarding",
        "created_at": datetime.now().isoformat(),
        "user_name": None,
        "concern": None,
        "user_email": None
    }
    db.conversations.insert_one(doc)
    return cid

def update_onboarding(cid, name, concern, email):
    db = get_db()
    db.conversations.update_one(
        {"id": cid},
        {"$set": {"user_name": name, "concern": concern, "user_email": email, "status": "bot"}}
    )

def add_message(conversation_id, role, content):
    db = get_db()
    msg = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    db.messages.insert_one(msg)

def get_messages(conversation_id):
    db = get_db()
    # Find messages for this conversation and sort by time
    cursor = db.messages.find({"conversation_id": conversation_id}).sort("timestamp", 1)
    # Return as list of (role, content) tuples to match your existing app logic
    return [(doc["role"], doc["content"]) for doc in cursor]

def get_conversation_data(conversation_id):
    db = get_db()
    doc = db.conversations.find_one({"id": conversation_id})
    if doc:
        return (
            doc.get("status", "onboarding"),
            doc.get("user_name", "Guest"),
            doc.get("concern", "General"),
            doc.get("ticket_id", "N/A"),
            doc.get("user_email", "N/A")
        )
    return "onboarding", "Guest", "General", "N/A", "N/A"

def get_conversation_status(conversation_id):
    db = get_db()
    doc = db.conversations.find_one({"id": conversation_id}, {"status": 1})
    if doc:
        return doc.get("status")
    return None

def set_status(conversation_id, status):
    db = get_db()
    db.conversations.update_one({"id": conversation_id}, {"$set": {"status": status}})

def get_escalated_conversations():
    db = get_db()
    # Fetch active tickets for the agent dashboard
    cursor = db.conversations.find(
        {"status": {"$in": ["escalated", "human_active"]}}
    ).sort("created_at", -1)
    
    return [
        (doc["id"], doc.get("user_name"), doc.get("concern"), doc.get("ticket_id"), doc.get("user_email"))
        for doc in cursor
    ]

def get_closed_conversations():
    db = get_db()
    cursor = db.conversations.find({"status": "closed"}).sort("created_at", -1)
    return [
        (doc["id"], doc.get("user_name"), doc.get("concern"), doc.get("ticket_id"), doc.get("user_email"))
        for doc in cursor
    ]

def close_conversation(conversation_id):
    set_status(conversation_id, "closed")

def send_escalation_email(ticket_id, user_name, user_email, concern):
    # Get email credentials from secrets
    sender_email = st.secrets["EMAIL_USER"]
    password = st.secrets["EMAIL_PASS"]
    receiver_email = "jm.trinchera@skypay.ph"

    subject = f"CHAT ESCALATION: {ticket_id} - {user_name}"
    body = f"""
    🚨 NEW CHAT ESCALATION
    
    Ticket ID: {ticket_id}
    Customer Name: {user_name}
    Customer Email: {user_email}
    Concern: {concern}
    Timestamp: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}
    """

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False