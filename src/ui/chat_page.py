"""
Chat page for MentalTalk Mental Health Chatbot
Handles the main chat interface with Streamlit.
"""

import streamlit as st
import datetime
from src.database import create_session, save_message, get_session_messages, get_all_sessions, log_mood
from src.rag.retriever import retrieve_context
from src.llm.gemini_client import get_gemini_response
from src.mood.analyzer import analyze_mood


def show_chat_page():
    # Initialize session state for chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "current_session_id" not in st.session_state:
        # Create a new session
        session_id = create_session(st.session_state.user_id)
        st.session_state.current_session_id = session_id

    # Apply dark theme styling
    st.markdown("""
    <style>
    .main .stApp {
        background-color: #0f1117;
    }
    .main .stApp > header {
        background-color: #0f1117;
        border-bottom: 1px solid #2a2d3e;
    }
    .stMarkdown {
        color: #e8eaf0;
    }
    .stTextInput > div > div > input {
        background-color: #1e2130;
        border: 1px solid #2a2d3e;
        color: #e8eaf0;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header area with image or placeholder
    try:
        st.image("images/1.png", width="100%")
    except:
        st.markdown("""
        <div style="height:120px; background: linear-gradient(135deg, #1e2130, #2a2d3e); border-radius:12px; display:flex; align-items:center; justify-content:center;">
            <span style="color:#6c8ebf; font-size:1.2rem;">MentalTalk</span>
        </div>
        """, unsafe_allow_html=True)

    # Welcome message
    st.markdown(f"""
    <div style="
        margin: 2rem 0;
        text-align: center;
    ">
        <h2 style="
            color: #e8eaf0;
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        ">Welcome, <strong style="color: #6c8ebf;">{st.session_state.username}</strong>! 👋</h2>
        <p style="
            color: #8b8fa8;
            font-size: 1.1rem;
        ">How are you feeling today?</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    _show_sidebar()

    # Display chat messages
    _display_messages()

    # Chat input
    _handle_chat_input()


def _show_sidebar():
    with st.sidebar:
        # Apply dark theme styling
        st.markdown("""
        <style>
        .main .stSidebar {
            background-color: #1a1d27;
            padding: 0;
        }
        </style>
        """, unsafe_allow_html=True)

        # Top section - Branding
        st.markdown("""
        <div style="
            padding: 1.5rem 1rem 1rem 1rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid #2a2d3e;
        ">
            <h1 style="
                color: #e8eaf0;
                margin: 0;
                font-size: 1.8rem;
                font-weight: 700;
            ">MentalTalk</h1>
            <p style="
                color: #8b8fa8;
                margin: 0.5rem 0 0 0;
                font-size: 0.9rem;
            ">Your safe space to talk</p>
        </div>
        """, unsafe_allow_html=True)

        # Middle section - Chat History
        st.markdown("""
        <div style="
            padding: 0 1rem 1rem 1rem;
            margin-bottom: 1rem;
        ">
            <h3 style="
                color: #e8eaf0;
                margin: 0 0 0.5rem 0;
                font-size: 1rem;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            ">💬 Chat History</h3>
        </div>
        """, unsafe_allow_html=True)

        # New Chat button
        if st.button("＋ New Chat", key="new_chat_btn", use_container_width=True):
            session_id = create_session(st.session_state.user_id)
            st.session_state.current_session_id = session_id
            st.session_state.messages = []
            st.rerun()

        # Get and display chat sessions
        sessions = get_all_sessions(st.session_state.user_id)
        if sessions:
            for session in sessions:
                # Format timestamp
                created_time = session.get('session_start') or session.get('created_at')
                if isinstance(created_time, str):
                    created_time = datetime.fromisoformat(created_time.replace('Z', '+00:00'))

                # Format date as "MM/DD/YYYY"
                date_str = created_time.strftime('%m/%d/%Y') if created_time else "Unknown"

                # Show "New chat" for all sessions since we don't store first_message
                first_msg = "New chat"

                # Session button
                session_button = st.button(
                    f"{date_str} - {first_msg}",
                    key=f"session_{session['id']}",
                    use_container_width=True,
                    type="primary" if st.session_state.current_session_id == session['id'] else "secondary"
                )

                if session_button:
                    # Load messages for this session
                    messages = get_session_messages(session['id'])
                    st.session_state.messages = messages
                    st.session_state.current_session_id = session['id']
                    st.session_state.current_page = "Chat"
                    st.rerun()
        else:
            st.markdown(
                "<p style='color: #8b8fa8; font-size: 0.9rem; padding: 0 1rem;'>No previous chats yet</p>",
                unsafe_allow_html=True
            )

        # Bottom section - Navigation
        st.markdown("---")
        st.markdown("""
        <div style="padding: 1rem 0;">
            <h3 style="
                color: #e8eaf0;
                margin: 0 0 0.5rem 0;
                font-size: 1rem;
                font-weight: 600;
            ">Navigation</h3>
        </div>
        """, unsafe_allow_html=True)

        # Toggle between Chat and Dashboard
        if st.session_state.current_page == "Chat":
            chat_button = st.button("💬 Chat", use_container_width=True, type="primary")
            dashboard_button = st.button("📊 Mood Dashboard", use_container_width=True)
        else:
            chat_button = st.button("💬 Chat", use_container_width=True)
            dashboard_button = st.button("📊 Mood Dashboard", use_container_width=True, type="primary")

        if dashboard_button:
            st.session_state.current_page = "Dashboard"
            st.rerun()

        # Account section
        st.markdown("---")
        st.markdown("""
        <div style="padding: 1rem 0;">
            <h3 style="
                color: #e8eaf0;
                margin: 0 0 0.5rem 0;
                font-size: 1rem;
                font-weight: 600;
            ">Account</h3>
        </div>
        """, unsafe_allow_html=True)

        # Show username
        st.markdown(f"""
        <p style="
            color: #8b8fa8;
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
        ">Welcome, {st.session_state.username}</p>
        """, unsafe_allow_html=True)

        # Logout button
        if st.button("🔒 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.current_session_id = None
            st.session_state.messages = None
            st.session_state.current_page = None
            st.rerun()


def _display_messages():
    # Container for chat messages with scrollable area
    message_container = st.container(height=600)

    with message_container:
        for msg in st.session_state.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                # User message bubble (right-aligned)
                st.markdown(f"""
                <div style="
                    display: flex;
                    justify-content: flex-end;
                    margin-bottom: 1rem;
                ">
                    <div style="
                        background-color: #2a2d3e;
                        border-radius: 12px 12px 4px 12px;
                        padding: 12px 16px;
                        max-width: 75%;
                        border: 1px solid #3a3d4e;
                    ">
                        <p style="
                            color: #e8eaf0;
                            margin: 0;
                        ">{content}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Bot message bubble (left-aligned)
                st.markdown(f"""
                <div style="
                    display: flex;
                    justify-content: flex-start;
                    margin-bottom: 1rem;
                    gap: 0.5rem;
                ">
                    <div style="
                        background-color: #1e2130;
                        border-radius: 12px 12px 12px 4px;
                        padding: 12px 16px;
                        max-width: 75%;
                        border: 1px solid #2a2d3e;
                    ">
                        <div style="
                            display: flex;
                            align-items: center;
                            gap: 0.5rem;
                            margin-bottom: 0.5rem;
                        ">
                            <span style="color: #7fbfb0; font-size: 1rem;">💙</span>
                            <span style="color: #7fbfb0; font-size: 0.85rem;">MentalTalk</span>
                        </div>
                        <p style="
                            color: #e8eaf0;
                            margin: 0;
                        ">{content}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)


def _handle_chat_input():
    # Apply custom styling to chat input
    st.markdown("""
    <style>
    .stChatInput {
        margin-top: 2rem;
    }
    .stChatInput > div > div {
        background-color: #1e2130;
        border-radius: 24px;
        border: 1px solid #2a2d3e;
    }
    .stChatInput > div > div > input {
        background-color: transparent;
        border: none;
        color: #e8eaf0;
        font-size: 1rem;
    }
    .stChatInput > div > div > input::placeholder {
        color: #8b8fa8;
    }
    </style>
    """, unsafe_allow_html=True)

    user_message = st.chat_input("Share what's on your mind...", key="chat_input")

    if user_message:
        # Add user message to session state
        user_msg_dict = {"role": "user", "content": user_message}
        st.session_state.messages.append(user_msg_dict)

        # Save user message to database
        save_message(st.session_state.current_session_id, "user", user_message)

        # Analyze mood of user message
        mood_result = analyze_mood(user_message)
        log_mood(
            st.session_state.user_id,
            mood_result["label"],
            mood_result["score"],
            mood_result["snippet"]
        )

        # Retrieve context from RAG
        rag_context = retrieve_context(user_message)

        # Get chat history (excluding the current user message for context)
        chat_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in st.session_state.messages[:-1]  # Exclude current user message
        ]

        # Get response from Gemini
        with st.spinner("Thinking..."):
            assistant_response = get_gemini_response(
                user_message=user_message,
                chat_history=chat_history,
                rag_context=rag_context
            )

        # Add assistant response to session state
        assistant_msg_dict = {"role": "assistant", "content": assistant_response}
        st.session_state.messages.append(assistant_msg_dict)

        # Save assistant message to database
        save_message(st.session_state.current_session_id, "assistant", assistant_response)

        # Rerun to update the UI
        st.rerun()
