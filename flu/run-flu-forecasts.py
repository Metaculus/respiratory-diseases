# https://www.metaculus.com/questions/29507/us-weekly-influenza-hospitalizations-24-25/

# The Challenge Period will begin November 20, 2024, and will run until May 31, 2025. Participants are asked to submit weekly nowcasts and forecasts by 11PM Eastern Time each Wednesday (herein referred to as the Forecast Due Date).

import requests
from datetime import datetime, timedelta
import pandas as pd
from utils import internal_to_actual
import numpy as np

question_id = 29507
url = f"https://metaculus.com/api/posts/{question_id}"
response = requests.get(url).json()

# get reference date, which is the saturday following the submission due date
today = datetime.now().date()  # this is the submission due date, a Tuesday
days_until_saturday = (5 - today.weekday()) % 7  # 5 is Saturday
reference_date = today + timedelta(days=days_until_saturday)

forecasts = []

subquestions = response["group_of_questions"]["questions"]
for subquestion in subquestions:
    # obtain the target end date
    question_title = subquestion["title"]
    target_end_date = question_title.split("(")[1].split(")")[0].strip()
    target_end_date = datetime.strptime(target_end_date, "%B %d, %Y").date()

    # calculate horizon based on target_end_date and reference_date
    # target_end_date should be equal to the reference_date + horizon*(7 days).
    horizon = (target_end_date - reference_date).days // 7

    # # only deal with forecast, if horizon is -1, 0, 1, 2, 3
    if horizon not in [-1, 0, 1, 2, 3]:
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

    # need a dataframe with the quantiles and the quantile levels
    latest_forecast_df = pd.DataFrame(
        {
            "reference_date": reference_date,
            "target": "wk inc flu hosp",
            "horizon": horizon,
            "target_end_date": target_end_date,
            "location": "US",
            "output_type": "quantile",
            "output_type_id": desired_quantile_levels,
            "value": desired_quantiles,
        }
    )
    forecasts.append(latest_forecast_df)

forecasts_df = pd.concat(forecasts)
forecasts_df.to_csv(
    f"2024-25/flu/metac-cp/{reference_date}-metaculus-cp.csv", index=False
)
