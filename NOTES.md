# What I checked, and what the agent got wrong

## What the agent got wrong

The biggest thing I caught was the `MILES_PER_KM` constant in `fleet_utils.py`. The original
value was `1.609`, and the agent initially left a comment saying "is that right?" without
flagging it as a bug. When I looked at `verify.py` I noticed the acceptance check requires
`km_to_miles(100)` to return between 61.0 and 63.5 — but `100 * 1.609 = 160.9`, which is
wildly wrong. The constant had the conversion direction backwards: 1.609 is how many
kilometres are in a mile, not the other way round. The correct factor is 0.621371. I
confirmed this before accepting the fix by checking that `km_to_miles(100)` now returns 62.1.

The second thing I checked carefully was the `analyze.py` risk model. The agent correctly
computed the correlations and flagged that odometer and age are flat, but I verified the
weight arithmetic manually: the three raw correlations (0.404 + 0.252 + 0.215 = 0.871) are
used as proportional weights, so the score is a weighted average of three min-max normalised
columns, not an arbitrary formula. I also checked the validation line at the bottom — broken-
down cars average 61.6 and intact cars average 41.4, which confirms the score discriminates.

## What I checked before I accepted the work

**Wear bug:** I ran `python verify.py` and confirmed the check "Wear is no longer floored to 0"
reports `99.3%` (was `0%` before). I also read the fixed line in `km_wachter.py` directly —
`(km_since_service / interval) * 100` — and confirmed it uses true division, not `//`.

**80% rule untouched:** `verify.py` prints `interval=15000, threshold=80 (both must be
untouched)` for both the in-code constants and the `settings.cfg` values. I read both files
to confirm neither constant was changed.

**Missing-reading fix:** I checked that `needs_service` returns `False` immediately when
`last_service_km` is absent, rather than defaulting to 0. The old default of 0 meant a car
at 92,000 km odometer was treated as 92,000 km into its service window and wrongly flagged.

**km-to-miles conversion:** I manually computed `100 * 0.621371 = 62.1` and matched it
against the `verify.py` range of 61.0–63.5. Pass confirmed.

**Test count:** I ran `pytest -v` and saw all 4 tests green, including the new
`test_summary_does_not_crash_on_missing_reading` that was explicitly called out as a TODO.

## What the data actually said

The obvious assumption — that older, higher-mileage cars break down — is not what the data
shows. The Pearson correlation of total odometer with `broke_down` is **+0.002**, and for
age it is **-0.001**. Both groups have virtually the same mean odometer (53,302 vs 53,448 km)
and the same mean age (5.89 vs 5.88 years). These columns are useless as predictors.

What actually separates the cars that broke down from those that did not:

1. **`km_since_service` (r = 0.40)** — the strongest signal by a wide margin. Cars that
   broke down had driven an average of 11,678 km since their last service; cars that did not
   averaged only 7,261 km. This makes physical sense: the further into a service window, the
   more wear has accumulated without a check.

2. **`avg_daily_km` (r = 0.25)** — daily usage intensity. Broken-down cars were driven harder
   on average (160 km/day vs 131 km/day). High daily usage accelerates wear between services.

3. **`load_factor` (r = 0.22)** — drive-cycle severity. Broken-down cars had a higher mean
   load factor (0.60 vs 0.51), meaning more demanding duty cycles.

The risk score weights these three columns in proportion to their correlations and scores each
car 0–100. The validation confirms it works: mean risk score for cars that later broke down
is 61.6, versus 41.4 for cars that did not. The top 20 ranked cars include 15 of the 26
actual breakdowns — far better than random chance.

The practical implication for the fleet team: do not wait for total mileage milestones. Flag
cars that are deep into their current service window AND being driven hard or heavily loaded,
even if the car is brand-new and low on total odometer.
