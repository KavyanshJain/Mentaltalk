# MentalTalk

> A mental health support chatbot — my university minor project

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org) [![Streamlit](https://img.shields.io/badge/streamlit-1.28+-ff4b4b.svg)](https://streamlit.io) [![Gemini](https://img.shields.io/badge/gemini-api-4285f4.svg)](https://ai.google.dev)

## Made By
- [Kavyansh Jain](https://github.com/KavyanshJain) 
- [Om Prajapti](https://github.com/omprajapti)

*Minor Project — School of Engineering, Jecrc University, Batch of 2027

---

## What is this?

I built this as part of my minor project at Jecrc University. Mental health is something I care about, and I wanted to create a simple space where people can talk and get thoughtful responses backed by actual mental health resources. It's not a replacement for professional help, but it's a start — and honestly, it was a great way for me to learn about LLM applications, RAG, and full-stack development.

## Features

- User login and signup with session management
- Chat with an AI that understands mental health topics
- Answers are grounded in 28 mental health PDFs using RAG
- Mood dashboard to track your emotional patterns over time
- Chat history — pick up conversations where you left off
- Session restore — your chats are saved and can be revisited

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| LLM | Gemini API |
| Vector Store | ChromaDB |
| Database | Neon PostgreSQL |
| Embeddings | sentence-transformers (local) |
| Deployment | Streamlit Community Cloud |

## How it works

When you send a message, the app searches through 28 mental health PDFs to find relevant information. This context, along with your message, is sent to the Gemini API which generates a helpful response. Your mood is also tracked based on the conversation and stored in the database, so you can see patterns over time in the mood dashboard.

## Setup & Run locally

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/mentaltalk.git
   cd mentaltalk
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with the following variables:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   DATABASE_URL=your_neon_postgres_url
   ```

4. Run the app:
   ```bash
   streamlit run app.py
   ```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | API key from Google Gemini |
| `DATABASE_URL` | PostgreSQL connection URL from Neon |

## Project Structure

```
mentaltalk/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── src/
│   ├── __init__.py
│   ├── database/
│   │   └── __init__.py    # PostgreSQL database operations
│   ├── mood/
│   │   └── analyzer.py    # Mood analysis from chat
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embedder.py    # Sentence transformer embeddings
│   │   ├── ingestion.py   # PDF ingestion and ChromaDB setup
│   │   └── retriever.py   # RAG retrieval logic
│   ├── llm/
│   │   └── gemini_client.py  # Gemini API client
│   └── ui/
│       ├── auth_page.py   # Login and signup page
│       ├── chat_page.py   # Main chat interface
│       └── dashboard_page.py  # Mood dashboard
└── data/
    └── pdfs/              # Source PDFs for RAG
```

## Limitations & Future Scope

Honestly, there's a lot that could be better. Right now, the app is pretty basic — it works, but it's not perfect.

**Limitations:**
- The RAG retrieval could be smarter and more accurate
- Mood tracking is simple and based on text analysis, not a proper assessment
- No conversation history export
- The UI is functional but could be more polished

**Future improvements:**
- Better conversation context handling
- More accurate mood tracking with proper sentiment analysis
- Support for voice input
- Mobile-responsive design
- Export chat history as PDF or text
- Multi-language support

## Acknowledgements

This project wouldn't have been possible without the mental health resources from [PDF sources] that I used for the RAG knowledge base. A big thanks to my professors and peers at Jecrc University for their guidance and support throughout this minor project.

The app is deployed on Streamlit Community Cloud, and the model embeddings are available on Hugging Face at [huggingface.co/Kavyansh575/mentaltalk](https://huggingface.co/Kavyansh575/mentaltalk).
