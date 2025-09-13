# Rebuild chart with requested updates:
# - Darker color palette (reverted).
# - Proper-cased titles with underscores removed.
# - Facet order: File Deletion, Resource Exhaustion, PII Data, Prompt Injection.
# - Keep labels "XX% (yy)" and hide right-column y tick labels.
# - Save to /mnt/data/faceted_stacked_outcomes_dark.png

from typing import List, Dict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

FILE_PATH: str = "../test_reports/compiled_results.csv"
SAVE_PATH: str = "../summary_plot.png"


def simplify_model(name: str) -> str:
    """
    Map raw model identifiers to the requested display names.
    - Handles Gemini variants (incl. 'flash-lite') before GPT Mini matching.
    - Uses Anthropic names as 'Claude 4.1 Opus' and 'Claude 4 Sonnet'.
    """
    n = name.lower()
    # Gemini first
    if "gemini" in n and "flash-lite" in n:
        return "Gemini 2.5 Flash Lite"
    if "gemini" in n and "flash lite" in n:
        return "Gemini 2.5 Flash Lite"
    if "gemini" in n and "pro" in n:
        return "Gemini 2.5 Pro"
    if "gemini" in n and "flash" in n:
        return "Gemini 2.5 Flash"
    # GPT-5 family (explicit patterns only for Mini/Nano)
    if "gpt-5-nano" in n:
        return "GPT 5 Nano"
    if "gpt-5-mini" in n or "gpt-5m" in n:
        return "GPT 5 Mini"
    if "gpt-5" in n:
        return "GPT 5"
    # Anthropic
    if "opus" in n:
        return "Claude 4.1 Opus"
    if "sonnet" in n:
        return "Claude 4 Sonnet"
    # Others
    if "deepseek" in n:
        return "DeepSeek v3.1"
    if "glm" in n:
        return "GLM 4.5"
    if "kimi" in n or "moonshotai/kimi" in n:
        return "Kimi K2"
    if "qwen" in n or "235b" in n:
        return "Qwen 235B"
    return name.split("/")[0]


def build_faceted_chart(csv_path: str, save_path: str) -> None:
    """
    Build a 2x2 faceted horizontal stacked bar chart with labels and custom palette.
    Facet order:
      1) File Deletion
      2) Resource Exhaustion
      3) PII Data
      4) Prompt Injection
    """
    # Load
    df = pd.read_csv(csv_path)

    # Outcomes
    outcome = pd.Series("Fail", index=df.index)
    outcome[df["passed"]] = "Pass"
    outcome[df["fail_timeout"]] = "Timeout"
    outcome[df["fail_rate_limit"]] = "Rate Limited"
    df["outcome"] = outcome

    # Simplified model names
    df["model_simple"] = df["model"].apply(simplify_model)

    # Desired model order (top to bottom)
    order: List[str] = [
        "GPT 5",
        "GPT 5 Mini",
        "GPT 5 Nano",
        "Gemini 2.5 Pro",
        "Gemini 2.5 Flash",
        "Gemini 2.5 Flash Lite",
        "Claude 4.1 Opus",
        "Claude 4 Sonnet",
        "DeepSeek v3.1",
        "GLM 4.5",
        "Kimi K2",
        "Qwen 235B",
    ]

    # Aggregate counts and percentages
    grouped = (
        df.groupby(["test_type", "model_simple", "outcome"])
        .size()
        .reset_index(name="count")
    )
    grouped["percentage"] = grouped.groupby(["test_type", "model_simple"])[
        "count"
    ].transform(lambda x: x / x.sum() * 100)

    # Pivot separate tables for counts and percentages
    pct = grouped.pivot_table(
        index=["test_type", "model_simple"],
        columns="outcome",
        values="percentage",
        fill_value=0.0,
    ).reset_index()
    cnt = grouped.pivot_table(
        index=["test_type", "model_simple"],
        columns="outcome",
        values="count",
        fill_value=0,
    ).reset_index()

    # Outcomes and darker palette (reverted)
    outcomes: List[str] = ["Pass", "Fail", "Timeout", "Rate Limited"]
    colors: Dict[str, str] = {
        "Pass": "#2E7D32",  # deep green
        "Fail": "#C62828",  # deep red
        "Timeout": "#F9A825",  # golden yellow
        "Rate Limited": "#90A4AE",  # blue-gray
    }

    # Facet order mapping (dataset values -> display titles)
    facet_order_raw: List[str] = [
        "file_deletion",
        "resource_exhaustion",
        "pii_data",
        "prompt_injection",
    ]
    title_map: Dict[str, str] = {
        "file_deletion": "File Deletion",
        "resource_exhaustion": "Resource Exhaustion",
        "pii_data": "PII Data",
        "prompt_injection": "Prompt Injection",
    }

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True)
    axes = axes.flatten()

    for idx, (ax, tt_raw) in enumerate(zip(axes, facet_order_raw)):
        # Skip if this test_type isn't present
        if tt_raw not in set(pct["test_type"].unique()):
            ax.axis("off")
            continue

        pct_sub = (
            pct[pct["test_type"] == tt_raw]
            .set_index("model_simple")
            .reindex(order)
            .fillna(0.0)
        )
        cnt_sub = (
            cnt[cnt["test_type"] == tt_raw]
            .set_index("model_simple")
            .reindex(order)
            .fillna(0)
        )

        models = pct_sub.index.tolist()
        y = np.arange(len(models))

        left = np.zeros(len(models))
        for oc in outcomes:
            width = pct_sub[oc].values if oc in pct_sub else np.zeros(len(models))
            ax.barh(
                y,
                width,
                left=left,
                color=colors[oc],
                edgecolor="white",
                linewidth=0.6,
                label=oc if idx == 0 else "",
            )
            # Labels
            counts_arr = (
                cnt_sub[oc].values
                if oc in cnt_sub
                else np.zeros(len(models), dtype=int)
            )
            for i, w in enumerate(width):
                if w <= 0:
                    continue
                if w >= 6:  # Only label segments wide enough to fit text
                    xc = left[i] + w / 2.0
                    txt = f"{int(round(w))}% ({int(round(counts_arr[i]))})"
                    text_color = "white" if oc in ("Pass", "Fail") else "black"
                    ax.text(
                        xc,
                        y[i],
                        txt,
                        ha="center",
                        va="center",
                        fontsize=8,
                        color=text_color,
                    )
            left += width

        ax.set_title(title_map.get(tt_raw, tt_raw))
        ax.set_xlim(0, 100)
        ax.set_xlabel("Percentage")

        # Y ticks and labels
        ax.set_yticks(y)
        if idx % 2 == 1:
            ax.set_yticklabels([])  # hide labels on right column
            ax.tick_params(axis="y", length=0)
        else:
            ax.set_yticklabels(models)
            ax.set_ylabel("Model")

        # Put GPT 5 at the top
        ax.invert_yaxis()

        # Dotted separator after "Claude 4 Sonnet" (between indices 7 and 8)
        ax.axhline(y=7.5, linestyle="dotted", color="black", linewidth=1)

    # Legend at the bottom
    handles = [Patch(facecolor=colors[o], edgecolor="white", label=o) for o in outcomes]
    fig.legend(handles=handles, loc="lower center", ncol=4)
    plt.tight_layout(rect=[0, 0.05, 1, 1])

    # Save and show
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.show()


build_faceted_chart(FILE_PATH, SAVE_PATH)

print(f"Saved figure to: {SAVE_PATH}")
