# Enterprise Financial Intelligence Chatbot

## Setup

Install the Python dependencies from `requirements.txt` and configure the required credentials in a local `.env` file. Keep `.env` out of version control.

Start the Streamlit application from the repository root with:

```powershell
streamlit run app.py
```

## SQL integration check

The live integration runner is in `tests/sql_integration.py`. Run it from the repository root after installing the dependencies and configuring `.env`:

```powershell
python tests/sql_integration.py
```

This runner sends a request to OpenAI and queries the configured PostgreSQL database. It makes up to three attempts, feeding each SQL execution error into the next generation prompt. Run it deliberately; it is not a routine unit test.

The retry loop currently exists only in this integration runner. Production retries will require a LangGraph conditional edge that routes failed SQL execution back to SQL generation while the retry limit has not been reached.