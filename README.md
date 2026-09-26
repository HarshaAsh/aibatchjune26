# Gemini Enterprise Agent Streamlit App

A Streamlit-based enterprise assistant that uses Google Gemini, LangGraph, SQL, RAG, and optional external search to answer business questions with grounded evidence.

Chatbot link: https://enterprise-chatbot.streamlit.app/

## Features
- Chat-style interface built with Streamlit
- Uses Google Gemini for routing, synthesis, and grounded responses
- Reads the API key and model name from a `.env` file
- LangGraph supervisor flow for SQL, RAG, external search, and visualisation routing
- Sidebar intake for PDF uploads and web links
- Source ingestion pipeline: extracts PDF/HTML text, chunks it, embeds it, and stores vectors in Qdrant collection `my-chat-documents`
- RAG retrieval mode grounded in Qdrant context with references
- Read-only SQL agent with schema-aware query generation and bounded retries
- Optional Serper-powered external search for latest updates
- Plotly chart rendering for trend and comparison prompts

# current limitations
- No built-in authentication yet
- No admin panel yet
- SQL answers depend on a correctly configured relational database in `.env`

## Requirements
- Python 3.9+
- Install dependencies with:

```bash
pip install -r requirements.txt
```

## Environment Setup
Create a `.env` file in the project root with:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
QDRANT_URL=https://your-qdrant-instance
QDRANT_API_KEY=your_qdrant_api_key
GEMINI_EMBEDDING_MODEL=models/embedding-001
DATABASE_URL=postgresql+psycopg://user:password@host:5432/database
SERPER_API_KEY=your_serper_api_key
```

You can use `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, and `DB_NAME` instead of `DATABASE_URL` if preferred.

## Run the App
```bash
streamlit run app.py
```

## Notes
- Keep your API key private and do not commit it to version control.
- If the SQL database or Serper is not configured, the graph degrades gracefully and still answers from the available branches.
