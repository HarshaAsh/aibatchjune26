# Gemini Chat Streamlit App

A simple Streamlit chatbot that uses Google Gemini to respond to chat messages.  

Chatbot link: https://enterprise-chatbot.streamlit.app/

## Features
- Chat-style interface built with Streamlit
- Uses Google Gemini via the `google.generativeai` SDK
- Reads the API key and model name from a `.env` file
- Sidebar intake for PDF uploads and web links (stored in session state for future RAG integration)
- Source ingestion pipeline: extracts PDF/HTML text, chunks it, embeds it, and stores vectors in Qdrant collection `my-chat-documents`
- RAG retrieval mode: after ingestion, answers are generated from Qdrant context only and always include references

# missing features
- delete rag collection
- add metadata

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
GEMINI_MODEL=gemini-2.5-flash
QDRANT_URL=https://your-qdrant-instance
QDRANT_API_KEY=your_qdrant_api_key
GEMINI_EMBEDDING_MODEL=models/embedding-001
```

## Run the App
```bash
streamlit run app.py
```

## Notes
- Keep your API key private and do not commit it to version control.
