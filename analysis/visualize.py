"""Create the two capstone charts from the generated EDA artifact."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib-cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


RESULTS_PATH = ROOT / "analysis" / "eda_results.json"
OUTPUT_DIR = ROOT / "visualizations"


def main() -> None:
    if not RESULTS_PATH.exists():
        raise FileNotFoundError(
            "analysis/eda_results.json is missing. Run python analysis/clean_and_eda.py first."
        )
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rates = results["payment_return_rates"]
    payment_order = sorted(rates, key=lambda method: (-rates[method], method))
    labels = payment_order
    values = [rates[method] for method in payment_order]
    card_rate = rates["CARD"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, color=["#c2413b", "#438a70", "#7198c8"])
    ax.bar_label(bars, labels=[f"{value:.1f}%" for value in values], padding=4, fontsize=11)
    ax.set_ylabel("Return rate (%)")
    ax.set_xlabel("Payment method")
    ax.set_ylim(0, max(values) * 1.22)
    ax.set_title(f"COD Returns at {rates['COD']:.1f}% — {rates['COD'] / card_rate:.0f}x Card")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "return_rate_by_payment.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    monthly = results["monthly_revenue_outlier_corrected"]
    months = list(monthly)
    revenue = list(monthly.values())
    peak_index = max(range(len(revenue)), key=revenue.__getitem__)
    peak_month = months[peak_index]
    peak_month_label = datetime.strptime(peak_month, "%Y-%m").strftime("%B %Y")

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(months, revenue, marker="o", linewidth=2.5, color="#2878a5")
    ax.scatter([peak_month], [revenue[peak_index]], s=75, color="#c2413b", zorder=3)
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue (INR)")
    ax.set_title(f"Outlier-Corrected Monthly Revenue - Peak: {peak_month_label}")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "monthly_revenue_trend.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("Saved visualizations/return_rate_by_payment.png")
    print("Saved visualizations/monthly_revenue_trend.png")
    print(f"Corrected revenue peak month: {peak_month} (INR {revenue[peak_index]:,.2f})")


if __name__ == "__main__":
    main()
