"""
Authentication page for MentalTalk Mental Health Chatbot
Handles login and signup UI with Streamlit.
"""

import streamlit as st
from src.auth import signup, login


def show_auth_page():
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
    .stTabs [data-testid="stTabs"] > div > div > div > button {
        background-color: #1a1d27;
        border: 1px solid #2a2d3e;
        color: #e8eaf0;
    }
    .stTabs [data-testid="stTabs"] > div > div > div > button:hover {
        background-color: #2a2d3e;
    }
    .stTabs [data-testid="stTabs"] > div > div > div > button[data-selected="true"] {
        background-color: #6c8ebf;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🧠 MentalTalk")
    st.markdown("### Mental Health Support Chatbot")
    st.markdown("---")

    # Create tabs for Login and Sign Up
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        _show_login_tab()

    with tab2:
        _show_signup_tab()


def _show_login_tab():
    st.header("Login")

    with st.form("login_form"):
        username = st.text_input("Username", label_visibility="collapsed", placeholder="Enter your username")
        password = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Enter your password")

        submit_button = st.form_submit_button("Login")

        if submit_button:
            if not username or not password:
                st.error("Please enter both username and password.")
                return

            # Attempt login
            success, user_id, message = login(username, password)

            if success:
                # Set session state and rerun
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.session_state.current_page = "Chat"
                st.success(message)
                st.rerun()
            else:
                st.error(message)


def _show_signup_tab():
    st.header("Create Account")

    with st.form("signup_form"):
        username = st.text_input("Username", label_visibility="collapsed", placeholder="3-30 chars, letters/numbers/_")
        password = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Minimum 8 characters")
        password_confirm = st.text_input("Confirm Password", type="password", label_visibility="collapsed", placeholder="Re-enter your password")

        submit_button = st.form_submit_button("Sign Up")

        if submit_button:
            if not username or not password or not password_confirm:
                st.error("Please fill in all fields.")
                return

            if password != password_confirm:
                st.error("Passwords do not match.")
                return

            # Attempt signup
            success, message = signup(username, password)

            if success:
                st.success(message)
                # Switch to login tab
                st.rerun()
            else:
                st.error(message)
