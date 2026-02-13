import streamlit as st
from groq import Groq
from database import get_messages, add_message, get_conversation_status, create_conversation

st.set_page_config(page_title="Skypay Support", page_icon="🤖")
st.title("🤖 Skypay Support Chat")

# Initialize Groq Client
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("Groq API Key missing in secrets.")
    st.stop()

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = create_conversation() 

conversation_id = st.session_state.conversation_id

# Check real-time status from DB
status = get_conversation_status(conversation_id)
human_active = status in ['escalated', 'human_active']

if human_active:
    st.info("👩‍💻 You are now being assisted by a person. Please know that the official work hours are 9AM-6PM so they might not be able to respond fast.")

st.subheader("Conversation")
messages = get_messages(conversation_id) 

for role, content in messages:
    if role == "user":
        st.chat_message("user").write(content)
    elif role == "ai":
        st.chat_message("assistant").write(content)
    elif role == "human":
        st.chat_message("assistant").write(f"👩‍💻 {content}")
    else:
        st.chat_message("system").write(content)

user_input = st.chat_input("Type your message here...")

if user_input:
    add_message(conversation_id, "user", user_input) 
    st.chat_message("user").write(user_input)

    if not human_active:
        SYSTEM_PROMPT = """You are a professional support chatbot for Skypay ONLY.
Rules:
- Answer ONLY Skypay-related questions.
- If the question is NOT related to Skypay, reply EXACTLY:
"I'm sorry but I am built only to answer inquiries regarding Skypay. Thank you." """
        
        with st.chat_message("assistant"):
            with st.spinner("Skypay AI is working on your answer..."):
                try:
                    # Retrieve history for context
                    full_history = [{"role": "system", "content": SYSTEM_PROMPT}]
                    for role, content in messages:
                        if role == "user":
                            full_history.append({"role": "user", "content": content})
                        elif role == "ai":
                            full_history.append({"role": "assistant", "content": content})
                    full_history.append({"role": "user", "content": user_input})

                    # Call Groq API
                    completion = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=full_history,
                        temperature=0.5,
                        max_tokens=300
                    )
                    reply = completion.choices[0].message.content
                    
                    st.write(reply)
                    add_message(conversation_id, "ai", reply) 
                except Exception as e:
                    st.error(f"Error: {e}")
    
    st.rerun()