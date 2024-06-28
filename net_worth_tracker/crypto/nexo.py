import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.expected_conditions import text_to_be_present_in_element
from selenium.webdriver.support.ui import WebDriverWait

from .utils import fname_from_date, get_password

RENAMES = {"NEXOBEP2": "NEXO", "NEXONEXO": "NEXO"}

FOLDER = Path(__file__).parent.parent / "nexo_data"
FOLDER.mkdir(parents=True, exist_ok=True)


def scrape_nexo_csv(
    username: Optional[str] = None,
    password: Optional[str] = None,
    timeout=30,
    download_transactions_csv: bool = False,
):
    if username is None:
        username = get_password("username", "nexo")
    if password is None:
        password = get_password(username, "nexo")

    chrome_options = Options()
    DesiredCapabilities.CHROME["goog:loggingPrefs"] = {"performance": "ALL"}

    with webdriver.Chrome(
        options=chrome_options, desired_capabilities=DesiredCapabilities.CHROME
    ) as driver:
        # Login
        driver.get("https://platform.nexo.io/")
        element_present = text_to_be_present_in_element(
            (By.CLASS_NAME, "Modal.FormLogin"), "Login"
        )
        WebDriverWait(driver, timeout).until(element_present)

        username_bar, password_bar = driver.find_elements_by_tag_name("input")
        username_bar.send_keys(username)
        password_bar.send_keys(password)

        continue_button = next(
            b for b in driver.find_elements_by_tag_name("button") if "Login" in b.text
        )
        continue_button.click()

        # Manually add 2FA and login!

        # Wait until page is loaded
        element_present = text_to_be_present_in_element(
            (By.TAG_NAME, "nav"), "Transactions"
        )
        wait = WebDriverWait(driver, 60)
        wait.until(element_present)
        if download_transactions_csv:
            # Note: one cannot correctly get the balances from the csv
            # file after an exchange on Nexo.
            transactions_button = next(
                s
                for s in driver.find_elements_by_tag_name("span")
                if "Transaction" in s.text
            )
            transactions_button.click()

            element_present = text_to_be_present_in_element(
                (By.CLASS_NAME, "text"), "Export"
            )
            wait = WebDriverWait(driver, 5)
            wait.until(element_present)

            export_button = next(
                b
                for b in driver.find_elements_by_tag_name("button")
                if "Export" in b.text
            )
            fname = Path("~/Downloads/nexo_transactions.csv").expanduser()
            if fname.exists():
                fname.unlink()
            export_button.click()
            for _ in range(10):
                time.sleep(1)
                if fname.exists():
                    print(f"Downloaded {fname}")
                    return
            print("Didn't download the file")
        else:
            # Get items from Network tab
            events = [
                json.loads(entry["message"])["message"]
                for entry in driver.get_log("performance")
            ]

            # Select relevant event
            event = next(
                event
                for event in events
                if "https://platform.nexo.io/api/1/get_balances" in str(event)
            )
            # Request the content of event
            response = driver.execute_cdp_cmd(
                "Network.getResponseBody", {"requestId": event["params"]["requestId"]}
            )
            result = json.loads(response["body"])["payload"]
            with fname_from_date(FOLDER).open("w") as f:
                json.dump(result, f, indent="  ")


def load_latest_data(folder=FOLDER):
    last_file = sorted(folder.glob("*.json"))[-1]
    with last_file.open("r") as f:
        return json.load(f)


@lru_cache
def get_nexo_balances(folder=FOLDER):
    data = load_latest_data(folder)
    return {
        RENAMES.get(d["short_name"], d["short_name"]): {"amount": d["total_balance"]}
        for d in data["balances"]
        if d["total_balance"] > 0
    }


@lru_cache
def get_nexo_balances_from_csv(
    csv_fname: str = "~/Downloads/nexo_transactions.csv",
):
    print("Download csv from https://platform.nexo.io/transactions")
    df = pd.read_csv(csv_fname)

    def fix_amount(x):
        try:
            return float(x)
        except ValueError:
            a, b = x.split("/")
            return float(a) + float(b)

    df["Amount"] = df["Amount"].apply(fix_amount)

    summed = df[df.Type == "Deposit"].groupby("Currency").sum("Amount").to_dict()
    withdraw = df[df.Type == "Withdrawal"].groupby("Currency").sum("Amount").to_dict()
    for k, v in withdraw["Amount"].items():
        summed["Amount"][k] += v
    total = pd.DataFrame(summed)
    balances = {i: row.Amount for i, row in total.iterrows()}
    for old, new in RENAMES.items():
        if old in balances:
            balances[new] = balances.pop(old)
    nexo = df[df.Type == "Interest"].groupby("Currency").sum("Amount")
    assert len(nexo) == 1
    balances["NEXO"] = balances.get("NEXO", 0) + nexo.iloc[0].Amount
    return {k: dict(amount=v) for k, v in balances.items()}


if __name__ == "__main__":
    scrape_nexo_csv()
