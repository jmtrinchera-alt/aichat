import streamlit as st
from streamlit_autorefresh import st_autorefresh
import os
from datetime import datetime
from database import *

# Ensure keyup is available for real-time search
try:
    from streamlit_keyup import st_keyup
    HAS_KEYUP = True
except ImportError:
    HAS_KEYUP = False

# --- CONFIG ---
st.set_page_config(page_title="SkyPay Agent Dashboard", page_icon="👩‍💻", layout="wide")
st_autorefresh(interval=3000, key="agent_refresh")
init_db()

# --- CSS FOR CARDS AND UI ---
st.markdown("""
    <style>
        /* Segmented Control Tabs */
        div[data-testid="stSegmentedControl"] {
            background-color: #f3f4f6;
            padding: 5px;
            border-radius: 12px;
            margin-bottom: 20px;
        }

        /* Sidebar Ticket Cards */
        div.stButton > button:first-child {
            width: 100%;
            height: auto;
            min-height: 85px;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            background-color: #ffffff;
            color: #111827 !important;
            text-align: left;
            display: block !important;
            transition: all 0.2s ease;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            margin-bottom: 10px;
        }
        
        div.stButton > button:hover {
            border-color: #023e8a;
            background-color: #f8fafc;
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }

        /* Resolution Action Card */
        .resolve-card {
            background-color: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
            border-left: 5px solid #22c55e;
        }

        [data-testid="stSidebar"] {
            background-color: #f9fafb;
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

def format_timestamp(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%b %d, %Y - %I:%M %p")
    except:
        return iso_str or "N/A"

st.title("👩‍💻 Agent Dashboard")

if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

with st.sidebar:
    st.header("🔍 Ticket Explorer")
    
    # Status Toggle
    mode = st.segmented_control(
        "Filter by Status",
        options=["🔥 Active", "📜 Closed"],
        default="🔥 Active",
        selection_mode="single",
        label_visibility="collapsed"
    )
    
    # --- REAL-TIME SEARCH FEATURE ---
    if HAS_KEYUP:
        # This triggers every keystroke
        search_query = st_keyup(
            "Search Name, Email, or Ticket ID", 
            key="ticket_search", 
            placeholder="Start typing to filter..."
        )
    else:
        search_query = st.text_input("Search Name, Email, or Ticket ID", key="ticket_search")

    # Fetch data based on mode
    all_convos = get_escalated_conversations() if mode == "🔥 Active" else get_closed_conversations()
    
    # Filter Logic (Instant feedback)
    filtered = []
    if search_query:
        q = search_query.lower()
        for c in all_convos:
            # c indices: 0:id, 1:name, 2:concern, 3:ticket_id, 4:email, 5:created_at
            name_txt = (c[1] or "").lower()
            tid_txt = (c[3] or "").lower()
            email_txt = (c[4] or "").lower()
            
            if q in name_txt or q in tid_txt or q in email_txt:
                filtered.append(c)
    else:
        filtered = all_convos

    st.caption(f"Showing {len(filtered)} {mode} tickets")
    st.divider()

    # --- TICKET LIST CARDS ---
    selected_data = None
    for convo in filtered:
        c_id, name, concern, t_id, email, created_at = convo
        
        status_icon = "🔵" if mode == "🔥 Active" else "🔘"
        card_label = f"{status_icon} **{t_id}**\n👤 {name or 'Guest'}\n📧 {email or 'No Email'}"
        
        if st.button(card_label, key=f"btn_{c_id}"):
            st.session_state.selected_id = c_id
            st.rerun()
        
        if st.session_state.selected_id == c_id:
            selected_data = convo

# --- MAIN CHAT AREA ---
if selected_data:
    s_id, s_name, s_concern, s_tid, s_email, s_created = selected_data
    
    st.subheader(f"💬 Ticket: {s_tid}")
    
    # Detailed Header Card with Escalation Time
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Customer:** {s_name}")
            st.write(f"**Email:** {s_email}")
            st.write(f"**Escalated:** {format_timestamp(s_created)}")
        with col2:
            st.write(f"**Topic:** {s_concern}")
            st.write(f"**Status:** {mode}")

    if mode == "🔥 Active": 
        set_status(s_id, "human_active")
    
    # Message History
    st.write("---")
    for r, c in get_messages(s_id):
        if r != "system":
            with st.chat_message(r, avatar=get_avatar(r)):
                st.write(f"👩‍💻 (You): {c}" if r == "human" else c)
    
    # Input Actions
    if mode == "🔥 Active":
        reply = st.chat_input("Type your response...")
        if reply:
            add_message(s_id, "human", reply)
            st.rerun()
            
        # Resolve Ticket Action Card
        st.markdown(f"""
            <div class="resolve-card">
                <h4 style="margin:0; color: #166534;">Finalize Ticket</h4>
                <p style="color: #374151; font-size: 14px;">Marking this as resolved will close the chat for the user and prompt them for a survey.</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("✅ Confirm Resolution & Close", use_container_width=True, type="primary"):
            close_conversation(s_id)
            add_message(s_id, "system", "Agent closed this ticket.")
            st.session_state.selected_id = None
            st.rerun()
else:
    st.info("### ⬅️ Select a ticket from the sidebar to begin assisting.")
