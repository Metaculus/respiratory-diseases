# https://www.metaculus.com/questions/30048/us-rsv-hospitalization-forecasts-2024-25/
# submissions:
# - output file: YYYY-MM-DD-team-model.parquet
# - team = abbreviated team name (metac)
# horizons = 1, 2, 3, 4
# - time: weekly forecasts by 11:59 PM Eastern Time each Tuesday.

import requests
from datetime import datetime, timedelta
import pandas as pd
from utils import internal_to_actual
import numpy as np

question_id = 30048
url = f"https://metaculus.com/api/posts/{question_id}"
response = requests.get(url).json()

# origin date is the first date of the week for that week's forecast (i.e. the Sunday before the submission due date).
today = datetime.now().date()  # this is the submission due date, a Tuesday
days_until_sunday = (6 - today.weekday()) % 7  # 6 is Sunday
origin_date = today + timedelta(days=days_until_sunday) - timedelta(days=7)

forecasts = []

subquestions = response["group_of_questions"]["questions"]
for subquestion in subquestions:
    question_title = subquestion["title"]
    target_end_date = question_title.split("(")[1].split(")")[0].strip()
    target_end_date = datetime.strptime(target_end_date, "%B %d, %Y").date()

    # origin_date is always a Sunday, target_end_date is always a Saturday
    horizon = ((target_end_date - origin_date).days + 1) // 7

    if horizon not in [0, 1, 2, 3, 4, 5]:
        continue

    # obtain the scaling of the x-axis
    range_max = subquestion["scaling"]["range_max"]
    range_min = subquestion["scaling"]["range_min"]
    zero_point = subquestion["scaling"]["zero_point"]

    try:
        cdf = subquestion["aggregations"]["recency_weighted"]["latest"][
            "forecast_values"
        ]
    except TypeError:
        print(f"No forecast for {question_title}")
        continue

    internal_x_grid = np.linspace(0, 1, 201)
    actual_x_grid = internal_to_actual(
        internal_x_grid, zero_point, range_min, range_max, is_linear=False
    )

    desired_quantile_levels = np.concatenate(
        [[0.01, 0.025], np.arange(0.05, 0.95 + 0.05, 0.05), [0.975, 0.99]]
    ).round(3)
    desired_quantiles = np.interp(desired_quantile_levels, cdf, actual_x_grid)

    latest_forecast_df = pd.DataFrame(
        {
            "horizon": horizon,
            "target_end_date": target_end_date,
            "output_type_id": desired_quantile_levels,
            "value": desired_quantiles,
        }
    )
    forecasts.append(latest_forecast_df)

forecasts_df = pd.concat(forecasts)

full_horizons = list(range(1, 5))  # NNEDS TO BE 1
full_target_end_dates = [origin_date + timedelta(days=7 * h - 1) for h in full_horizons]

full_forecast_df = pd.DataFrame(
    {
        "horizon": full_horizons,
        "target_end_date": full_target_end_dates,
        "origin_date": origin_date,
        "target": "inc hosp",
        "location": "US",
        "output_type": "quantile",
        "age_group": "0-130",
    }
)
full_forecast_df = full_forecast_df.merge(
    pd.DataFrame({"output_type_id": desired_quantile_levels}), how="cross"
)

forecasts_df_full = full_forecast_df.merge(
    forecasts_df, on=["horizon", "target_end_date", "output_type_id"], how="left"
)

# sort according to quantile levels, then horizons
forecasts_df_full = forecasts_df_full.sort_values(by=["output_type_id", "horizon"])

forecasts_df_full["value"] = forecasts_df_full.groupby("output_type_id")[
    "value"
].transform(lambda x: x.interpolate(method="linear", fill_value="extrapolate"))

forecasts_df_full = forecasts_df_full.sort_values(by=["horizon", "output_type_id"])

forecasts_df_full = forecasts_df_full[
    [
        "origin_date",
        "horizon",
        "target",
        "target_end_date",
        "location",
        "output_type",
        "output_type_id",
        "value",
        "age_group",
    ]
]

forecasts_df_full.to_csv(f"rsv/submissions/{origin_date}-Metaculus-cp.csv", index=False)
