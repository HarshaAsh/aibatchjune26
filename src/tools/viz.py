"""Generate Plotly chart JSON from SQL result records when useful."""

import ast
import json
import re
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.tools.database import client


CHART_CODE_PROMPT = """You create Plotly charts from tabular data.
Decide whether a chart is appropriate for the user's query and the supplied data.
If a chart is not helpful or not requested, respond with only the word NONE.
Otherwise, respond only with Python code that builds a Plotly figure and assigns it to `fig`.
The code must operate directly on the existing pandas DataFrame `df`, using only `px` or `go`.
Do not import modules, call fig.show(), or include Markdown fences or explanations.
Write straight-line code only. Do not use conditionals, loops, helper functions, or classes.
Prefer one direct assignment such as `fig = px.line(df, x='year', y='revenue')`.

User query:
{query}

DataFrame columns:
{columns}

First three records:
{records}
"""


_ALLOWED_CALL_ROOTS = {"df", "px", "go", "pd", "fig"}
_ALLOWED_CALLS = {
    "df": {
        "groupby", "head", "melt", "pivot_table", "reset_index", "select_dtypes",
        "sort_values", "to_frame", "transpose", "mean", "sum", "max", "min",
        "count", "agg", "aggregate", "rename", "fillna", "dropna", "astype",
    },
    "px": {
        "area", "bar", "box", "density_heatmap", "histogram", "line", "pie",
        "scatter", "scatter_matrix", "strip", "violin", "update_layout",
        "update_traces", "update_xaxes", "update_yaxes",
    },
    "go": {
        "Figure", "Bar", "Box", "Histogram", "Layout", "Scatter", "Violin",
        "update_layout", "update_traces", "update_xaxes", "update_yaxes",
    },
    "pd": {"DataFrame", "to_numeric"},
    "fig": {
        "add_bar", "add_scatter", "add_trace", "update_layout", "update_traces",
        "update_xaxes", "update_yaxes",
    },
}


def _validate_chart_code(code: str) -> None:
    """Reject imports, dunder access, and calls outside chart/dataframe APIs."""
    if len(code) > 8_000:
        raise ValueError("Generated chart code is too long.")
    tree = ast.parse(code, mode="exec")
    if len(list(ast.walk(tree))) > 500:
        raise ValueError("Generated chart code is too complex.")
    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
                ast.Lambda,
                ast.FunctionDef,
                ast.ClassDef,
                ast.While,
                ast.For,
                ast.AsyncFor,
                ast.With,
                ast.AsyncWith,
                ast.Try,
            ),
        ):
            raise ValueError(
                "Generated chart code contains a disallowed construct: "
                f"{type(node).__name__}."
            )
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("Generated chart code contains a disallowed name.")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                raise ValueError("Generated chart code contains a disallowed attribute.")
        if isinstance(node, ast.Call):
            call_name = node.func.attr if isinstance(node.func, ast.Attribute) else None
            target = node.func
            while isinstance(target, (ast.Attribute, ast.Call, ast.Subscript)):
                target = (
                    target.value
                    if isinstance(target, (ast.Attribute, ast.Subscript))
                    else target.func
                )
            if (
                not isinstance(target, ast.Name)
                or target.id not in _ALLOWED_CALL_ROOTS
                or call_name not in _ALLOWED_CALLS[target.id]
            ):
                raise ValueError("Generated chart code calls a disallowed function.")


def generate_and_run_chart_code(query: str, records: list[dict]) -> str | None:
    """Ask OpenAI for an optional Plotly figure and return its JSON form."""
    if not records:
        return None

    try:
        df = pd.DataFrame(records)
        prompt = CHART_CODE_PROMPT.format(
            query=query,
            columns=json.dumps(df.columns.tolist(), ensure_ascii=False),
            records=json.dumps(
                df.head(3).to_dict(orient="records"),
                default=str,
                ensure_ascii=False,
            ),
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        generated_code = response.choices[0].message.content or ""
        generated_code = re.sub(
            r"^\s*```(?:python)?\s*|\s*```\s*$",
            "",
            generated_code,
            flags=re.IGNORECASE,
        )
        generated_code = generated_code.replace("`", "").strip()

        if generated_code.upper() == "NONE":
            print("Chart generation skipped: the model returned NONE.")
            return None
        if not generated_code:
            print("Chart generation failed: the model returned an empty response.")
            return None

        _validate_chart_code(generated_code)
        local_scope: dict[str, Any] = {"df": df, "px": px, "go": go, "pd": pd}
        exec(
            compile(generated_code, "<generated_plotly_code>", "exec"),
            {"__builtins__": {}},
            local_scope,
        )
        figure = local_scope.get("fig")
        return figure.to_json() if figure is not None else None
    except Exception as exc:
        print(f"Chart generation failed ({type(exc).__name__}): {exc}")
        return None
