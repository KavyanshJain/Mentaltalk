<<<<<<< HEAD
---

title: MentalTalk
emoji: 🧠
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: "5.29.0"
app_file: app.py
pinned: false
license: mit
---

# 🧠 MentalTalk — AI Mental Health Companion

A compassionate, AI-powered mental health chatbot built with **Gradio**, **Gemini 2.5 Flash-Lite**, and a **RAG pipeline** backed by WHO & clinical mental health resources.

> **⚠️ Disclaimer:** MentalTalk is an AI companion for emotional support and wellness guidance. It is **not** a substitute for professional mental health care. If you are in crisis, please contact a helpline immediately.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Chat** | Empathetic, evidence-based responses powered by Gemini 2.5 Flash-Lite |
| 📚 **RAG Pipeline** | Retrieves context from 28 WHO/clinical mental health PDFs via ChromaDB |
| 🎭 **Mood Dashboard** | Log your daily mood, view 7-day patterns, streaks & statistics |
| 🆘 **Crisis Support** | Instant crisis resource display (India helplines) |
| 🔐 **Privacy** | Conversations stay in-session; mood data persists locally |
| 🎨 **Premium UI** | Dark-themed, animated interface with glassmorphism design |

---

## 🏗️ Project Structure

```
Mentaltalk-1/
├── app.py                 ← Main application (run this)
├── requirements.txt       ← Python dependencies
├── .env.example           ← Template for API key
├── mood_data.json         ← Auto-created mood persistence
│
├── static/
│   └── index.html         ← Full chat UI (HTML/CSS/JS)
│
├── rag/
│   ├── __init__.py
│   ├── ingest.py          ← PDF → ChromaDB ingestion script
│   └── retriever.py       ← Vector search retrieval module
│
├── chroma_db/             ← Pre-built vector embeddings
│   └── ...
│
├── data/                  ← Source PDFs (28 mental health documents)
│   └── *.pdf
│
└── gradio_temp.py         ← Original UI prototype (reference only)
```

---

## 🚀 Local Setup & Testing

### Prerequisites

- **Python 3.10+**
- **Gemini API key** (free) — get one at [Google AI Studio](https://aistudio.google.com/apikey)
- Pre-built `chroma_db/` directory (from running `ingest.py`)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note (Disk Space):** The embedding model (`google/embeddinggemma-300m`) will be downloaded (~600MB) on first run. If your C: drive is full, the app automatically caches it to `D:\hf_cache` on Windows.

### Step 2: Set Your API Key

**Option A — Environment variable (recommended for quick testing):**

```powershell
# PowerShell
$env:GEMINI_API_KEY = "your_gemini_api_key_here"
```

```cmd
# Command Prompt
set GEMINI_API_KEY=your_gemini_api_key_here
```

**Option B — `.env` file (persistent):**

```bash
# Copy the template and edit it
copy .env.example .env
# Then edit .env and paste your key
```

### Step 3: Run the App

```bash
python app.py
```

You should see output like:

```
14:00:00 │ INFO     │ ════════════════════════════════════════════════════════════
14:00:00 │ INFO     │   MentalTalk — AI Mental Health Companion
14:00:00 │ INFO     │ ════════════════════════════════════════════════════════════
14:00:01 │ INFO     │ ✅ Gemini client initialized (model: gemini-2.5-flash-lite)
14:00:03 │ INFO     │ ✅ ChromaDB loaded — 2847 chunks in 'mental_health'
14:00:03 │ INFO     │ Running on local URL:  http://0.0.0.0:7860
```

### Step 4: Open in Browser

Navigate to **<http://localhost:7860>**

- Sign in with any name (or continue as Guest)
- Try the quick prompts or type your own message
- Select moods in the sidebar to see the dashboard update
- Click "🆘 Crisis Support" to see helpline information

---

## ☁️ Deploy to Hugging Face Spaces

### Step 1: Create a New Space

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. Choose:
   - **Space name:** `MentalTalk` (or your preference)
   - **SDK:** `Gradio`
   - **Hardware:** `CPU Basic` (free tier works fine)
3. Click **Create Space**

### Step 2: Add Your API Key as a Secret

1. Go to your Space → **Settings** → **Variables and secrets**
2. Click **New secret**
3. Name: `GEMINI_API_KEY`
4. Value: Your Gemini API key
5. Click **Save**

### Step 3: Upload Files

Upload these files/folders to your Space (via the web UI or `git`):

```
app.py
requirements.txt
static/
  └── index.html
rag/
  ├── __init__.py
  └── retriever.py
chroma_db/
  └── (all files inside)
```

> **Important:** The `chroma_db/` folder (~40MB) contains your pre-built vector embeddings. Without it, the chatbot works but without RAG context.

**Using Git:**

```bash
# Clone your Space
git clone https://huggingface.co/spaces/YOUR_USERNAME/MentalTalk
cd MentalTalk

# Copy your project files
copy /Y D:\project\Mentaltalk-1\app.py .
copy /Y D:\project\Mentaltalk-1\requirements.txt .
xcopy /E /I D:\project\Mentaltalk-1\static static
xcopy /E /I D:\project\Mentaltalk-1\rag rag
xcopy /E /I D:\project\Mentaltalk-1\chroma_db chroma_db

# Push to HF
git add .
git commit -m "Initial MentalTalk deployment"
git push
```

### Step 4: Wait for Build

The Space will automatically install dependencies and start. First build takes ~3-5 minutes (downloading the embedding model).

### Step 5: Share Your Space

Once running, your Space URL will be:

```
https://huggingface.co/spaces/YOUR_USERNAME/MentalTalk
```

---

## 🔧 How It Works

### Architecture

```
User Input → Gradio JS Bridge → Python Backend
                                      │
                                      ├─→ RAG Retriever (ChromaDB)
                                      │        → Top-5 relevant chunks
                                      │
                                      ├─→ Gemini 2.5 Flash-Lite
                                      │        → System prompt + context + history
                                      │        → Empathetic, evidence-based response
                                      │
                                      └─→ Mood Store (JSON persistence)
                                               → Per-user mood logging
```

### RAG Pipeline

1. **Ingestion** (`rag/ingest.py`): Extracts text from 28 PDFs → chunks into 500-char segments → embeds with `google/embeddinggemma-300m` → stores in ChromaDB
2. **Retrieval** (`rag/retriever.py`): For each user message, queries ChromaDB for the top-5 most semantically similar chunks
3. **Generation** (`app.py`): Injects retrieved context into the Gemini prompt alongside conversation history

### Mood Dashboard

- **Per-session:** Chart, stats, and streak update live in the browser (JavaScript)
- **Per-user persistence:** Each mood selection is saved to `mood_data.json` with timestamps, keyed by username
- **Data survives restarts** locally (on HF Spaces, ephemeral storage resets on Space restart)

---

## 📝 Files You Don't Need to Upload

These files are only used during development and are **not needed** for deployment:

| File | Purpose |
|------|---------|
| `data/*.pdf` | Source PDFs (already embedded in `chroma_db/`) |
| `rag/ingest.py` | Ingestion script (run once locally) |
| `gradio_temp.py` | Original UI prototype |
| `.env` / `.env.example` | Local dev only (use HF Secrets instead) |
| `mood_data.json` | Auto-created at runtime |
| `orchestrator.py` | Placeholder (unused) |
| `auth.py` | Placeholder (unused) |
| `dashboard/` | Placeholder (unused) |
| `mcp/` | Placeholder (unused) |

---

## 🛟 Troubleshooting

| Issue | Solution |
|-------|----------|
| "GEMINI_API_KEY not set" | Set the env var or create a `.env` file |
| "ChromaDB directory not found" | Run `python rag/ingest.py` first |
| "Not enough disk space" | Set `HF_HOME=D:\hf_cache` before running |
| Slow first start | Embedding model download (~600MB) — only happens once |
| Safety-blocked responses | The app handles this gracefully with fallback messages |

---

## 📄 License

This project is for educational and demonstration purposes.

Mental health resources referenced: WHO mhGAP guidelines, CBT manuals, NIMHANS guidelines, and other publicly available clinical documents.
