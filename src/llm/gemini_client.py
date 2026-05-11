"""
Gemini client module for MentalTalk Mental Health Chatbot
Handles communication with Google's Generative AI API.
"""

import os
from typing import List, Dict, Optional
import google.generativeai as genai

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# System prompt for the chatbot
SYSTEM_PROMPT = """
You are MentalTalk, a compassionate mental health support assistant.
You provide empathetic, non-judgmental support for users dealing with stress, anxiety, depression, loneliness, and other mental health challenges.
You are NOT a licensed therapist and always encourage users to seek professional help when needed.
Use the provided context from mental health resources to inform your responses.
Keep responses warm, concise (2-4 paragraphs max), and focused on the user's emotional needs.
"""

# Cached model instance
_model = None


def _get_model():
    global _model
    if _model is None:
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set it in your .env file or environment."
            )
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT
        )
    return _model


def _convert_history_to_gemini_format(db_history: List[Dict[str, str]]) -> List[Dict[str, List[str]]]:
    gemini_history = []
    for msg in db_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Map 'assistant' to 'model' for Gemini
        gemini_role = "model" if role == "assistant" else role

        gemini_history.append({
            "role": gemini_role,
            "parts": [content]
        })
    return gemini_history


def get_gemini_response(user_message: str, chat_history: List[Dict[str, str]], rag_context: str) -> str:
    try:
        model = _get_model()

        # Build the full user message with context
        if rag_context.strip():
            full_user_message = f"[CONTEXT FROM MENTAL HEALTH RESOURCES]\n{rag_context}\n\n[USER MESSAGE]\n{user_message}"
        else:
            full_user_message = user_message

        # Convert history to Gemini format
        gemini_history = _convert_history_to_gemini_format(chat_history)

        # Start chat with history
        chat = model.start_chat(history=gemini_history)

        # Send message and get response
        response = chat.send_message(full_user_message)

        # Return the response text
        return response.text

    except Exception as e:
        print(f"Error getting Gemini response: {e}")
        return "I'm sorry, I encountered an error processing your request. Please try again."


def test_connection() -> bool:
    try:
        model = _get_model()
        # Send a simple test message
        chat = model.start_chat(history=[])
        response = chat.send_message("Say 'ok'")
        return response.text.strip().lower() == 'ok'
    except Exception as e:
        print(f"Gemini connection test failed: {e}")
        return False
