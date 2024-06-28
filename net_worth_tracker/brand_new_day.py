from functools import lru_cache
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located,
    text_to_be_present_in_element,
)
from selenium.webdriver.support.ui import WebDriverWait

from .utils import get_password


@lru_cache
def scrape_brand_new_day(
    username: Optional[str] = None,
    password: Optional[str] = None,
    timeout=30,
    headless=True,
):
    if username is None:
        username = get_password("username", "brandnewday")
    if password is None:
        password = get_password(username, "brandnewday")
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    if headless:
        chrome_options.add_argument("--headless")

    with webdriver.Chrome(options=chrome_options) as driver:
        # Login
        driver.get("https://secure.brandnewday.nl/mijn-gegevens/inloggen")
        username_bar = driver.find_element(By.NAME, "username")
        password_bar = driver.find_element(By.NAME, "password")
        username_bar.send_keys(username)
        password_bar.send_keys(password)

        login_button = next(
            b for b in driver.find_elements(By.NAME, "button") if "Inloggen" in b.text
        )
        login_button.click()

        # Select "Pensioenrekening"
        element_present = text_to_be_present_in_element(
            (By.CLASS_NAME, "accountsTable"), "Pensioenrekening"
        )
        WebDriverWait(driver, timeout).until(element_present)

        accounts_table = driver.find_element(By.CLASS_NAME, "accountsTable")

        pensioen_rekening = next(
            row
            for row in accounts_table.find_elements(By.CLASS_NAME, "accountsTableRow")
            if "Pensioenrekening-beleggen" in row.text
        )

        pensioen_rekening.find_element(By.CLASS_NAME, "goToButton").click()

        # Go to "Fondsen & geld" submenu
        element_present = presence_of_element_located((By.CLASS_NAME, "submenu"))
        WebDriverWait(driver, timeout).until(element_present)

        menu = driver.find_element(By.CLASS_NAME, "submenu")

        fondsen_en_geld_button = next(
            li
            for li in menu.find_elements(By.TAG_NAME, "li")
            if "Fondsen & geld" in li.text
        )
        fondsen_en_geld_button.click()

        # Extract information from table
        element_present = text_to_be_present_in_element(
            (By.ID, "fundsMoney"), "BND Wereld Indexfonds"
        )
        WebDriverWait(driver, timeout).until(element_present)

        table = driver.find_element(By.ID, "fundsMoney")
        header = table.find_element(By.TAG_NAME, "thead")
        headers = [th.text for th in header.find_elements(By.TAG_NAME, "th")]
        trs = table.find_elements(By.TAG_NAME, "tr")
        rows = []
        for tr in trs:
            values = [td.text for td in tr.find_elements(By.TAG_NAME, "td")]
            row = dict(zip(headers, values))
            if row.get("Fondsnaam"):  # only add relevant rows
                rows.append(row)
        return rows


def get_bnd_balances(scraped_data):
    to_float = lambda x: float(  # noqa: E731
        x.replace("€", "").replace(".", "").replace(",", ".").strip()
    )
    balances = {
        d["Fondsnaam"]: dict(
            amount=to_float(d["Aantal"]),
            value=to_float(d["Waarde"]),
            price=to_float(d["Koers"]),
        )
        for d in scraped_data
        if d["Aantal"] != "" and ("%" not in d["Aantal"])
    }
    return balances


if __name__ == "__main__":
    bnd = scrape_brand_new_day()
    print(bnd)
