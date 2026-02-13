import streamlit as st
from streamlit_autorefresh import st_autorefresh
import os
from database import *

try:
    from st_keyup import st_keyup
    HAS_KEYUP = True
except ImportError:
    HAS_KEYUP = False

# --- CONFIG ---
st.set_page_config(page_title="SkyPay Dashboard", page_icon="👩‍💻", layout="wide")
st_autorefresh(interval=3000, key="agent_refresh")
init_db()

# --- IMPROVED CSS FOR CARDS AND TOGGLES ---
st.markdown("""
    <style>
        /* 1. Styled Segmented Control (Tabs) */
        div[data-testid="stSegmentedControl"] {
            background-color: #f3f4f6;
            padding: 5px;
            border-radius: 12px;
            margin-bottom: 20px;
        }

        /* 2. Clickable Card Styles */
        div.stButton > button:first-child {
            width: 100%;
            height: auto;
            min-height: 75px;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            background-color: #ffffff;
            color: #111827 !important;
            text-align: left;
            font-size: 14px;
            white-space: pre-wrap !important;
            word-wrap: break-word !important;
            display: block !important;
            transition: all 0.2s ease;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        
        div.stButton > button:hover {
            border-color: #3b82f6;
            background-color: #f8fafc;
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }

        /* Highlight the card if it matches the active session */
        .active-card {
            border: 2px solid #3b82f6 !important;
            background-color: #eff6ff !important;
        }
    </style>
""", unsafe_allow_html=True)

def get_avatar(role):
    user_img = "assets/person.jpg"
    skypay_img = "assets/skypay_logo.jpg"
    if role == "user":
        return user_img if os.path.exists(user_img) else "user"
    else:
        return skypay_img if os.path.exists(skypay_img) else "assistant"

st.title("👩‍💻 Agent Dashboard")

if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

with st.sidebar:
    st.header("🔍 Ticket Explorer")
    
    # --- NEW: MODERN VIEW MODE TOGGLE ---
    mode = st.segmented_control(
        "Filter by Status",
        options=["🔥 Active", "📜 Closed"],
        default="🔥 Active",
        selection_mode="single",
        label_visibility="collapsed"
    )
    
    if HAS_KEYUP:
        search_query = st_keyup("Search Name, Email, or Ticket ID", key="ticket_search", placeholder="Start typing...")
    else:
        search_query = st.text_input("Search Name, Email, or Ticket ID", key="ticket_search")

    # Fetch data based on selected segment
    all_convos = get_escalated_conversations() if mode == "🔥 Active" else get_closed_conversations()
    
    # FILTER LOGIC
    filtered = []
    if search_query:
        q = search_query.lower()
        for c in all_convos:
            # c = (id, user_name, concern, ticket_id, user_email)
            if q in (c[1] or "").lower() or q in (c[3] or "").lower() or q in (c[4] or "").lower():
                filtered.append(c)
    else:
        filtered = all_convos

    st.caption(f"Showing {len(filtered)} {mode} tickets")
    st.divider()

    # --- CLICKABLE CARD LIST ---
    selected_data = None
    for convo in filtered:
        c_id, name, concern, t_id, email = convo[0], convo[1], convo[2], convo[3], convo[4]
        
        status_icon = "🔵" if mode == "🔥 Active" else "🔘"
        card_label = f"{status_icon} **{t_id}**\n👤 {name or 'Guest'}"
        
        # Clickable Card
        if st.button(card_label, key=f"btn_{c_id}"):
            st.session_state.selected_id = c_id
            st.rerun()
        
        if st.session_state.selected_id == c_id:
            selected_data = convo

# --- MAIN AREA ---
if selected_data:
    s_id, s_name, s_concern, s_tid, s_email = selected_data[0], selected_data[1], selected_data[2], selected_data[3], selected_data[4]
    
    st.subheader(f"💬 Ticket: {s_tid}")
    
    # Detail Header
    with st.container(border=True):
        col1, col2 = st.columns(2)
        col1.write(f"**Customer:** {s_name}")
        col1.write(f"**Email:** {s_email}")
        col2.write(f"**Topic:** {s_concern}")
        col2.write(f"**Status:** {mode}")

    if mode == "🔥 Active": 
        set_status(s_id, "human_active")
    
    # Message Thread
    st.write("---")
    for r, c in get_messages(s_id):
        if r != "system":
            with st.chat_message(r, avatar=get_avatar(r)):
                st.write(f"👩‍💻 (You): {c}" if r == "human" else c)
    
    # Actions
    if mode == "🔥 Active":
        reply = st.chat_input("Type your response...")
        if reply:
            add_message(s_id, "human", reply)
            st.rerun()
            
        st.divider()
        if st.button("✅ Resolve & Close Ticket", use_container_width=True, type="primary"):
            close_conversation(s_id)
            add_message(s_id, "system", "Agent closed this ticket.")
            st.session_state.selected_id = None
            st.rerun()
else:
    st.info("### ⬅️ Select a ticket to begin chatting")