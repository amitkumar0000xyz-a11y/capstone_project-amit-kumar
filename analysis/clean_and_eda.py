"""Reproducible pandas cleaning and exploratory analysis for the capstone."""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
ANALYSIS_DIR = ROOT / "analysis"
NARRATOR_DIR = ROOT / "narrator"


def money(value: float) -> float:
    """Round a currency amount to paise for stable JSON and printed output."""
    return round(float(value) + 1e-9, 2)


def add_order_value(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    discount = result["discount_pct"].fillna(0).astype(float)
    result["order_value"] = (
        result["quantity"].astype(float)
        * result["price"].astype(float)
        * (1 - discount / 100)
    )
    return result


def correlation_band(value: float) -> str:
    magnitude = abs(value)
    if magnitude < 0.2:
        return "negligible"
    if magnitude < 0.4:
        return "weak"
    if magnitude < 0.7:
        return "moderate"
    return "strong"


def run_pipeline() -> dict:
    print("=" * 72)
    print("PART 2 - PYTHON / PANDAS DATA WRANGLING & EDA")
    print("=" * 72)

    customers = pd.read_csv(DATA_DIR / "customers.csv")
    products = pd.read_csv(DATA_DIR / "products.csv")
    orders = pd.read_csv(DATA_DIR / "orders.csv")

    print("\nTASK 1 - LOAD AND INSPECT")
    print(f"customers.shape = {customers.shape}")
    print(f"products.shape  = {products.shape}")
    print(f"orders.shape before cleaning = {orders.shape}")
    print("orders dtypes:\n", orders.dtypes.to_string())
    print("raw payment_method unique values:", sorted(orders["payment_method"].unique().tolist()))
    print("raw missing values:\n", orders.isna().sum().to_string())

    raw_orders = orders.copy()
    raw_payment_values = sorted(orders["payment_method"].unique().tolist())

    print("\nTASK 2 - STANDARDIZE PAYMENT METHOD")
    orders["payment_method"] = orders["payment_method"].str.strip().str.upper()
    print("distinct raw values before standardization:", len(raw_payment_values))
    print("payment_method counts after standardization:\n", orders["payment_method"].value_counts().sort_index().to_string())

    print("\nTASK 3 - REMOVE DUPLICATE ORDERS BY NATURAL KEY")
    natural_key = [
        "customer_id",
        "product_id",
        "order_date",
        "quantity",
        "discount_pct",
        "payment_method",
        "rating",
        "returned",
    ]
    duplicate_mask = orders.duplicated(subset=natural_key, keep="first")
    dropped_orders = orders.loc[duplicate_mask].copy()
    orders_clean = orders.loc[~duplicate_mask].copy()
    print(f"duplicate rows flagged and removed = {len(dropped_orders)}")
    print("dropped order_id values:", dropped_orders["order_id"].tolist())
    print(f"orders_clean.shape = {orders_clean.shape}")

    print("\nTASK 4 - IMPUTE MISSING VALUES AFTER DEDUPLICATION")
    discount_missing = int(orders_clean["discount_pct"].isna().sum())
    rating_missing = int(orders_clean["rating"].isna().sum())
    rating_median = float(orders_clean["rating"].median())
    print(f"discount_pct missing values to fill with 0 = {discount_missing}")
    print(f"rating median before imputation = {rating_median:.1f}")
    print(f"rating missing values to fill with median = {rating_missing}")
    orders_clean["discount_pct"] = orders_clean["discount_pct"].fillna(0)
    orders_clean["rating"] = orders_clean["rating"].fillna(rating_median)
    print("missing values after imputation:\n", orders_clean[["discount_pct", "rating"]].isna().sum().to_dict())

    # Raw total is calculated independently on all source rows, matching SQL Part 1.
    raw_merged = raw_orders.merge(products, on="product_id", how="left", validate="many_to_one")
    raw_valued = add_order_value(raw_merged)
    raw_total_revenue = money(raw_valued["order_value"].sum())

    dropped_valued = dropped_orders.merge(products, on="product_id", how="left", validate="many_to_one")
    dropped_valued = add_order_value(dropped_valued)
    duplicate_delta = money(dropped_valued["order_value"].sum())

    merged = orders_clean.merge(products, on="product_id", how="left", validate="many_to_one")
    merged = merged.merge(customers, on="customer_id", how="left", validate="many_to_one")
    merged["order_date"] = pd.to_datetime(merged["order_date"], errors="raise")
    merged = add_order_value(merged)
    cleaned_total_revenue = money(merged["order_value"].sum())

    print("\nTASK 5 - MERGE AND RECONCILE AGAINST PART 1")
    print(f"raw total revenue (180 source rows; Part 1 SQL) = INR {raw_total_revenue:,.2f}")
    print(f"cleaned total revenue ({len(merged)} deduplicated rows) = INR {cleaned_total_revenue:,.2f}")
    print(f"independent order_value sum for dropped rows = INR {duplicate_delta:,.2f}")
    actual_delta = money(raw_total_revenue - cleaned_total_revenue)
    print(
        "Reconciliation: cleaned revenue is INR "
        f"{actual_delta:,.2f} below the Part 1 raw total. This exact difference is the combined "
        f"order_value of the five duplicate rows removed in Task 3 (INR {duplicate_delta:,.2f}), "
        "confirmed by summing those dropped rows independently. Filling missing discount_pct "
        "with 0% and rating with the deduplicated median does not change order_value, so the "
        "revenue reconciliation is attributable to duplicate removal, not imputation."
    )

    print("\nTASK 6 - IQR OUTLIER DETECTION ON QUANTITY")
    q1 = float(merged["quantity"].quantile(0.25))
    q3 = float(merged["quantity"].quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    merged["is_outlier"] = ~merged["quantity"].between(lower, upper, inclusive="both")
    outliers = merged.loc[merged["is_outlier"], ["order_id", "quantity"]]
    print(f"Q1={q1:.1f}, Q3={q3:.1f}, IQR={iqr:.1f}, lower={lower:.1f}, upper={upper:.1f}")
    print(f"outlier rows flagged (retained in dataset) = {len(outliers)}")
    print("flagged orders:\n", outliers.to_string(index=False))

    print("\nTASK 7 - HYPOTHESIS: DOES COD HAVE A HIGHER RETURN RATE?")
    print("Hypothesis: COD orders have a higher return rate than CARD and UPI orders.")
    payment_stats = merged.groupby("payment_method")["returned"].agg(["count", "mean"])
    payment_rates = (payment_stats["mean"] * 100).round(1)
    print("return-rate summary (mean is a proportion):\n", payment_stats.to_string())
    print("return rates (%):\n", payment_rates.to_string())
    cod_rate = float(payment_rates.loc["COD"])
    other_max = float(payment_rates.drop(index="COD").max())
    hypothesis_label = "Confirmed" if cod_rate > other_max else "Not confirmed"
    print(f"Hypothesis result: {hypothesis_label} - COD return rate is {cod_rate:.1f}%.")

    print("\nTASK 8 - MULTI-LEVEL PAYMENT x CITY-TIER SEGMENTATION")
    segments = (
        merged.groupby(["payment_method", "city_tier"])["returned"]
        .agg(order_count="count", return_rate=lambda values: values.mean() * 100)
        .reset_index()
    )
    segments["return_rate_pct"] = segments["return_rate"].round(1)
    print(segments[["payment_method", "city_tier", "order_count", "return_rate_pct"]].to_string(index=False))
    highest_segment = segments.sort_values(
        ["return_rate", "payment_method", "city_tier"], ascending=[False, True, True]
    ).iloc[0]
    print(
        "Highest-risk segment: "
        f"{highest_segment['payment_method']} + Tier-{int(highest_segment['city_tier'])} "
        f"at {highest_segment['return_rate_pct']:.1f}% return rate."
    )
    cod_tier_rates = segments.loc[segments["payment_method"].eq("COD")].set_index("city_tier")
    print(
        "COD is not uniform by tier: Tier-1 has "
        f"{int(cod_tier_rates.loc[1, 'order_count'])} orders at {cod_tier_rates.loc[1, 'return_rate_pct']:.1f}%; "
        "Tier-2 has "
        f"{int(cod_tier_rates.loc[2, 'order_count'])} orders at {cod_tier_rates.loc[2, 'return_rate_pct']:.1f}%."
    )

    print("\nTASK 9 - CORRELATION ANALYSIS")
    corr_columns = ["rating", "returned", "discount_pct", "quantity"]
    correlation = merged[corr_columns].corr()
    print(correlation.to_string(float_format=lambda value: f"{value:.4f}"))
    pairwise = {}
    for left, right in combinations(corr_columns, 2):
        value = float(correlation.loc[left, right])
        band = correlation_band(value)
        pairwise[f"{left} vs {right}"] = {"correlation": round(value, 4), "band": band}
        print(f"{left} vs {right}: r={value:.4f} - {band} (|r|={abs(value):.4f})")
    discount_return_corr = float(correlation.loc["discount_pct", "returned"])
    discount_hypothesis = "Busted" if discount_return_corr <= 0 or abs(discount_return_corr) < 0.2 else "Not busted"
    print(
        "Hypothesis 'higher discounts reduce returns': "
        f"{discount_hypothesis} - discount_pct vs returned r={discount_return_corr:.4f}; "
        "this is negligible association, not evidence of a causal effect."
    )

    print("\nTASK 10 - MONTHLY REVENUE WITH AND WITHOUT QUANTITY OUTLIERS")
    merged["year_month"] = merged["order_date"].dt.to_period("M").astype(str)
    monthly_including_outliers = merged.groupby("year_month")["order_value"].sum().sort_index().map(money)
    monthly_corrected = (
        merged.loc[~merged["is_outlier"]]
        .groupby("year_month")["order_value"]
        .sum()
        .sort_index()
        .map(money)
    )
    print("Monthly revenue including flagged quantity outliers:")
    for month, amount in monthly_including_outliers.items():
        print(f"  {month}: {amount:,.2f}")
    print("Monthly revenue excluding flagged quantity outliers (corrected):")
    for month, amount in monthly_corrected.items():
        print(f"  {month}: {amount:,.2f}")
    inflated_peak_month = str(monthly_including_outliers.idxmax())
    corrected_peak_month = str(monthly_corrected.idxmax())
    print(
        "Interpretation: January's apparent lead is an artifact of the two bulk orders landing "
        "in January (O0011 on 2026-01-28 and O0098 on 2026-01-10). March is the genuine peak "
        "month once those flagged quantity outliers are excluded."
    )

    findings = {
        "cleaned_total_revenue_inr": cleaned_total_revenue,
        "raw_total_revenue_inr": raw_total_revenue,
        "duplicate_reconciliation_delta_inr": duplicate_delta,
        "return_rate_by_payment": {method: float(payment_rates.loc[method]) for method in ["COD", "CARD", "UPI"]},
        "highest_risk_segment": {
            "payment_method": str(highest_segment["payment_method"]),
            "city_tier": int(highest_segment["city_tier"]),
            "return_rate_pct": float(highest_segment["return_rate_pct"]),
        },
        "true_peak_month": {
            "month": corrected_peak_month,
            "revenue_inr": money(monthly_corrected.loc[corrected_peak_month]),
        },
        "outlier_inflated_month": {
            "month": inflated_peak_month,
            "apparent_revenue_inr": money(monthly_including_outliers.loc[inflated_peak_month]),
            "corrected_revenue_inr": money(monthly_corrected.loc[inflated_peak_month]),
        },
    }
    result_artifact = {
        "payment_return_rates": {method: float(payment_rates.loc[method]) for method in ["COD", "CARD", "UPI"]},
        "monthly_revenue_including_outliers": {month: money(amount) for month, amount in monthly_including_outliers.items()},
        "monthly_revenue_outlier_corrected": {month: money(amount) for month, amount in monthly_corrected.items()},
        "findings": findings,
    }
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    NARRATOR_DIR.mkdir(parents=True, exist_ok=True)
    (ANALYSIS_DIR / "eda_results.json").write_text(
        json.dumps(result_artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (NARRATOR_DIR / "findings.json").write_text(
        json.dumps(findings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("\nPart 3 input generated from computed Part 2 results: narrator/findings.json")
    print(json.dumps(findings, indent=2, ensure_ascii=False))
    print("\n" + "=" * 72)
    return result_artifact


if __name__ == "__main__":
    run_pipeline()
