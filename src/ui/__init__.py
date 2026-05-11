# UI module
# Re-export all public functions from page modules

from .auth_page import show_auth_page
from .chat_page import show_chat_page
from .dashboard_page import show_dashboard_page

__all__ = [
    "show_auth_page",
    "show_chat_page",
    "show_dashboard_page",
]
