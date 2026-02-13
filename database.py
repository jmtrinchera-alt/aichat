import os
import pymongo
from datetime import datetime, timedelta
import uuid
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =========================
# 1. Connection Logic
# =========================
@st.cache_resource
def get_db():
    # Looks for "MONGO_URI" in your Streamlit Secrets
    client = pymongo.MongoClient(st.secrets["MONGO_URI"])
    return client["skypay_support"]

def init_db():
    # MongoDB creates collections automatically on first insert
    pass

# =========================
# 2. Ticket & Conversation Management
# =========================
def generate_ticket_id():
    db = get_db()
    # Count documents to generate a sequential ID
    count = db.conversations.count_documents({}) + 1
    # Philippines Time (UTC+8) for Ticket ID generation
    pht_now = datetime.utcnow() + timedelta(hours=8)
    date_str = pht_now.strftime("%Y%m%d")
    return f"SKY-{date_str}-{count:04d}"

def create_conversation():
    db = get_db()
    cid = str(uuid.uuid4())
    tid = generate_ticket_id()
    
    # Philippine Time for creation timestamp
    pht_now = datetime.utcnow() + timedelta(hours=8)
    
    doc = {
        "id": cid,
        "ticket_id": tid,
        "status": "onboarding",
        "created_at": pht_now.isoformat(),
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
    # Use Philippine Time (UTC+8) for message timestamps
    pht_now = datetime.utcnow() + timedelta(hours=8)
    msg = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "timestamp": pht_now.isoformat()
    }
    db.messages.insert_one(msg)

# =========================
# 3. Data Retrieval
# =========================
def get_messages(conversation_id):
    db = get_db()
    cursor = db.messages.find({"conversation_id": conversation_id}).sort("timestamp", 1)
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

def set_status(conversation_id, status):
    db = get_db()
    db.conversations.update_one({"id": conversation_id}, {"$set": {"status": status}})

def get_escalated_conversations():
    db = get_db()
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

# =========================
# 4. Email Notification (With Time Fix)
# =========================
def send_escalation_email(ticket_id, user_name, user_email, concern):
    # Credentials from Streamlit Secrets
    sender_email = st.secrets["EMAIL_USER"]
    password = st.secrets["EMAIL_PASS"]
    receiver_email = "jm.trinchera@skypay.ph" #

    # FIX: Manually add 8 hours for Philippine Time
    pht_time = datetime.utcnow() + timedelta(hours=8)
    pht_str = pht_time.strftime('%Y-%m-%d %I:%M %p')

    subject = f"CHAT ESCALATION: {ticket_id} - {user_name}"
    body = f"""
    🚨 NEW CHAT ESCALATION
    
    Ticket ID: {ticket_id}
    Customer Name: {user_name}
    Customer Email: {user_email}
    Concern: {concern}
    Timestamp: {pht_str} (PHT)
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
