# Enterprise Financial Intelligence Chatbot

## Setup

Install the Python dependencies from `requirements.txt`. Copy [.env.example](.env.example) to `.env` and replace the placeholders with local credentials. Keep `.env` out of version control.

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

## Retrieval-augmented generation

The RAG path separates retrieval from answering:

1. [src/tools/rag.py](src/tools/rag.py) embeds the question with OpenAI's `text-embedding-3-small` model and calls the Supabase `match_documents` RPC.
2. The RPC returns matching document rows. Each row should include a `content` field, and its stored embedding dimension must match the embedding model.
3. [src/agents/rag_agent.py](src/agents/rag_agent.py) formats retrieved passages into `rag_context`. Its answer node instructs OpenAI to use only that context and to say when it does not contain enough information.

The current RPC call sends `query_embedding` and `match_count`. Keep these parameter names aligned with the function deployed in Supabase. Do not add `match_threshold` unless the deployed function accepts it; PostgREST rejects arguments that are not in the function signature.

Run the live RAG integration check from the repository root with:

```powershell
python tests/test_rag.py
```

This check calls OpenAI for embeddings and an answer, and calls the Supabase RPC for retrieval. It is a live integration check, not an offline unit test. It checks the retrieval and answer nodes directly; the current Streamlit chat page does not compile or invoke a complete production LangGraph workflow.

The RAG example follows the [Enterprise Chatbot article](https://www.harshaash.com/Python/Enterprise%20Chatbot%20Example/): retrieval embeds the question, fetches related chunks from Supabase, and passes those chunks to an answer node. The implementation in this repository keeps these steps in separate tool and agent modules.

## External news search

The external-search path uses [src/agents/news_agent.py](src/agents/news_agent.py) and [src/tools/search.py](src/tools/search.py). The news node sends the user's query to Serper's Google Search API, serialises the returned JSON into `external_context`, and limits that context to 5,000 characters. If the search or result conversion fails, the node returns an empty context so the workflow can continue without news data.

`src/config.py` loads `SERPER_API_KEY` from the environment or local `.env` into `AppConfig.serper_api_key`. It is a required setting, like the other configured credentials. The variable is included in [.env.example](.env.example); provide your own Serper API key locally and never commit it.

Run the live Serper integration check from the repository root with:

```powershell
python tests/test_news.py
```

This check makes a request to Serper and requires a valid `SERPER_API_KEY` and network access. It is a manual integration check, not an offline unit test. Search results are time-sensitive external evidence; check dates and source links before relying on them.