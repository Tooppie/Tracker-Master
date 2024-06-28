import yaml

from net_worth_tracker import degiro


def load(fname="manual.yaml"):
    with open(fname) as f:
        manual = yaml.safe_load(f)
    prices = degiro.get_latest_prices(manual["stock_manual"].keys())
    for ticker, price in prices.items():
        d = manual["stock_manual"][ticker]
        d["price"] = price
        d["value"] = price * d["amount"]
    return manual
