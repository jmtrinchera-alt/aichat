import streamlit as st
from streamlit_autorefresh import st_autorefresh
import os
import re
import time
from thefuzz import process, fuzz 
from groq import Groq 
from database import *

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

# CSS for FAQ buttons
st.markdown("""
    <style>
        div.stButton > button:first-child {
            width: 100%;
            height: auto;
            min-height: 70px;
            border-radius: 10px;
            text-align: left;
            font-size: 14px;
        }
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
# FULL PRESET ANSWERS (Restored)
# =========================
PRESET_ANSWERS = {
    "What is SkyPay?": """**What is SkyPay?** SkyPay (formerly known as SkyBridge Payment, Inc.) is a Philippines-based fintech company that specializes in payment gateway services and digital payment solutions. It operates primarily as a payment bridge connecting merchants, financial institutions, lenders, billers, and enterprise platforms.

**SkyPay Office Hours:** I couldn't find any publicly available information on the current office hours of SkyPay. As a support agent, I can tell you that we are available to assist customers during our business hours, which typically run from 9:00 AM to 6:00 PM Philippine Standard Time (GST).""",

    "Is SkyPay a scam?": """**Is SkyPay a scam?** No, SkyPay is a legitimate company. It is a publicly traded company listed on the OTC Market Group under the ticker symbol SKYPAY, and it is also a BSP-licensed fintech firm. As an SEC-registered company, SkyPay operates transparently and follows regulatory guidelines.""",

    "What are SkyPay office hours?": """I'm a Skypay support agent.

SkyPay is a digital payment platform that allows individuals and businesses to make secure, fast, and convenient transactions.

Our office hours are as follows:
**Monday to Friday: 9:00 AM to 6:00 PM**
Please note that these hours apply to our two primary office locations in Mandaluyong City.""",

    "What are SkyPay's services?": """As a Skypay support agent, I'm happy to inform you about the various services we offer:

* **Over-the-Counter (OTC) and Digital Payment Collections**
* **Cash Payouts**
* **Bill Payments**: We partner with over 200 biller partners.
* **Value-Added Services**: Buy Load, Top Up, Cash In.

**Disbursement Channels Supported:**
* **InstaPay**
* **PESONet**""",

    "How do I contact SkyPay support?": """To contact SkyPay support, you can reach us through the following channels:

* **Email:** You can email us at cs@skypay.ph for any payment-related concerns or questions.
* **Phone Numbers:** Please visit our official website to find the latest phone numbers and contact details.""",

    "How do I use SkyPay?": """**Using SkyPay:** To use SkyPay, follow these general steps:
1. Go to the website of the merchant or biller you want to pay.
2. Select SkyPay as your preferred payment method.
3. Follow the prompts to log in to your SkyPay account or enter your payment details.
4. Review and confirm your transaction.""",

    "Is SkyPay a loaning company?": """**Is SkyPay a loaning company?** No, SkyPay is not a loaning company. We are a payment solutions company that connects merchants, financial institutions, lenders, billers, and enterprise platforms to facilitate secure and convenient transactions. Any money received or collected via SkyPay originates from third-party loaning apps/companies or billers, not from us."""
}

# =========================
# Sidebar & Testing Tools (RESTORED)
# =========================
with st.sidebar:
    st.header("🧪 Testing Tools")
    if st.button("🚀 Simulate New Chat"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# =========================
# Context Logic
# =========================
OFF_TOPIC = "I'm sorry, but I can only answer inquiries regarding SkyPay services. I cannot assist with general knowledge questions."
UNSURE = "I'm not sure about that yet, but I can help escalate it."

def get_fuzzy_context(query):
    try:
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
        email_input = st.text_input("What is your email address?", placeholder="e.g. name@domain.com")
        topic = st.selectbox("Type of concern?", ["Inquiries", "Partnerships", "Others"])
        
        if st.form_submit_button("Start Chat"):
            if not name.strip() or not email_input.strip() or not is_valid_email(email_input):
                st.error("Please provide a valid name and email.")
            else:
                update_onboarding(cid, name, topic, email_input)
                add_message(cid, "system", f"User: {name} ({email_input}), Concern: {topic}")
                st.rerun()
    st.stop()

# =========================
# CLOSED STATE
# =========================
if status == 'closed':
    st.title(f"🤖 Goodbye, {user_name}!")
    st.success(f"Ticket {ticket_id} has been resolved.")
    for r, c in get_messages(cid):
        if r != "system":
            with st.chat_message(r, avatar=get_avatar(r)): 
                st.write(f"👩‍💻 {c}" if r == "human" else c)
    st.stop()

# =========================
# CHAT INTERFACE
# =========================
st.title(f"🤖 Hello, {user_name}!")
st.subheader(f"Ticket: {ticket_id}")

human_active = status in ['escalated', 'human_active']

if not human_active:
    st.markdown("### FAQs")
    cols = st.columns(4)
    presets = list(PRESET_ANSWERS.keys())
    for i, q in enumerate(presets):
        if cols[i % 4].button(q): st.session_state.curr_prompt = q

# --- DISPLAY MESSAGES & DETECT REFUSALS ---
db_msgs = get_messages(cid)
show_esc = False

# RESTORED FULL KEYWORD LIST
refusal_keywords = [
    "i'm sorry", "cannot assist", "support agent", "escalate", 
    "unrelated", "can only assist", "not sure", "don't have information", 
    "no information", "unable to answer", "don't know", "unsure",
    "click the button", "button below", "talk to support agent"
]

for r, c in db_msgs:
    if r != "system":
        with st.chat_message(r, avatar=get_avatar(r)):
            st.write(f"👩‍💻 {c}" if r == "human" else c)
    
    if r == "ai":
        clean_content = c.lower()
        if any(k in clean_content for k in refusal_keywords) or OFF_TOPIC.lower() in clean_content or UNSURE.lower() in clean_content:
            show_esc = True

if human_active:
    st.warning("⚠️ **Note:** This has now been escalated to a Support Agent. Official work hours: 9:00 AM - 6:00 PM.")
else:
    st.info("💡 **Tip:** SkyPay AI is powered by Groq and responds instantly.")

# =========================
# INPUT HANDLING
# =========================
u_input = st.chat_input("Message the agent..." if human_active else "Ask about Skypay...")
prompt = st.session_state.get("curr_prompt") or u_input

if prompt:
    if "curr_prompt" in st.session_state: del st.session_state["curr_prompt"]
    
    # 1. Save User Message
    add_message(cid, "user", prompt)
    
    if not human_active:
        if prompt in PRESET_ANSWERS:
            with st.spinner("Skypay AI is thinking..."):
                time.sleep(1)
                add_message(cid, "ai", PRESET_ANSWERS[prompt])
        else:
            # 2. History & Context
            history = get_messages(cid)
            is_ongoing_convo = len(history) > 3 

            ctx = get_fuzzy_context(prompt)
            skypay_keywords = ["skypay", "skybridge", "payment", "bills", "loan", "support", "office", "scam", "legit", "money"]
            
            # 3. Guardrail Logic: Auto-refuse if context is missing and query is off-brand
            if not ctx and not any(k in prompt.lower() for k in skypay_keywords) and not is_ongoing_convo:
                add_message(cid, "ai", OFF_TOPIC)
            else:
                with st.spinner("Skypay AI is working on your answer..."):
                    try:
                        # REFINED SYSTEM PROMPT with strict trigger logic
                        sys_p = (
                            f"You are a strict customer support agent for SkyPay. "
                            f"Your ONLY purpose is to answer questions about Skypay services, payments, and office details. "
                            f"Context: {ctx}. "
                            f"RULES:\n"
                            f"1. Use the Context to answer naturally.\n"
                            f"2. If the user asks general knowledge questions unrelated to Skypay, YOU MUST REPLY: '{OFF_TOPIC}'\n"
                            f"3. If the answer is NOT in the context or you are UNSURE, YOU MUST REPLY: '{UNSURE}'\n"
                            f"4. NEVER say 'I have escalated this'. Users must click the button manually."
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
                        st.error(f"Error: {e}")

    st.rerun()

# =========================
# ESCALATION
# =========================
if not human_active and show_esc:
    st.divider()
    st.info("Need more specific help? You can connect with a human agent.")
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