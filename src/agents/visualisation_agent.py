from __future__ import annotations

from typing import Any, Dict, List, Optional

import plotly.graph_objects as go
import plotly.io as pio


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def build_chart_json(records: List[Dict[str, Any]]) -> Optional[str]:
    if not records:
        return None

    sample = records[0]
    numeric_columns = [key for key, value in sample.items() if _is_number(value)]
    if not numeric_columns:
        return None

    x_column = next((key for key in sample.keys() if key not in numeric_columns), None)
    y_column = numeric_columns[0]

    x_values = [row.get(x_column) if x_column else index + 1 for index, row in enumerate(records)]
    y_values = [row.get(y_column) for row in records]

    figure = go.Figure(
        data=[go.Bar(x=x_values, y=y_values, marker_color="#1f77b4")]
    )
    figure.update_layout(
        title=f"{y_column} by {x_column or 'row'}",
        xaxis_title=x_column or "row",
        yaxis_title=y_column,
        template="plotly_white",
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    return pio.to_json(figure)


def run_visualisation_agent(sql_result: Dict[str, Any]) -> Dict[str, Any]:
    chart_json = build_chart_json(sql_result.get("data", []))
    return {
        "status": "success" if chart_json else "skipped",
        "chart_json": chart_json,
    }