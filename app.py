"""
MentalTalk Mental Health Chatbot
Main Streamlit application entrypoint.
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="MentalTalk",
    page_icon="🧠",
    layout="wide"
)

# Initialize database on startup
from src.database import init_db
from src.rag.ingestion import ingest_pdfs, is_collection_empty


def main():
    # Initialize database
    _initialize_database()

    # Initialize RAG system
    _initialize_rag()

    # Initialize session state
    _initialize_session_state()

    # Route to appropriate page
    _route_page()


def _initialize_database():
    try:
        init_db()
    except Exception as e:
        st.error(f"Failed to initialize database: {e}")
        st.stop()


def _initialize_rag():
    try:
        # Check if ChromaDB collection is empty
        if is_collection_empty():
            # Ingest PDFs from the data/pdfs directory
            pdf_dir = os.path.join(os.path.dirname(__file__), "data", "pdfs")
            num_chunks = ingest_pdfs(pdf_dir)
            if num_chunks > 0:
                st.toast(f"Ingested {num_chunks} chunks from PDFs.")
    except Exception as e:
        st.warning(f"RAG initialization warning: {e}")


def _initialize_session_state():
    # Initialize logged_in state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # Initialize user info
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if "username" not in st.session_state:
        st.session_state.username = None

    # Initialize current session
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None

    # Initialize messages
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Initialize current page
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Auth"


def _route_page():
    if not st.session_state.logged_in:
        # Show auth page
        from src.ui.auth_page import show_auth_page
        show_auth_page()
    else:
        # User is logged in, show selected page
        if st.session_state.current_page == "Chat":
            from src.ui.chat_page import show_chat_page
            show_chat_page()
        elif st.session_state.current_page == "Dashboard":
            from src.ui.dashboard_page import show_dashboard_page
            show_dashboard_page()
        else:
            # Default to chat page
            st.session_state.current_page = "Chat"
            from src.ui.chat_page import show_chat_page
            show_chat_page()


if __name__ == "__main__":
    main()
