import io

import pandas as pd


def parse_csv(csv_data: str) -> pd.DataFrame:
    """Read CSV text into a DataFrame."""
    return pd.read_csv(io.StringIO(csv_data))


def build_dataset_summary(df: pd.DataFrame) -> dict:
    """Build human-readable dataset metadata and descriptive statistics."""
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    column_info = [
        {"name": col, "dtype": str(df[col].dtype)} for col in df.columns
    ]

    return {
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "columns": df.columns.tolist(),
        "column_info": column_info,
        "numeric_columns": numeric_cols,
        "shape_label": f"{df.shape[0]} hàng x {df.shape[1]} cột",
        "column_label": ", ".join(f"{col} ({df[col].dtype})" for col in df.columns),
        "describe_text": df.describe().to_string(),
        "summary_stats": df.describe().to_dict(),
    }


def build_chart_data(df: pd.DataFrame, numeric_cols: list[str]) -> dict:
    """Prepare chart-friendly JSON for the dashboard frontend."""
    charts: dict = {}

    if not numeric_cols:
        return charts

    charts["mean_bar"] = {
        "type": "bar",
        "title": "Giá trị trung bình theo cột",
        "labels": numeric_cols,
        "values": [round(float(df[col].mean()), 2) for col in numeric_cols],
    }

    if len(df) <= 100:
        first_numeric_col = numeric_cols[0]
        charts["trend_line"] = {
            "type": "line",
            "title": f"Xu hướng: {first_numeric_col}",
            "labels": list(range(len(df))),
            "values": df[first_numeric_col].fillna(0).tolist(),
        }

    return charts
