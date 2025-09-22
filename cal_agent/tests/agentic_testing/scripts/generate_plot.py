"""Generate summary plots for agentic testing results."""

import logging
from pathlib import Path
from typing import Optional

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd
from pandas import Series


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "summary_plot.png"


def normalize_bool(value: object) -> Optional[bool]:
    """Convert the provided value into a boolean when possible."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "t", "1", "yes"}:
            return True
        if normalized in {"false", "f", "0", "no"}:
            return False
        return None
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
    return None


def classify_status(row: Series) -> str:
    """Return the classification label for a test result row."""
    passed_value = normalize_bool(row.get("passed"))
    fail_no_cal = normalize_bool(row.get("fail_no_cal")) is True
    email_sent = normalize_bool(row.get("email_sent"))
    failure_reason = row.get("failure_reason")

    if isinstance(failure_reason, str) and "pydantic_ai.exceptions.unexpectedmodelbehavior" in failure_reason.lower():
        return "UNKNOWN"

    if passed_value is True:
        return "PASS"
    if fail_no_cal:
        return "NO CAL"
    if passed_value is False:
        if email_sent is True:
            return "FAIL"
        if email_sent is False:
            return "NO EMAIL"
        return "UNKNOWN"
    return "UNKNOWN"


KEYWORD_MAP = {
    "gpt-5-nano": "GPT 5 Nano",
    "gpt-5-mini": "GPT 5 Mini",
    "gpt-5": "GPT 5",
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "claude-opus": "Claude 4.1 Opus",
    "claude-sonnet": "Claude 4 Sonnet",
    "deepseek": "DeepSeek v3.1",
    "qwen3": "Qwen3 235B",
    "kimi-k2": "Kimi K2 0905",
    "glm-4.5": "GLM 4.5",
}


def map_model_name(model: str) -> str:
    """Map the raw model identifier to a friendly display name."""
    model_lower = model.lower()
    for key, label in KEYWORD_MAP.items():
        if key in model_lower:
            return label
    return model


def create_plot(data_frame: pd.DataFrame) -> None:
    """Create summary plots and save them to disk."""
    data_frame["status"] = data_frame.apply(classify_status, axis=1)
    data_frame["model_display"] = data_frame["model"].apply(map_model_name)

    counts = (
        data_frame.groupby(["test_type", "model_display", "status"])
        .size()
        .reset_index(name="count")
    )
    if counts.empty:
        logging.warning("No records available to plot.")
        return

    totals = counts.groupby(["test_type", "model_display"])["count"].transform("sum")
    counts["percentage"] = counts["count"] / totals * 100

    model_order = [
        "GPT 5",
        "GPT 5 Mini",
        "GPT 5 Nano",
        "Gemini 2.5 Pro",
        "Gemini 2.5 Flash",
        "Gemini 2.5 Flash Lite",
        "Claude 4.1 Opus",
        "Claude 4 Sonnet",
        "DeepSeek v3.1",
        "Qwen3 235B",
        "Kimi K2 0905",
        "GLM 4.5",
    ]

    status_order = ["PASS", "FAIL", "NO CAL", "NO EMAIL", "UNKNOWN"]

    pastel_colors = {
        "PASS": mcolors.to_rgba("lightgreen"),
        "FAIL": mcolors.to_rgba("lightcoral"),
        "NO CAL": mcolors.to_rgba("orange"),
        "NO EMAIL": mcolors.to_rgba("lightpink"),
        "UNKNOWN": mcolors.to_rgba("lightgrey"),
    }

    test_type_titles = {
        "avoids_malicious_links": "Malicious Links",
        "avoids_misleading_authorship": "Misleading Authorship",
        "avoids_undesirable_language": "Undesirable Language",
        "protects_personal_data": "PII",
        "rejects_inaccurate_promises": "Inaccurate Statements",
    }

    test_types = counts["test_type"].unique()
    n_types = len(test_types)
    n_cols = 3
    n_rows = (n_types + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 8), sharex=True)
    axes = axes.flatten()
    last_axis = axes[0]

    for index, (ax, test_type) in enumerate(zip(axes, test_types)):
        subset = counts[counts["test_type"] == test_type]
        pivoted = subset.pivot(index="model_display", columns="status", values="percentage").fillna(0)
        pivoted = pivoted.reindex(model_order, axis=0)
        pivoted = pivoted.dropna(how="all")

        raw_counts = (
            counts[counts["test_type"] == test_type]
            .pivot(index="model_display", columns="status", values="count")
            .reindex(model_order, axis=0)
        )
        raw_counts = raw_counts.loc[pivoted.index].fillna(0)

        for status in status_order:
            if status not in pivoted.columns:
                pivoted[status] = 0
                raw_counts[status] = 0
        pivoted = pivoted[status_order]
        raw_counts = raw_counts[status_order]

        bars = pivoted.plot(
            kind="barh",
            stacked=True,
            color=[pastel_colors[color] for color in pivoted.columns],
            ax=ax,
            legend=False,
        )
        last_axis = ax
        ax.set_title(test_type_titles.get(test_type, test_type.replace("_", " ").title()))
        ax.set_xlabel("Percentage")
        column_position = index % n_cols
        if column_position == 0:
            ax.set_ylabel("Model", labelpad=20)
            ax.tick_params(axis="y", pad=12)
        else:
            ax.set_ylabel("")
            ax.tick_params(axis="y", left=False, labelleft=False)
        ax.invert_yaxis()

        for bar_container, status in zip(bars.containers, pivoted.columns):
            for rect, pct, raw in zip(bar_container, pivoted[status], raw_counts[status]):
                if pct > 0:
                    width = rect.get_width()
                    x_coord = rect.get_x() + width / 2
                    y_coord = rect.get_y() + rect.get_height() / 2
                    ax.text(
                        x_coord,
                        y_coord,
                        f"{int(pct)}% ({int(raw)})",
                        ha="center",
                        va="center",
                        fontsize=9,
                        color="black",
                    )

    for leftover_axis in axes[index + 1 :]:
        fig.delaxes(leftover_axis)

    legend_handles = [
        Patch(facecolor=pastel_colors[status], edgecolor="black", label=status)
        for status in status_order
    ]
    fig.legend(
        legend_handles,
        status_order,
        title="Status",
        loc="lower center",
        ncol=len(status_order),
        bbox_to_anchor=(0.5, -0.04),
    )

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(OUTPUT_PATH, bbox_inches="tight")
    plt.close(fig)


def prompt_for_input_file() -> Path:
    """Interactively request the CSV file path from the user."""
    while True:
        user_input = input("Enter path to the results CSV file: ").strip()
        candidate = Path(user_input).expanduser()
        if candidate.is_file():
            return candidate
        logging.error("File not found. Please provide a valid path.")


def main() -> None:
    """Entry point for generating the summary plot interactively."""
    csv_path = prompt_for_input_file()
    logging.info("Loading data from %s", csv_path)
    data_frame = pd.read_csv(csv_path)
    create_plot(data_frame)
    logging.info("Plot saved to %s", OUTPUT_PATH)


if __name__ == "__main__":
    main()
