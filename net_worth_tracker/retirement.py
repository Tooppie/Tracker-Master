from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


@dataclass
class Snapshot:
    date: datetime
    n_months: int
    n_years: int
    net_worth: float
    net_worth_inflation_corrected: float
    save_per_month: float
    monthly_spending: float
    investment_income: float
    fire: bool
    age: float | None = None


def compound(
    average_saving_daily: float,
    monthly_spending: float,
    continue_n_years_after_retirement: int | None = 10,
    n_months: int | None = None,
    date_of_birth: int | None = None,
    yearly_pct_raise: int = 5,
    percent_rule: int = 4,
    inflation: float = 2,
    start_with: int = 200_000,
    interest_per_year: int = 7,
) -> list[Snapshot]:
    if n_months is None and continue_n_years_after_retirement is None:
        raise ValueError(
            "Must provide either n_months or continue_n_years_after_retirement"
        )
    pct_per_month = interest_per_year / 12
    save_per_month = average_saving_daily * 365.25 / 12

    lst = []
    total = start_with
    months_fire = 0
    date = datetime.now()
    for i in range(12 * 200):
        date += timedelta(days=365.25 / 12)
        if i % 12 == 0:
            save_per_month *= 1 + yearly_pct_raise / 100
        monthly_spending *= (1 + (inflation / 100)) ** (1 / 12)
        total = total * (1 + pct_per_month / 100) + save_per_month
        net_worth_inflation_corrected = total * (1 - inflation / 100) ** (i / 12)
        investment_income = total * (percent_rule / 100) / 12
        financially_free = investment_income > monthly_spending
        age = (date - date_of_birth).days / 365 if date_of_birth else None
        ss = Snapshot(
            date=date,
            n_months=i,
            n_years=i / 12,
            net_worth=total,
            net_worth_inflation_corrected=net_worth_inflation_corrected,
            save_per_month=save_per_month,
            monthly_spending=monthly_spending,
            investment_income=investment_income,
            fire=financially_free,
            age=age,
        )
        lst.append(ss)
        if financially_free:
            months_fire += 1
        if n_months is not None and i > n_months:
            break
        if (
            continue_n_years_after_retirement is not None
            and months_fire > 12 * continue_n_years_after_retirement
        ):
            break
    return lst


def cost_in_early_retirement(
    extra: float | int,
    average_saving_daily: float,
    monthly_spending: float,
    n_months: int | None = None,
    extra_key: str = "start_with",
    date_of_birth: int | None = None,
    yearly_pct_raise: int = 5,
    percent_rule: int = 4,
    inflation: float = 2,
    start_with: int = 200_000,
    interest_per_year: int = 7,
    verbose: bool = False,
) -> float:
    defaults = dict(
        average_saving_daily=average_saving_daily,
        monthly_spending=monthly_spending,
        n_months=n_months,
        date_of_birth=date_of_birth,
        yearly_pct_raise=yearly_pct_raise,
        percent_rule=percent_rule,
        inflation=inflation,
        start_with=start_with,
        interest_per_year=interest_per_year,
        continue_n_years_after_retirement=0,
    )
    case_1 = compound(**defaults)
    kw = defaults.copy()
    kw[extra_key] += extra
    case_2 = compound(**kw)
    n_years = case_1[-1].n_years - case_2[-1].n_years
    if verbose:
        print(f"Extra {extra} will last {n_years} years or {n_years * 12} months")
    return n_years


def plot_net_worth(df_future: pd.DataFrame) -> go.Figure:
    fire_date = df_future[df_future.fire].iloc[0]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=df_future.age, y=df_future.net_worth, name="Net worth"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df_future.age, y=df_future.monthly_spending, name="Monthly spending"
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title_text="Net worth and monthly spending",
    )
    fig.update_xaxes(title_text="Age")
    fig.update_yaxes(title_text="<b>A</b> Net worth", secondary_y=False)
    fig.update_yaxes(title_text="<b>B</b> Monthly spending", secondary_y=True)
    fig.add_hline(y=fire_date.net_worth, line_dash="dash")
    fig.add_vrect(
        x0=fire_date.age,
        x1=df_future.age.max(),
        line_width=0,
        fillcolor="green",
        opacity=0.2,
    )
    return fig


def plot_cost_in_early_retirement(**kwargs):
    # Difference in cost of early retirement
    sims = [
        {
            "amount": amount,
            "n_months": 12 * cost_in_early_retirement(extra=amount, **kwargs),
        }
        for amount in range(-50_000, 50_000, 5_000)
    ]
    sims = pd.DataFrame(sims)
    fig = px.line(sims, x="amount", y="n_months")
    fig.update_layout(
        title_text="Difference in time of early retirement",
    )
    fig.update_xaxes(title_text="Amount spent in $")
    fig.update_yaxes(title_text="Months earlier/later")
    return fig
