Skill: Visualisation — Plotly Renderer
=====================================

Purpose
-------
Convert structured tabular results into clear, accessible Plotly visuals and small PNG thumbnails for Streamlit display and downloads.

When to use
-----------
- Whenever the SQL agent (or combined Supervisor output) returns tabular data that benefits from a chart.

Inputs
------
- `pandas.DataFrame`, a user intent hint (e.g., "trend", "compare categories"), optional axis preferences.

Outputs
-------
- Plotly Figure object and a PNG thumbnail, plus `caption` and `alt_text` strings.

Step-by-step
-----------
1. Inspect DataFrame: identify time column, numeric columns, categorical columns.
2. Choose chart type: time-series -> line; categorical comparison -> bar; distribution -> histogram; correlation -> scatter.
3. Build Plotly figure with clean labels and a brief caption; generate a PNG via `fig.to_image()` for thumbnail.
4. Return `{'figure': fig, 'png_bytes': b'...', 'caption': str, 'alt_text': str}`.

Decision points
---------------
- Chart choice heuristics can be tuned; allow admin/user overrides in the UI.

Quality criteria
----------------
- Charts must have readable labels, reasonable default colours, and accessible `alt_text`.
- PNG thumbnails must be < 500KB for quick UI load.

Files & hooks
-------------
- Implement `src/agents/visualisation_agent.py` with hooks `pre_visualise` and `post_visualise`.

Example prompts
---------------
- "Render the returned table as the most suitable Plotly chart and return a PNG thumbnail." 
