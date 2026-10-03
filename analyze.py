# analyze.py
# Risk-factor analysis for Vossberg Mobility fleet breakdown prediction.
#
# KEY FINDING: Total odometer mileage and car age do NOT separate cars that broke down
# from those that did not — their group means are virtually identical (53 302 vs 53 448 km;
# 5.89 vs 5.88 years). The factors that actually predict breakdown are km_since_service
# (how far the car is into its current service window, r=0.40), avg_daily_km (daily usage
# intensity, r=0.25), and load_factor (drive-cycle severity, r=0.22). A car that is deep
# into its service window AND driven hard daily is the real risk profile — not an old car.

import pandas as pd

# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------
df = pd.read_csv("fleet_history.csv")

# ---------------------------------------------------------------------------
# 2. Compare group means to see which columns separate the two outcomes
# ---------------------------------------------------------------------------
features = ["odometer_km", "km_since_service", "avg_daily_km", "load_factor", "age_years"]
group_means = df.groupby("broke_down")[features].mean().round(2)
correlations = df[features + ["broke_down"]].corr()["broke_down"].drop("broke_down").round(3)

print("=" * 60)
print("GROUP MEANS  (0 = no breakdown, 1 = broke down)")
print("=" * 60)
print(group_means.to_string())
print()
print("=" * 60)
print("PEARSON CORRELATION WITH BROKE_DOWN")
print("=" * 60)
for feat, corr in correlations.sort_values(ascending=False).items():
    marker = " <-- signal" if abs(corr) >= 0.20 else " <-- flat (not useful)"
    print(f"  {feat:<22} {corr:+.3f}{marker}")

print()
print("CONCLUSION:")
print("  odometer_km  : means 53302 vs 53448 — identical. Total mileage does NOT predict breakdown.")
print("  age_years    : means 5.89  vs 5.88  — identical. Car age does NOT predict breakdown.")
print("  km_since_service, avg_daily_km, load_factor DO separate the groups and are used below.")

# ---------------------------------------------------------------------------
# 3. Build a 0–100 risk score from the three predictive columns only.
#    Each column is min–max normalised to [0, 1], then combined with weights
#    proportional to their absolute correlations with broke_down.
#    Weight shares: km_since_service 0.404 / 0.871 ≈ 46%
#                   avg_daily_km     0.252 / 0.871 ≈ 29%
#                   load_factor      0.215 / 0.871 ≈ 25%
# ---------------------------------------------------------------------------
def minmax(series: pd.Series) -> pd.Series:
    """Scale a series to the [0, 1] range."""
    lo, hi = series.min(), series.max()
    return (series - lo) / (hi - lo) if hi > lo else pd.Series(0.0, index=series.index)


W_KSS  = 0.404   # km_since_service weight (raw correlation magnitude)
W_ADK  = 0.252   # avg_daily_km weight
W_LF   = 0.215   # load_factor weight
W_TOTAL = W_KSS + W_ADK + W_LF

df["_n_kss"] = minmax(df["km_since_service"])
df["_n_adk"] = minmax(df["avg_daily_km"])
df["_n_lf"]  = minmax(df["load_factor"])

df["risk_score"] = (
    (W_KSS * df["_n_kss"] + W_ADK * df["_n_adk"] + W_LF * df["_n_lf"]) / W_TOTAL * 100
).round(1)

# ---------------------------------------------------------------------------
# 4. Print cars ranked by risk, highest first
# ---------------------------------------------------------------------------
ranked = (
    df[["car_id", "km_since_service", "avg_daily_km", "load_factor", "risk_score", "broke_down"]]
    .sort_values("risk_score", ascending=False)
    .reset_index(drop=True)
)
ranked.index += 1   # 1-based rank

print()
print("=" * 60)
print("FLEET RISK RANKING  (highest risk first)")
print("=" * 60)
print(f"{'Rank':<5} {'Car ID':<12} {'km_since_svc':>13} {'avg_daily_km':>13} {'load':>6} {'risk':>6} {'broke':>6}")
print("-" * 65)
for rank, row in ranked.iterrows():
    broke = "*" if row["broke_down"] == 1 else ""
    print(
        f"{rank:<5} {row['car_id']:<12} {int(row['km_since_service']):>13,} "
        f"{int(row['avg_daily_km']):>13,} {row['load_factor']:>6.2f} "
        f"{row['risk_score']:>6.1f} {broke:>6}"
    )

print()
print("  * = car that later broke down")
print(f"  Total cars: {len(df)}  |  Breakdowns: {df['broke_down'].sum()}  ({df['broke_down'].mean()*100:.1f}%)")

# Validate: broken-down cars should score higher on average
mean_risk_broken  = df.loc[df["broke_down"] == 1, "risk_score"].mean()
mean_risk_ok      = df.loc[df["broke_down"] == 0, "risk_score"].mean()
print(f"  Mean risk score — broke down: {mean_risk_broken:.1f}  |  did not: {mean_risk_ok:.1f}")
