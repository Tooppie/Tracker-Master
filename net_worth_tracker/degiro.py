import getpass
import json
from collections import defaultdict
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Optional

import requests
import yfinance as yf

from .utils import fname_from_date, get_password

FOLDER = Path(__file__).parent.parent / "degiro_data"


class DeGiro:
    def __init__(self) -> None:
        self.session = None
        self.session_id = None

    def login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        with_2fa: bool = False,
    ):

        if username is None:
            username = get_password("username", "degiro")
        if password is None:
            password = get_password(username, "degiro")

        self.session = requests.Session()

        # Login
        url = "https://trader.degiro.nl/login/secure/login"
        payload = {
            "username": username,
            "password": password,
            "isPassCodeReset": False,
            "isRedirectToMobile": False,
        }
        header = {"content-type": "application/json"}

        if with_2fa:
            payload["oneTimePassword"] = getpass.getpass("DEGIRO 2FA Token: ")
            url += "/totp"

        r = self.session.post(url, headers=header, data=json.dumps(payload))

        # Get session id
        self.session_id = r.headers["Set-Cookie"].split(";")[0].split("=")[1]
        return self

    @cached_property
    def int_account(self):
        """This contain loads of user data, main interest here is the 'intAccount'."""
        url = "https://trader.degiro.nl/pa/secure/client"
        payload = {"sessionId": self.session_id}
        data = self.session.get(url, params=payload).json()
        return data["data"]["intAccount"]

    @cached_property
    def data(self):
        """This gets a lot of data, orders, news, portfolio, cash funds etc."""
        url = "https://trader.degiro.nl/trading/secure/v5/update/"
        url += f"{self.int_account};jsessionid={self.session_id}"
        payload = {
            "portfolio": 0,
            "totalPortfolio": 0,
            "orders": 0,
            "historicalOrders": 0,
            "transactions": 0,
            "alerts": 0,
            "cashFunds": 0,
            "intAccount": self.int_account,
            "sessionId": self.session_id,
        }

        r = self.session.get(url, params=payload)

        return r.json()

    def get_cash_funds(self):
        """Get the cash funds."""
        cash_funds = {}
        for cf in self.data["cashFunds"]["value"]:
            entry = {}
            for y in cf["value"]:
                # Useful if the currency code is the key to the dict
                if y["name"] == "currencyCode":
                    key = y["value"]
                    continue
                entry[y["name"]] = y["value"]
            cash_funds[key] = entry
        return cash_funds

    def get_portfolio_summary(self):
        """Only returns a summary of the portfolio."""
        pf = self.get_portfolio()
        cf = self.get_cash_funds()
        return {
            "equity": sum(d["value"] for d in pf["PRODUCT"].values()),
            "cash": cf["EUR"]["value"],
        }

    @lru_cache
    def get_portfolio(self):
        """Returns the entire portfolio."""
        portfolio = []
        for row in self.data["portfolio"]["value"]:
            entry = {}
            for y in row["value"]:
                k = y["name"]
                v = None
                if "value" in y:
                    v = y["value"]
                entry[k] = v
            # Also historic equities are returned, let's omit them
            if entry["size"] != 0:
                portfolio.append(entry)

        # Restructure portfolio and add extra data
        portf_n = defaultdict(dict)
        # Restructuring
        for r in portfolio:
            pos_type = r["positionType"]
            pid = r["id"]  # Product ID
            del r["positionType"]
            del r["id"]
            portf_n[pos_type][pid] = r

        # Adding extra data
        url = "https://trader.degiro.nl/product_search/secure/v5/products/info"
        params = {"intAccount": str(self.int_account), "sessionId": self.session_id}
        header = {"content-type": "application/json"}
        pid_list = list(portf_n["PRODUCT"].keys())
        r = self.session.post(
            url, headers=header, params=params, data=json.dumps(pid_list)
        )

        for k, v in r.json()["data"].items():
            del v["id"]
            # Some bonds tend to have a non-unit size
            portf_n["PRODUCT"][k]["size"] *= v["contractSize"]
            portf_n["PRODUCT"][k].update(v)

        return dict(portf_n)

    def get_holdings(self):
        holdings = {}
        portfolio = self.get_portfolio()
        for v in portfolio["PRODUCT"].values():
            holdings[v["symbol"]] = {
                k: v[k] for k in ["size", "price", "value", "name"]
            }
        cash = portfolio["CASH"]
        eur_value = cash.get("EUR", {}).get("value", 0) + cash.get(
            "FLATEX_EUR", {}
        ).get("value", 0)
        holdings["EUR"] = dict(size=eur_value, value=eur_value, price=1, name="Euro")
        return holdings


def load_latest_data(folder=FOLDER):
    last_file = sorted(folder.glob("*.json"))[-1]
    with last_file.open("r") as f:
        return json.load(f)


def get_latest_prices(tickers):
    price = {}
    for ticker in tickers:
        if ticker == "EUR":
            price[ticker] = 1
            continue
        for ext in [".AS", ".DE", ""]:
            # Try AMS exchange, then German, then anything.
            t = yf.Ticker(ticker + ext)
            if t.info.get("regularMarketPrice") is not None:
                assert t.info["currency"] == "EUR"
                price[ticker] = t.info["regularMarketPrice"]
                break
    return price


@lru_cache
def get_degiro_balances(folder=FOLDER):
    data = load_latest_data(folder)
    prices = get_latest_prices(data)
    return {
        t: dict(amount=info["size"], value=info["size"] * prices[t], price=prices[t])
        for t, info in data.items()
    }


def update_data(
    username: Optional[str] = None, password: Optional[str] = None, with_2fa=True
):
    dg = DeGiro().login(username, password, with_2fa=with_2fa)
    holdings = dg.get_holdings()
    print(holdings)
    with fname_from_date(FOLDER).open("w") as f:
        json.dump(holdings, f, indent="  ")


if __name__ == "__main__":
    update_data()
