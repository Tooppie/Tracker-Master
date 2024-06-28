from __future__ import annotations

import contextlib
import shutil
import time
from functools import partial
from itertools import chain
from pathlib import Path

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support.ui import WebDriverWait

from net_worth_tracker.utils import combine_balances, euro_per_dollar

from .utils import get_password

FOLDER = Path(__file__).parent.parent / "apeboard_data"
FOLDER.mkdir(parents=True, exist_ok=True)


def wait_for_xpath(xpath, driver, timeout, sleep=1):
    time.sleep(sleep)
    element_present = presence_of_element_located((By.XPATH, xpath))
    WebDriverWait(driver, timeout).until(element_present)
    elements = driver.find_elements(By.XPATH, xpath)
    assert len(elements) == 1
    return elements[0]


def download_from_apeboard(
    url: str | None = None,
    timeout: int = 60,
    headless: bool = True,
):
    if url is None:
        url = get_password("apeboard", "url")

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-dev-shm-usage")
    DesiredCapabilities.CHROME["goog:loggingPrefs"] = {"performance": "ALL"}

    with webdriver.Chrome(
        options=chrome_options, desired_capabilities=DesiredCapabilities.CHROME
    ) as driver:
        # Login
        driver.get(url)

        time.sleep(30)  # Wait for all data to load

        _wait_for_xpath = partial(wait_for_xpath, driver=driver, timeout=timeout)

        export_button = _wait_for_xpath(xpath='//button[text()="Export"]')
        export_button.click()

        download_export_button = _wait_for_xpath("//div/div[2]/button[text()='Export']")
        download_export_button.click()

        selector = _wait_for_xpath("//div[text()='Wallets']")
        selector.click()

        positions_option = _wait_for_xpath("//div/ul/li[text()='Positions']")
        positions_option.click()

        download_export_button = _wait_for_xpath("//div/div[2]/button[text()='Export']")
        download_export_button.click()
        time.sleep(1)

    download_folder = Path("~/Downloads").expanduser()
    for fname in chain(
        download_folder.glob("Export Positions *.csv"),
        download_folder.glob("Export Wallets *.csv"),
    ):
        shutil.move(fname, FOLDER / fname.name)


def load_last_data(split_tri_pool=True, with_price_and_value=False):
    last_positions = sorted(FOLDER.glob("Export Positions *.csv"))[-1]
    last_wallets = sorted(FOLDER.glob("Export Wallets *.csv"))[-1]
    positions = pd.read_csv(last_positions)
    wallets = pd.read_csv(last_wallets)

    # Make into list of single dicts because there can be
    # multiple entries for a single coin
    balances_wallet = [
        {
            row.symbol: {
                "amount": row.balance,
                "price": row.price * euro_per_dollar(),
                "value": row.value * euro_per_dollar(),
            },
        }
        for _, row in wallets.iterrows()
    ]
    balances_wallet = combine_balances(*balances_wallet)

    balances_defi = [
        {
            row.symbol: {
                "amount": row.balance,
                "price": row.price * euro_per_dollar(),
                "value": row.value * euro_per_dollar(),
            },
        }
        for _, row in positions.iterrows()
    ]
    balances_defi = combine_balances(*balances_defi)

    if split_tri_pool:
        with contextlib.suppress(Exception):
            balances_defi = split_out_atricrypto(balances_defi)

    if not with_price_and_value:
        for info in chain(balances_defi.values(), balances_wallet.values()):
            info.pop("price", None)
            info.pop("value", None)

    return balances_wallet, balances_defi


def split_out_atricrypto(balances_defi, name="CRVUSDBTCETH"):
    from net_worth_tracker.coin_gecko import get_prices

    prices = get_prices(dict(BTC=None, ETH=None, USDT=None))

    value_per_part = balances_defi.pop(name)["value"] / 3

    balances = {
        symbol: {
            "amount": value_per_part / prices[symbol],
            "price": prices[symbol],
            "value": value_per_part,
        }
        for symbol in ("BTC", "ETH", "USDT")
    }

    return combine_balances(balances, balances_defi)
