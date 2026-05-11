"""
Dashboard page for MentalTalk Mental Health Chatbot
Displays mood history and analytics with Plotly charts.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from datetime import timedelta
from src.database import get_mood_history, get_all_sessions
from collections import Counter


def show_dashboard_page():
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
    .stDataFrame {
        background-color: #1a1d27;
        border: 1px solid #2a2d3e;
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown(f"""
    <div style="
        margin: 2rem 0 1rem 0;
        text-align: center;
    ">
        <h1 style="
            color: #e8eaf0;
            font-size: 2rem;
            margin-bottom: 0.5rem;
        ">📊 Mood Dashboard</h1>
        <p style="
            color: #8b8fa8;
            font-size: 1.1rem;
        ">Your mood insights and patterns</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    _show_sidebar()

    # Load mood history
    mood_history = get_mood_history(st.session_state.user_id, days=30)

    if not mood_history:
        _show_empty_state()
        return

    # Display mood analytics
    _display_mood_analytics(mood_history)


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
        if st.button("＋ New Chat", key="new_chat_btn_dashboard", use_container_width=True):
            session_id = create_session(st.session_state.user_id)
            st.session_state.current_session_id = session_id
            st.session_state.messages = []
            st.session_state.current_page = "Chat"
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

        if chat_button:
            st.session_state.current_page = "Chat"
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


def _show_empty_state():
    st.markdown("""
    <div style="
        text-align: center;
        padding: 3rem;
        background-color: #1e2130;
        border: 1px solid #2a2d3e;
        border-radius: 12px;
    ">
        <h3 style="
            color: #e8eaf0;
            margin-bottom: 1rem;
        ">🌙 No mood data yet</h3>
        <p style="
            color: #8b8fa8;
            margin-bottom: 0.5rem;
        ">Start chatting and your mood patterns will appear here! 💙</p>
        <p style="
            color: #6c8ebf;
            font-size: 0.9rem;
        ">Your mood is automatically tracked as you chat with MentalTalk</p>
    </div>
    """, unsafe_allow_html=True)


def _display_mood_analytics(mood_history: list):
    # Convert to DataFrame
    df = pd.DataFrame(mood_history)

    # Convert logged_at to datetime
    df['logged_at'] = pd.to_datetime(df['logged_at'])

    # Sort by date
    df = df.sort_values('logged_at')

    # Today's Mood Summary card
    st.markdown("""
    <div style="
        background-color: #1e2130;
        border: 1px solid #2a2d3e;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 2rem;
    ">
        <h3 style="
            color: #e8eaf0;
            margin: 0 0 1rem 0;
            font-size: 1.2rem;
        ">Today's Mood Summary</h3>
    </div>
    """, unsafe_allow_html=True)

    # Get most recent mood entry
    latest_mood = df.iloc[-1]
    mood_score = latest_mood['mood_score']

    # Determine mood emoji and label
    if mood_score > 0.5:
        mood_emoji = "😊"
        mood_label = "Feeling Good"
    elif mood_score >= 0.1:
        mood_emoji = "🙂"
        mood_label = "Mostly Okay"
    elif mood_score >= -0.1:
        mood_emoji = "😐"
        mood_label = "Neutral"
    elif mood_score >= -0.5:
        mood_emoji = "😔"
        mood_label = "A Bit Low"
    else:
        mood_emoji = "😢"
        mood_label = "Rough Day"

    # Display mood summary
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: 2rem;
    ">
        <div style="
            font-size: 4rem;
            margin-bottom: 1rem;
        ">{mood_emoji}</div>
        <h2 style="
            color: #e8eaf0;
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        ">{mood_label}</h2>
        <p style="
            color: #8b8fa8;
            font-size: 0.9rem;
        ">{latest_mood['logged_at'].strftime('%B %d, %Y')}</p>
    </div>
    """, unsafe_allow_html=True)

    # Mood This Week - bar chart
    st.markdown("""
    <div style="
        background-color: #1e2130;
        border: 1px solid #2a2d3e;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 2rem;
    ">
        <h3 style="
            color: #e8eaf0;
            margin: 0 0 1rem 0;
            font-size: 1.2rem;
        ">Mood This Week</h3>
    </div>
    """, unsafe_allow_html=True)

    # Get last 7 days of data
    last_7_days = df.tail(7)

    # Create bar chart
    fig = go.Figure()

    # Add bar trace
    fig.add_trace(go.Bar(
        x=[date.strftime('%a') for date in last_7_days['logged_at']],
        y=last_7_days['mood_score'],
        marker_color='#6c8ebf',
        width=0.5
    ))

    # Update layout with dark theme
    fig.update_layout(
        template="plotly_dark",
        height=300,
        showlegend=False,
        xaxis_title="Day",
        yaxis_title="Mood",
        yaxis=dict(
            range=[-1, 1],
            gridcolor='#2a2d3e'
        ),
        xaxis=dict(
            gridcolor='#2a2d3e'
        )
    )

    # Add horizontal reference lines
    fig.add_hline(y=0.5, line_dash="dash", line_color="#4caf82",
                  annotation_text="Good", annotation_font_color="#4caf82")
    fig.add_hline(y=0, line_dash="dash", line_color="#8b8fa8",
                  annotation_text="Neutral", annotation_font_color="#8b8fa8")
    fig.add_hline(y=-0.5, line_dash="dash", line_color="#e05c5c",
                  annotation_text="Low", annotation_font_color="#e05c5c")

    st.plotly_chart(fig, use_container_width=True)

    # Mood Streak card
    st.markdown("""
    <div style="
        background-color: #1e2130;
        border: 1px solid #2a2d3e;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 2rem;
    ">
        <h3 style="
            color: #e8eaf0;
            margin: 0 0 1rem 0;
            font-size: 1.2rem;
        ">Mood Streak</h3>
    </div>
    """, unsafe_allow_html=True)

    # Calculate positive streak (consecutive days with mood > 0)
    positive_days = df[df['mood_score'] > 0]
    if not positive_days.empty:
        # Group by date and check consecutive days
        positive_days = positive_days.sort_values('logged_at')
        streak = 1
        max_streak = 1

        for i in range(1, len(positive_days)):
            current_date = positive_days.iloc[i]['logged_at'].date()
            prev_date = positive_days.iloc[i-1]['logged_at'].date()

            if (current_date - prev_date).days == 1:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 1

        st.markdown(f"""
        <div style="
            text-align: center;
            padding: 1rem;
        ">
            <p style="
                color: #4caf82;
                font-size: 1.2rem;
                font-weight: 600;
            ">🔥 {max_streak}-day positive streak!</p>
            <p style="
                color: #8b8fa8;
                font-size: 0.9rem;
            ">Keep going — log your mood daily</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="
            text-align: center;
            padding: 1rem;
        ">
            <p style="
                color: #f0b429;
            ">Start tracking your mood daily!</p>
        </div>
        """, unsafe_allow_html=True)


def _create_mood_score_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    # Add mood score line
    fig.add_trace(go.Scatter(
        x=df['logged_at'],
        y=df['mood_score'],
        mode='lines+markers',
        name='Mood Score',
        line=dict(color='#8B5CF6', width=2),
        marker=dict(size=8, color=df['mood_score'], colorscale='RdYlGn', showscale=True)
    ))

    # Add horizontal lines for score ranges
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Neutral")
    fig.add_hline(y=0.5, line_dash="dot", line_color="lightgreen", annotation_text="Positive")
    fig.add_hline(y=-0.5, line_dash="dot", line_color="lightcoral", annotation_text="Negative")

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Mood Score",
        yaxis_range=[-1.1, 1.1],
        hovermode='x unified',
        height=350
    )

    return fig


def _create_mood_distribution_chart(df: pd.DataFrame) -> go.Figure:
    # Count mood labels
    mood_counts = df['mood_label'].value_counts()

    # Define color mapping based on mood category
    color_map = {
        "Very Positive": "#00CC00",
        "Positive": "#00AA00",
        "Neutral": "#AAAAAA",
        "Negative": "#CC6600",
        "Very Negative": "#CC0000"
    }

    colors = [color_map.get(label, "#666666") for label in mood_counts.index]

    fig = go.Figure(data=[go.Bar(
        x=mood_counts.index,
        y=mood_counts.values,
        marker_color=colors,
        text=mood_counts.values,
        textposition='auto',
    )])

    fig.update_layout(
        xaxis_title="Mood Category",
        yaxis_title="Count",
        height=350
    )

    return fig


def _display_summary_stats(df: pd.DataFrame):
    col1, col2, col3 = st.columns(3)

    with col1:
        avg_score = df['mood_score'].mean()
        st.metric("Average Mood Score", f"{avg_score:.3f}")

    with col2:
        most_common_mood = df['mood_label'].mode()[0]
        st.metric("Most Common Mood", most_common_mood)

    with col3:
        total_logs = len(df)
        st.metric("Total Mood Logs", total_logs)

    # Additional insights
    st.markdown("### Insights")
    col1, col2 = st.columns(2)

    with col1:
        positive_count = len(df[df['mood_score'] > 0.3])
        st.info(f"😊 Positive moods: {positive_count}")

    with col2:
        negative_count = len(df[df['mood_score'] < -0.3])
        st.warning(f"😞 Negative moods: {negative_count}")
