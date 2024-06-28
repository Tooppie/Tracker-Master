import matplotlib
import matplotlib.pyplot as plt
import numpy as np


def plot_pie_at_date(df, date, min_euro=1, show=True, fname=None, fig=None, ax=None):
    if fig is None:
        fig, ax = plt.subplots(figsize=(15, 15))
    else:
        ax.clear()
    df = df[df.value > min_euro]
    last = (
        df[df.date == date]
        .set_index("symbol")
        .value.dropna()
        .sort_values(ascending=False)
    )

    coins = sorted(df.symbol.unique())
    color_map = dict(
        zip(coins, matplotlib.cm.get_cmap("tab20c")(np.linspace(0, 1, len(coins))))
    )
    colors = [color_map[coin] for coin in last.index]

    patches, texts, _ = ax.pie(
        last, labels=last.index, colors=colors, autopct="%1.1f%%"
    )
    factor = 100 / last.sum()
    legend_labels = [
        f"{coin} - {factor*amount:1.2f}% - €{amount:.2f}"
        for coin, amount in last.items()
    ]

    ax.axis("equal")
    ax.legend(
        patches,
        legend_labels,
        loc="upper left",
        bbox_to_anchor=(-0.25, 1.0),
        fontsize=12,
    )
    ax.set_title(str(date))
    if fname is not None:
        plt.savefig(fname)
    if show:
        plt.show()


def plot_barh_at_date(df, date, min_euro=10, show=True, fname=None, fig=None, ax=None):
    if fig is None:
        fig, ax = plt.subplots(figsize=(15, 15))
    else:
        ax.clear()
    to_drop = df.value < min_euro
    # dropped = df[to_drop].value.sum()

    last = (
        df[(~to_drop) & (df.date == date)]
        .set_index("symbol")
        .value.dropna()
        .sort_values(ascending=True)
    )

    coins = sorted(df.symbol.unique())
    coins.append("others")
    color_map = dict(
        zip(coins, matplotlib.cm.get_cmap("tab20c")(np.linspace(0, 1, len(coins))))
    )
    colors = [color_map[coin] for coin in last.index]

    bars = ax.barh(last.index, last, color=colors)

    factor = 100 / last.sum()
    labels = [
        f"{coin} - €{amount:.2f} ({factor*amount:1.2f}%)"
        for coin, amount in last.items()
    ]

    for label, bar in zip(labels, bars):
        width = bar.get_width()
        ax.text(
            width * 1.01,
            bar.get_y() + bar.get_height() / 2,
            f"{label}",
            ha="left",
            va="center",
        )

    ax.set_title(f"Value at {date}")
    ax.set_axis_off()
    ax.set_xlim(0, 1.2 * df.value.max())

    if fname is not None:
        plt.savefig(fname)
    if show:
        plt.show()


def plot_barh_at_date_with_profits(
    df, date, min_euro=10, show=True, fname=None, fig=None, ax=None
):
    if fig is None:
        fig, ax = plt.subplots(figsize=(15, 15))
    else:
        ax.clear()
    to_drop = df.value < min_euro

    sel = (
        df[(~to_drop) & (df.date == date)]
        .set_index("symbol")
        .sort_values(ascending=True, by="value")
    )
    value = sel.value
    profits = sel.amount * (sel.price - sel.avg_price)
    colors = ["r" if p < 0 else "g" for p in profits]

    bars = ax.barh(value.index, value, color="grey")
    _ = ax.barh(profits.index, profits.abs(), color=colors, alpha=0.2, hatch="//")

    factor = 100 / value.sum()
    labels = [
        f"{coin} - €{amount:.2f} ({factor*amount:1.2f}%)"
        for coin, amount in value.items()
    ]

    for label, bar in zip(labels, bars):
        width = bar.get_width()
        ax.text(
            width * 1.01,
            bar.get_y() + bar.get_height() / 2,
            f"{label}",
            ha="left",
            va="center",
        )

    ax.set_title(f"Value at {date}")
    ax.set_axis_off()
    ax.set_xlim(0, 1.2 * df.value.max())

    if fname is not None:
        plt.savefig(fname)
    if show:
        plt.show()
