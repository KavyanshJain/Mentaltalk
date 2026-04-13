"""
MentalTalk — AI Mental Health Companion
=======================================
Main application: Gradio UI  +  RAG Pipeline  +  Gemini 2.5 Flash-Lite  +  Mood Dashboard

Run locally:
    set GEMINI_API_KEY=your_key_here
    python app.py

Then open http://localhost:7860
"""

#  SECTION 1 — ENVIRONMENT SETUP (must run before any other imports)

import os
import sys
from pathlib import Path

# Project root — all paths are resolved relative to this
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file if python-dotenv is available (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


#  SECTION 2 — IMPORTS
import re
import json
import logging
import datetime

import gradio as gr

# Gemini LLM
from google import genai
from google.genai import types

# RAG retriever
from rag.retriever import load_collection, retrieve, build_context

# Database (PostgreSQL auth + persistence)
import db


#  SECTION 3 — LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("mentaltalk")


#  SECTION 4 — CONFIGURATION
GEMINI_MODEL     = "gemini-2.5-flash-lite"
MAX_HISTORY_TURNS = 6     # last N user-bot pairs included in the Gemini prompt
RAG_TOP_K         = 5     # number of chunks retrieved per query


#  SECTION 5 — SYSTEM PROMPT
SYSTEM_PROMPT = """\
You are MentalTalk — a compassionate, knowledgeable AI mental health companion.

## Your Core Identity
- You are a **supportive listener and wellness guide**, not a therapist or doctor.
- You draw from trusted mental health resources (WHO guidelines, mhGAP, CBT techniques) \
provided to you as context.
- You combine genuine warmth with evidence-based guidance.

## Your Personality
- 🌿 **Warm & Empathetic** — You make people feel genuinely heard and understood.
- 🧘 **Calm & Patient** — Your presence is a safe space; never rushing, never judging.
- 💡 **Gently Insightful** — You offer perspectives that help people see their situation clearly.
- 🤝 **Encouraging** — You highlight strengths and celebrate small victories.
- You speak naturally and conversationally, like a trusted friend who understands psychology.

## How You Respond
1. **ALWAYS start by validating** the person's feelings — acknowledge what they're going through.
2. **Ask thoughtful follow-up questions** to understand their situation better (1-2 per response).
3. **Offer practical, actionable strategies** when appropriate (breathing exercises, \
journaling prompts, cognitive reframing, grounding techniques, etc.).
4. **Reference the provided context material** naturally — weave the knowledge in, \
don't quote it verbatim or mention document names.
5. **Keep responses warm but concise** — typically 2-3 short paragraphs. Avoid walls of text.
6. **Use emojis sparingly** (1-2 max per response) to add warmth, never excessively.

## Critical Safety Rules
- If someone mentions **self-harm, suicide, or hurting themselves/others**, IMMEDIATELY:
  1. Express genuine care and concern
  2. Provide these crisis resources:
     - 📞 iCall: 9152987821 (Mon-Sat 8am-10pm)
     - 📞 Vandrevala Foundation: 1860-2662-345 (24/7)
     - 📞 NIMHANS: 080-46110007
     - 🆘 Emergency: 112
  3. Strongly encourage them to reach out NOW
- **NEVER** diagnose conditions or prescribe/recommend medication.
- **NEVER** minimize someone's pain or say things like "just think positive" or "others have it worse".
- For serious or persistent concerns, gently suggest professional help while staying supportive.
- Acknowledge that you are an AI when relevant, and that professional human support is invaluable.\
"""


#  SECTION 6 — INITIALIZE SERVICES

# ── Gemini client ────────────────────────────────────────────────────────────────
_api_key = os.environ.get("GEMINI_API_KEY")
if not _api_key:
    log.warning("GEMINI_API_KEY not set — chat will return placeholder responses.")
    log.warning("   Set it via environment variable or .env file (see .env.example).")
    gemini_client = None
else:
    gemini_client = genai.Client(api_key=_api_key)
    log.info(f"Gemini client initialized (model: {GEMINI_MODEL})")

# ── RAG collection ───────────────────────────────────────────────────────────────
try:
    rag_collection = load_collection()
except Exception as e:
    log.warning(f"RAG collection unavailable: {e}")
    log.warning("   Chatbot will work without RAG context. Run ingest.py to build it.")
    rag_collection = None

# ── Database ─────────────────────────────────────────────────────────────────────
try:
    db.init_db()
except Exception as e:
    log.warning(f"⚠️  Database unavailable: {e}")
    log.warning("   Auth and persistence will not work. Set DATABASE_URL in .env.")


#  SECTION 7 — RESPONSE FORMATTING

def format_response(text: str) -> str:
    """Convert Gemini's markdown response to safe HTML for chat bubbles.

    Handles: bold, italic, headers, bullet/numbered lists, inline code,
    code blocks, and line breaks.  Escapes raw HTML first for safety.
    """
    if not text:
        return ""

    # Step 1 — Escape HTML special characters
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    # Step 2 — Markdown → HTML conversions (order matters)

    # Fenced code blocks:  ```lang\n...\n```
    text = re.sub(
        r"```(?:\w*)\n?(.*?)```",
        lambda m: (
            '<pre style="background:rgba(99,179,150,.08);padding:8px 12px;'
            'border-radius:8px;font-size:13px;overflow-x:auto;margin:4px 0;'
            f'white-space:pre-wrap">{m.group(1).strip()}</pre>'
        ),
        text,
        flags=re.DOTALL,
    )

    # Inline code:  `code`
    text = re.sub(
        r"`([^`]+)`",
        r'<code style="background:rgba(99,179,150,.1);padding:1px 5px;'
        r'border-radius:4px;font-size:13px">\1</code>',
        text,
    )

    # Bold:  **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

    # Italic:  *text*  (but not inside **)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)

    # Headers:  ## Title  →  bold text
    text = re.sub(
        r"^#{1,4}\s+(.+)$",
        r'<strong style="font-size:15px">\1</strong>',
        text,
        flags=re.MULTILINE,
    )

    # Bullet lists:  - item  or  * item
    text = re.sub(
        r"^\s*[-*]\s+(.+)$",
        r'<span style="display:block;padding-left:14px">• \1</span>',
        text,
        flags=re.MULTILINE,
    )

    # Numbered lists:  1. item
    text = re.sub(
        r"^\s*(\d+)\.\s+(.+)$",
        r'<span style="display:block;padding-left:14px">\1. \2</span>',
        text,
        flags=re.MULTILINE,
    )

    # Line breaks
    text = text.replace("\n", "<br>")

    # Clean up excessive <br> runs
    text = re.sub(r"(<br\s*/?>){3,}", "<br><br>", text)

    return text.strip()


def get_crisis_response() -> str:
    """Return an immediate crisis-resource response (formatted HTML)."""
    return (
        "I hear you, and I want you to know that <strong>your feelings matter deeply</strong>. "
        "You don't have to go through this alone.<br><br>"
        "Please reach out to one of these crisis support lines right now:<br><br>"
        "📞 <strong>iCall:</strong> 9152987821 (Mon–Sat 8am–10pm)<br>"
        "📞 <strong>Vandrevala Foundation:</strong> 1860-2662-345 (24/7)<br>"
        "📞 <strong>NIMHANS:</strong> 080-46110007<br>"
        "🆘 <strong>Emergency:</strong> 112<br><br>"
        "Talking to a trained counsellor can make a real difference. "
        "I'm here for you too — would you like to talk about what you're going through? 💙"
    )


def get_fallback_response() -> str:
    """Return a gentle fallback when the LLM is unavailable."""
    return (
        "I'm here for you. I'm having a moment of difficulty connecting right now, "
        "but please know that <strong>your feelings are completely valid</strong>.<br><br>"
        "Would you like to try again in a moment? In the meantime, here's a quick "
        "grounding exercise: take a slow, deep breath in for 4 counts, hold for 4, "
        "and breathe out for 6. 🌿"
    )


#  SECTION 8 — LLM RESPONSE GENERATION (RAG + Gemini)

# Crisis-related keywords for fast-path detection
_CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "want to die", "self-harm",
    "self harm", "cutting myself", "hurt myself", "no reason to live",
    "better off dead",
]


def get_bot_response(user_msg: str, chat_history: list, username: str) -> str:
    """Generate a chatbot response using the RAG pipeline + Gemini LLM.

    Args:
        user_msg:     The user's latest message.
        chat_history: List of dicts [{user, bot, ...}, ...] from session state.
        username:     The user's display name.

    Returns:
        An HTML-formatted response string.
    """
    msg_lower = user_msg.lower()

    # ── Fast-path: crisis detection ──────────────────────────────────────────
    # If the message contains crisis keywords, we still call the LLM but
    # prepend an urgent context directive.
    is_crisis = any(kw in msg_lower for kw in _CRISIS_KEYWORDS)

    # ── Step 1: Retrieve RAG context ─────────────────────────────────────────
    rag_context = ""
    if rag_collection is not None:
        try:
            hits = retrieve(query=user_msg, collection=rag_collection, n_results=RAG_TOP_K)
            rag_context = build_context(hits)
            if hits:
                log.info(
                    f"📚 Retrieved {len(hits)} chunks "
                    f"(best dist: {hits[0]['distance']:.3f})"
                )
            else:
                log.info("📚 No RAG hits for this query")
        except Exception as e:
            log.warning(f"RAG retrieval failed: {e}")

    # ── Step 2: Check if Gemini client is available ──────────────────────────
    if gemini_client is None:
        if is_crisis:
            return get_crisis_response()
        return (
            "<strong>Setup needed:</strong> The Gemini API key is not configured yet.<br>"
            "Set the <code>GEMINI_API_KEY</code> environment variable and restart the app.<br><br>"
            "See the README for instructions."
        )

    # ── Step 3: Build conversation contents for Gemini ───────────────────────
    contents = []

    # Add recent conversation history (alternating user/model)
    for entry in chat_history[-(MAX_HISTORY_TURNS):]:
        contents.append(
            types.Content(role="user", parts=[types.Part(text=entry["user"])])
        )
        contents.append(
            types.Content(role="model", parts=[types.Part(text=entry["bot_raw"])])
        )

    # Build the current user message with RAG context
    parts = []

    if rag_context:
        parts.append(
            "[Relevant reference material from trusted mental health sources — "
            "use this to inform your response naturally]\n\n"
            f"{rag_context}\n\n---\n\n"
        )

    if is_crisis:
        parts.append(
            "[URGENT: The user may be in crisis. Follow the safety rules in your "
            "instructions IMMEDIATELY. Provide crisis resources and express care.]\n\n"
        )

    parts.append(f"User ({username}): {user_msg}")
    current_message = "".join(parts)

    contents.append(
        types.Content(role="user", parts=[types.Part(text=current_message)])
    )

    # ── Step 4: Call Gemini ───────────────────────────────────────────────────
    try:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT + f"\n\nThe user's name is: {username}",
            temperature=0.75,
            top_p=0.92,
            max_output_tokens=1024,
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT",
                    threshold="BLOCK_ONLY_HIGH",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH",
                    threshold="BLOCK_ONLY_HIGH",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    threshold="BLOCK_ONLY_HIGH",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT",
                    threshold="BLOCK_ONLY_HIGH",
                ),
            ],
        )

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=config,
        )

        # Extract text from response
        if response and response.text:
            bot_raw = response.text
            bot_html = format_response(bot_raw)
            log.info(f"🤖 Gemini responded ({len(bot_raw)} chars)")
            return bot_html
        else:
            # Response was blocked or empty
            log.warning("Gemini returned empty/blocked response")
            if is_crisis:
                return get_crisis_response()
            return (
                "I want to help you with this. Let me try approaching it differently — "
                "could you share a bit more about what you're experiencing? "
                "I'm here to listen without judgment. 🌿"
            )

    except Exception as e:
        log.error(f"Gemini API error: {type(e).__name__}: {e}")
        if is_crisis:
            return get_crisis_response()
        return get_fallback_response()


#  SECTION 9 — SIDEBAR HTML BUILDER

def _build_hist_html(chat_hist: list) -> str:
    """Build the sidebar conversation-history HTML from session state."""
    if not chat_hist:
        return "<p style='color:#7a8f86;font-size:12px;padding:8px 16px'>No conversations yet</p>"

    html = ""
    for i, item in enumerate(reversed(chat_hist[-8:])):
        msg   = item.get("user", "")
        short = (msg[:34] + "…") if len(msg) > 34 else msg
        # Escape HTML in user text for safety
        short = short.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        color = item.get("color", "#7a8f86")
        label = item.get("mood_label", "")
        date  = item.get("date", "")
        active = (
            "background:rgba(99,179,150,.1);border-color:rgba(99,179,150,.3);"
            if i == 0 else ""
        )
        html += f"""
        <div class="hist-item" style="{active}">
          <div class="hist-title">
            <span class="mood-dot" style="background:{color}"></span>{short}
          </div>
          <div class="hist-meta"><span>{date}</span><span>{label}</span></div>
        </div>"""

    return html



#  SECTION 10 — GRADIO APPLICATION

def build_app():
    """Construct and return the full Gradio Blocks application.

    Returns:
        demo — Gradio Blocks app (css/theme/head baked in for Gradio 5.x).
    """
    static_dir = PROJECT_ROOT / "static"

    # Load frontend assets from separate files
    PAGE_HTML = (static_dir / "index.html").read_text(encoding="utf-8")
    APP_CSS   = (static_dir / "style.css").read_text(encoding="utf-8")
    APP_JS    = (static_dir / "script.js").read_text(encoding="utf-8")

    # ── <head> injection: Google Fonts + client-side JS ──────────────────────
    # In Gradio 5.x css/theme/head go into gr.Blocks(), NOT launch().
    APP_HEAD = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link href="https://fonts.googleapis.com/css2?family='
        'Playfair+Display:ital,wght@0,400;0,600;1,400&family='
        'DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">\n'
        f'<script>\n{APP_JS}\n</script>'
    )

    APP_THEME = gr.themes.Base(
        primary_hue="green",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("DM Sans"),
    )

    # ── Gradio Blocks ────────────────────────────────────────────────────────
    with gr.Blocks(
        title="Mental Talk — AI Mental Health Companion",
        css=APP_CSS,
        theme=APP_THEME,
        head=APP_HEAD,
    ) as demo:

        # ── Session state ────────────────────────────────────────────────────
        chat_history_state = gr.State([])   # [{user, bot_raw, bot_html, mood_label, color, date}]
        mood_history_state = gr.State([])   # [{score, label, color, date}]
        user_id_state      = gr.State(0)    # 0 = guest, >0 = registered DB user

        # ── Full-page HTML UI (body content only — no CSS/JS) ────────────────
        ui = gr.HTML(value=PAGE_HTML)

        # ── Bridge textboxes (CSS hides them off-screen) ─────────────────────
        user_input     = gr.Textbox(elem_id="gradio-user-input",     label="", value="")
        mood_input     = gr.Textbox(elem_id="gradio-mood-input",     label="", value="")
        username_input = gr.Textbox(elem_id="gradio-username-input", label="", value="Friend")
        reply_out      = gr.Textbox(elem_id="gradio-reply-out",      label="", value="")
        hist_out       = gr.Textbox(elem_id="gradio-hist-out",       label="", value="")
        auth_input     = gr.Textbox(elem_id="gradio-auth-input",     label="", value="")
        auth_out       = gr.Textbox(elem_id="gradio-auth-out",       label="", value="")

        # ── Handler: Auth ────────────────────────────────────────────────────
        def handle_auth(auth_json: str):
            """Process login/signup requests from the frontend.

            Input JSON: {"action": "login"|"signup", "username": "...", "password": "..."}
            Output JSON: {"ok": true, "user_id": N, "username": "...", "stats": {...},
                          "moods": [...], "chat_count": N}
                     or: {"ok": false, "error": "..."}
            """
            auth_json = (auth_json or "").strip()
            if not auth_json:
                return 0, ""

            try:
                data = json.loads(auth_json)
            except json.JSONDecodeError:
                return 0, json.dumps({"ok": False, "error": "Invalid request"})

            action   = data.get("action", "")
            username = (data.get("username", "") or "").strip()
            password = data.get("password", "")

            if not username:
                return 0, json.dumps({"ok": False, "error": "Username is required"})
            if not password:
                return 0, json.dumps({"ok": False, "error": "Password is required"})
            if len(username) < 3:
                return 0, json.dumps({"ok": False, "error": "Username must be at least 3 characters"})
            if len(password) < 4:
                return 0, json.dumps({"ok": False, "error": "Password must be at least 4 characters"})

            try:
                if action == "signup":
                    user = db.create_user(username, password)
                    if user is None:
                        return 0, json.dumps({"ok": False, "error": "Username already taken"})
                    uid = user["id"]
                    stats = db.get_user_stats(uid)
                    return uid, json.dumps({
                        "ok": True,
                        "user_id": uid,
                        "username": user["username"],
                        "stats": stats,
                        "moods": [],
                        "chat_count": 0,
                    })

                elif action == "login":
                    user = db.verify_user(username, password)
                    if user is None:
                        return 0, json.dumps({"ok": False, "error": "Invalid username or password"})
                    uid = user["id"]
                    stats = db.get_user_stats(uid)
                    moods = db.get_recent_moods(uid, limit=7)
                    chat_count = len(db.get_chat_history(uid, limit=1))
                    # Serialize dates for JSON
                    for m in moods:
                        if "created_at" in m:
                            m["created_at"] = str(m["created_at"])
                    return uid, json.dumps({
                        "ok": True,
                        "user_id": uid,
                        "username": user["username"],
                        "stats": stats,
                        "moods": moods,
                        "chat_count": chat_count,
                    })

                else:
                    return 0, json.dumps({"ok": False, "error": "Unknown action"})

            except Exception as e:
                log.error(f"Auth error: {e}")
                return 0, json.dumps({"ok": False, "error": "Server error — please try again"})

        # ── Handler: Chat ────────────────────────────────────────────────────
        def handle_chat(
            user_msg: str,
            chat_hist: list,
            mood_hist: list,
            username: str,
            user_id: int,
        ):
            """Process a user chat message and return the bot's reply."""
            user_msg = (user_msg or "").strip()
            if not user_msg:
                return chat_hist, "", ""

            username = (username or "Friend").strip() or "Friend"

            # Generate bot response via RAG + Gemini
            bot_html = get_bot_response(user_msg, chat_hist, username)

            # Store raw text (strip HTML) for conversation history sent to Gemini
            bot_raw = re.sub(r"<[^>]+>", "", bot_html)
            bot_raw = bot_raw.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            bot_raw = bot_raw.replace("&quot;", '"').replace("&#039;", "'")

            # Build history entry
            today = datetime.date.today().strftime("%d %b")
            current_mood_label = mood_hist[-1]["label"] if mood_hist else "😐 Okay"
            current_mood_color = mood_hist[-1]["color"] if mood_hist else "#e8c4a0"

            chat_hist = chat_hist + [{
                "user":       user_msg,
                "bot_raw":    bot_raw,
                "bot_html":   bot_html,
                "mood_label": current_mood_label,
                "color":      current_mood_color,
                "date":       today,
            }]

            # Persist to DB for registered users (not guests)
            if user_id and user_id > 0:
                try:
                    db.save_chat_message(
                        user_id, user_msg, bot_raw,
                        current_mood_label, current_mood_color
                    )
                    db.increment_session(user_id)
                except Exception as e:
                    log.warning(f"DB save failed (non-fatal): {e}")

            # Build sidebar history HTML
            hist_html = _build_hist_html(chat_hist)

            log.info(f"💬 {username}: \"{user_msg[:50]}...\" → response sent")
            return chat_hist, bot_html, hist_html

        # ── Handler: Mood ────────────────────────────────────────────────────
        def handle_mood(
            mood_json: str,
            mood_hist: list,
            username: str,
            user_id: int,
        ):
            """Process a mood selection and persist it."""
            mood_json = (mood_json or "").strip()
            if not mood_json:
                return mood_hist

            try:
                data = json.loads(mood_json)
                mood_hist = mood_hist + [data]

                # Persist to DB for registered users (not guests)
                if user_id and user_id > 0:
                    db.save_mood(
                        user_id,
                        data.get("score", 3),
                        data.get("label", "😐 Okay"),
                        data.get("color", "#e8c4a0"),
                        data.get("date", ""),
                    )
            except (json.JSONDecodeError, TypeError) as e:
                log.warning(f"Invalid mood JSON: {e}")

            return mood_hist

        # ── Wire events ──────────────────────────────────────────────────────
        # show_progress="hidden" suppresses Gradio's built-in loading overlay
        # which otherwise blocks the custom HTML chat UI (looks "stuck").

        # Auth: login / signup
        auth_input.submit(
            handle_auth,
            inputs=[auth_input],
            outputs=[user_id_state, auth_out],
            show_progress="hidden",
        )

        # Chat: when JS submits a message via the hidden textbox
        user_input.submit(
            handle_chat,
            inputs=[user_input, chat_history_state, mood_history_state,
                    username_input, user_id_state],
            outputs=[chat_history_state, reply_out, hist_out],
            show_progress="hidden",
            concurrency_limit=None,
        )

        # Mood: when JS pushes a mood selection via the hidden textbox
        mood_input.submit(
            handle_mood,
            inputs=[mood_input, mood_history_state, username_input, user_id_state],
            outputs=[mood_history_state],
            show_progress="hidden",
        )

        # Bridge: when Python updates reply_out, push it to the custom chat UI
        reply_out.change(
            fn=None,
            inputs=[reply_out, hist_out],
            js="""
            (reply, hist) => {
              if (!reply) return [reply, hist];
              if (window.receiveReply) window.receiveReply(reply, hist);
              return ['', ''];
            }
            """,
            outputs=[reply_out, hist_out],
            show_progress="hidden",
        )

        # Bridge: when Python updates auth_out, push auth result to JS
        auth_out.change(
            fn=None,
            inputs=[auth_out],
            js="""
            (authResult) => {
              if (!authResult) return [''];
              if (window.receiveAuth) window.receiveAuth(authResult);
              return [''];
            }
            """,
            outputs=[auth_out],
            show_progress="hidden",
        )

    return demo


#  SECTION 11 — LAUNCH

log.info("=" * 60)
log.info("  MentalTalk — AI Mental Health Companion")
log.info("=" * 60)

# Build at module level — required for HF Spaces to discover the `demo` object.
# css / theme / head are baked into gr.Blocks() (Gradio 5.x style).
demo = build_app()

if __name__ == "__main__":
    # Local dev: python app.py
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        ssr_mode=False,
    )
else:
    # HF Spaces runner
    demo.launch(
        server_name="0.0.0.0",
        share=False,
        ssr_mode=False,
    )
