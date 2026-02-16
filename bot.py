import streamlit as st
from streamlit_autorefresh import st_autorefresh
import os
import re
import time
from thefuzz import process, fuzz 
from groq import Groq 
from database import *

# =========================
# Hide Streamlit Branding
# =========================
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            [data-testid="stStatusWidget"] {display: none;}
            .stActionButton {display: none;}
            button[title="View fullscreen"] {display: none;}
            .main .block-container {
                padding-bottom: 0px;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# =========================
# Page Configuration
# =========================
st.set_page_config(page_title="Skypay Support Bot", page_icon="🤖", layout="wide")
st_autorefresh(interval=3000)

# Initialize DB
init_db()

# Initialize Groq Client
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("🚨 Groq API Key is missing. Please check .streamlit/secrets.toml")
    st.stop()

# CSS for UI Styling
st.markdown(f"""
    <style>
        :root {{
            --background-color: #ffffff;
            --secondary-background-color: #eeeeee;
            --primary-color: #023e8a;
        }}

        .stApp {{ 
            background-color: #ffffff !important; 
        }}
        
        .stAppHost, .stApp, .stApp * {{
            color: #000000;
        }}

        h1, h2, h3, [data-testid="stHeader"], [data-testid="stWidgetLabel"] p {{
            color: #000000 !important;
            font-weight: 700 !important;
        }}

        div[data-baseweb="input"], 
        div[data-baseweb="select"] > div, 
        div[data-baseweb="base-input"] {{
            background-color: #eeeeee !important; 
            border: 1px solid #cccccc !important;
            border-radius: 8px !important;
        }}

        input, textarea, [data-testid="stSelectbox"] div {{
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
        }}

        [data-testid="stChatInput"] {{
            background-color: #ffffff !important;
            border-top: 1px solid #eeeeee !important;
            padding-top: 10px !important;
        }}

        [data-testid="stChatInput"] textarea {{
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 2px solid #023e8a !important; 
            border-radius: 12px !important;
            -webkit-text-fill-color: #000000 !important;
        }}

        div.stButton > button, [data-testid="stForm"] button {{
            background-color: #023e8a !important; 
            border: 2px solid #023e8a !important; 
            border-radius: 8px !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
            color: #ffffff !important;
            font-weight: 600 !important;
        }}

        div.stButton > button p, [data-testid="stForm"] button p {{
            color: #ffffff !important;
        }}

        div.stButton > button:hover, [data-testid="stForm"] button:hover {{
            background-color: #28a745 !important; 
            border-color: #28a745 !important;
            color: #ffffff !important;
        }}

        [data-testid="stChatMessageContent"] p {{ 
            color: #000000 !important; 
        }}
        
        .stChatMessage:has([data-testid="chatAvatarIcon-user"]) {{
            background-color: #7dcef4 !important;
        }}
        
        .stChatMessage:has([data-testid="chatAvatarIcon-assistant"]) {{
            background-color: #f1f3f4 !important;
        }}

        /* ESCALATION BOX */
        .escalation-box {{
            border: 1px solid #7dcef4 !important;
            border-radius: 10px;
            padding: 15px;
            background-color: #f0faff;
            margin: 10px 0;
            color: #000000 !important;
            font-weight: 500;
        }}

        /* YELLOW ESCALATION STATUS CARD */
        .escalation-active-card {{
            background-color: #fffbeb;
            border: 1px solid #fde68a;
            border-radius: 10px;
            padding: 15px;
            color: #92400e;
            text-align: center;
            margin-bottom: 20px;
            font-weight: 600;
        }}

        .resolved-card-container {{
            background-color: #ffffff;
            border: 2px solid #28a745;
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            margin: 20px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}

        [data-testid="stSidebar"] {{ 
            background-color: #023e8a !important; 
        }}
        
        [data-testid="stSidebar"] * {{
            color: #ffffff !important;
        }}
        
        [data-testid="stSidebar"] button p {{
            color: #ffffff !important;
        }}
    </style>
""", unsafe_allow_html=True)

# =========================
# Helper Functions
# =========================
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def get_avatar(role):
    user_img = "assets/person.jpg"
    skypay_img = "assets/skypay_logo.jpg"
    if role == "user":
        return user_img if os.path.exists(user_img) else "user"
    else:
        return skypay_img if os.path.exists(skypay_img) else "assistant"

# =========================
# CONSTANTS & PRESETS
# =========================
OFF_TOPIC = "I'm sorry, but I can only answer inquiries regarding SkyPay services. I cannot assist with general knowledge questions."
UNSURE = "I'm not sure about that yet, but I can help escalate it."

PRESET_ANSWERS = {
    "What is SkyPay?": "SkyPay is a Philippines-based fintech company specializing in payment gateway services. We connect merchants, financial institutions, and billers.",
    "Is SkyPay a scam?": "No, SkyPay is a legitimate, BSP-licensed fintech firm and SEC-registered company.",
    "What are SkyPay office hours?": "Our office hours are Monday to Friday: 9:00 AM to 6:00 PM Philippine Standard Time.",
    "What are SkyPay's services?": "We offer OTC and Digital Collections, Cash Payouts, Bill Payments (200+ partners), and Disbursement via InstaPay/PESONet.",
    "How do I contact SkyPay support?": "Email us at cs@skypay.ph for any payment-related concerns.",
    "Is SkyPay a loaning company?": "No, SkyPay is a payment solution provider. We facilitate payments for third-party lenders but do not issue loans ourselves."
}

def get_fuzzy_context(query):
    try:
        if not os.path.exists("knowledge.txt"): return ""
        with open("knowledge.txt", "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if len(l.strip()) > 10]
        matches = process.extract(query, lines, scorer=fuzz.token_set_ratio, limit=3)
        return "\n".join([m[0] for m in matches if m[1] > 60])
    except: return ""

# =========================
# Session Setup
# =========================
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = create_conversation()
cid = st.session_state.conversation_id
status, user_name, concern, ticket_id, user_email = get_conversation_data(cid)

# =========================
# ONBOARDING FLOW
# =========================
if status == 'onboarding':
    st.subheader("👋 Welcome to Skypay Support!")
    with st.form("onboarding"):
        name = st.text_input("What is your name?")
        email_input = st.text_input("What is your email address?")
        topic = st.selectbox("Type of concern?", ["Inquiries", "Partnerships", "Others"])
        if st.form_submit_button("Start Chat"):
            if not name.strip() or not email_input.strip() or not is_valid_email(email_input):
                st.error("Please provide a valid name and email.")
            else:
                update_onboarding(cid, name, topic, email_input)
                add_message(cid, "system", f"User: {name}, Email: {email_input}")
                st.rerun()
    st.stop()

# =========================
# CHAT INTERFACE
# =========================
st.title(f"🤖 Hello, {user_name}!")
st.caption(f"Ticket ID: **{ticket_id}**") 

# Define the closed states
is_closed = status in ['resolved', 'closed']
human_active = status in ['escalated', 'human_active']

# Sidebar Testing Tools & TIPS (Features Preserved)
with st.sidebar:
    st.markdown("### 💡 Support Tips")
    st.info("""
    * **Be Specific:** Mention transaction IDs if you have them.
    * **Office Hours:** We're active Mon-Fri, 9AM-6PM.
    * **Privacy:** Don't share your full password or OTP.
    """)
    st.divider()
    if st.button("🚀 Simulate New Chat"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# Display FAQ Buttons
if not human_active and not is_closed:
    st.markdown("### FAQs")
    cols = st.columns(3)
    for i, q in enumerate(list(PRESET_ANSWERS.keys())):
        if cols[i % 3].button(q): st.session_state.curr_prompt = q

# --- DISPLAY MESSAGES ---
db_msgs = get_messages(cid)
show_esc = False

for r, c in db_msgs:
    if r != "system":
        with st.chat_message(r, avatar=get_avatar(r)):
            st.write(f"👩‍💻 {c}" if r == "human" else c)

if db_msgs:
    last_role, last_content = db_msgs[-1]
    if last_role == "ai":
        is_refusal = (
            last_content.strip() == OFF_TOPIC or 
            last_content.strip() == UNSURE or 
            "cannot assist" in last_content.lower() or
            "not sure" in last_content.lower()
        )
        if is_refusal:
            show_esc = True

# Yellow Escalation Card
if human_active:
    st.markdown("""
        <div class="escalation-active-card">
            ⚠️ This chat is escalated to a Support Agent (9AM - 6PM).
        </div>
    """, unsafe_allow_html=True)

# =========================
# INPUT HANDLING
# =========================
if is_closed:
    # --- IMPROVED RESOLVED UI (Survey Button) ---
    st.markdown("---")
    st.markdown(f"""
        <div class="resolved-card-container">
            <h2 style="color: #28a745; margin-bottom: 10px;">✅ Conversation Resolved</h2>
            <p style="color: #1a1a1a; font-size: 1.1em;">
                Ticket ID: <strong>{ticket_id}</strong>
            </p>
            <p style="color: #666; margin-bottom: 20px;">
                This support session has ended. We hope your inquiry was handled to your satisfaction.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Satisfaction Survey Button (Not linked yet)
    if st.button("📝 Take a satisfaction survey", type="primary", use_container_width=True):
        pass
        
    st.chat_input("Chat disabled - Ticket Closed", disabled=True)
else:
    # Tip placed at the bottom, above chat field
    if not human_active:
        st.info("💡 **Tip:** SkyPay AI might take a few moments to process your inquiry and provide the most accurate information.")
    
    u_input = st.chat_input("Message the agent..." if human_active else "Ask about Skypay...")
    prompt = st.session_state.get("curr_prompt") or u_input

    if prompt:
        if "curr_prompt" in st.session_state: del st.session_state["curr_prompt"]
        add_message(cid, "user", prompt)
        
        if not human_active:
            if prompt in PRESET_ANSWERS:
                with st.spinner("Skypay AI is thinking..."):
                    time.sleep(1)
                    add_message(cid, "ai", PRESET_ANSWERS[prompt])
            else:
                history = get_messages(cid)
                is_ongoing_convo = len(history) > 3 
                ctx = get_fuzzy_context(prompt)
                skypay_keywords = ["skypay", "skybridge", "payment", "bills", "loan", "support", "office", "scam", "legit", "money"]
                
                if not ctx and not any(k in prompt.lower() for k in skypay_keywords) and not is_ongoing_convo:
                    with st.spinner("Reviewing inquiry..."):
                        time.sleep(1)
                        add_message(cid, "ai", OFF_TOPIC)
                else:
                    with st.spinner("Skypay AI is working on your answer..."):
                        try:
                            sys_p = (
                                f"You are a strict customer support agent for SkyPay. "
                                f"Your ONLY purpose is to answer questions about Skypay services. "
                                f"Context: {ctx}. "
                                f"RULES:\n"
                                f"1. Use the Context to answer naturally.\n"
                                f"2. If unrelated, reply: '{OFF_TOPIC}'\n"
                                f"3. If unsure, reply: '{UNSURE}'"
                            )
                            msgs = [{"role": "system", "content": sys_p}]
                            for r, c in history:
                                if r in ["user", "ai", "human"]:
                                    role_map = "assistant" if r in ["ai", "human"] else "user"
                                    msgs.append({"role": role_map, "content": c})
                            completion = client.chat.completions.create(
                                model="llama-3.1-8b-instant", 
                                messages=msgs,
                                temperature=0.1, 
                                max_tokens=500
                            )
                            reply = completion.choices[0].message.content
                            add_message(cid, "ai", reply)
                        except Exception as e:
                            st.error(f"Error calling Groq API: {e}")
        st.rerun()

# =========================
# ESCALATION
# =========================
if not human_active and not is_closed and show_esc:
    st.divider()
    st.markdown("""
        <div class="escalation-box">
            I didn't quite get that. Would you like to talk to a Support Agent?
        </div>
    """, unsafe_allow_html=True)
    if st.button("👩‍💻 Talk to a Support Agent"):
        set_status(cid, "escalated")
        add_message(cid, "system", "User requested human agent. Support notified.")
        with st.spinner("Notifying support team via email..."):
            success = send_escalation_email(ticket_id, user_name, user_email, concern)
            if success:
                st.toast(f"Ticket {ticket_id} escalated!", icon="📧")
            else:
                st.error("Failed to send email alert. Please check connection.")
        st.rerun()
