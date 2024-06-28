import time
from collections import defaultdict
from functools import lru_cache
from typing import Literal, Optional

import requests
from bscscan import BscScan

from net_worth_tracker.utils import euro_per_dollar, read_config

IGNORE_TOKENS = {"VERA"}

# Pool/vault -> coin name
LP_MAPPING = {
    "BELT-BNB BELT LP": "BELT-BNB-LP",
    "Belt Venus BLP": "Belt-Venus-BLP",
    "AUTO-WBNB Pool": "AUTO-WBNB-LP",
}
LP_MAPPING_REVERSE = {v: k for k, v in LP_MAPPING.items()}
RENAMES = {
    "Cake": "CAKE",
    "sBDO": "SBDO",
}


@lru_cache
def get_bep20_balances(my_address: Optional[str] = None, api_key: Optional[str] = None):
    config = read_config()
    if my_address is None:
        my_address = config["bsc"]["address"]
    if api_key is None:
        api_key = config["bscscan"]["api_key"]

    bsc = BscScan(api_key)
    my_address = my_address.lower()
    txs = bsc.get_bep20_token_transfer_events_by_address(
        address=my_address, startblock=0, endblock=999999999, sort="asc"
    )
    balances = defaultdict(float)
    for d in txs:
        symbol = d["tokenSymbol"]
        if symbol in IGNORE_TOKENS:
            continue
        if d["to"].lower() == my_address:
            # Incoming tokens
            sign = +1
        else:
            sign = -1
        factor = 10 ** int(d["tokenDecimal"])
        balances[symbol] += sign * float(d["value"]) / factor

    # Get BNB balance
    balances["BNB"] += float(bsc.get_bnb_balance(address=my_address)) / 1e18

    # Remove 0 or negative balances
    # TODO: why can it become negative?
    balances = {k: v for k, v in balances.items() if v > 0}
    renames = {"Belt.fi bDAI/bUSDC/bUSDT/bBUSD": "BUSD"}
    for old, new in renames.items():
        if old in balances:
            balances[new] = balances.pop(old)

    return {k: dict(amount=v) for k, v in balances.items()}


def get_wallet_balances_from_yieldwatch(
    raw: dict, base="EUR", minimum_value: float = 1.0
):
    base_currency = raw["currencies"][base]
    balances = {}
    for info in raw["walletBalance"]["balances"]:
        info = info.copy()
        info["price"] = info["priceInUSD"] / base_currency
        info["value"] = info["balance"] * info["price"]
        if info["value"] >= minimum_value:
            balances[info["symbol"]] = {
                "amount": info["balance"],
                "price": info["price"],
                "value": info["value"],
            }
    return balances


@lru_cache
def get_yieldwatch_balances(  # noqa: C901
    my_address: Optional[str] = None,
    return_raw_data: bool = False,
    network: Literal["bsc", "polygon"] = "bsc",
    bearer_token: Optional[str] = None,
):
    config = read_config()
    if my_address is None:
        my_address = config["bsc"]["address"]
    if network == "bsc":
        platforms = {
            "Acryptos": "acryptos",
            "Alpha": "alpha",
            "ApeSwap": "apeswap",
            "Autofarm": "auto",
            "BeefyFinance": "beefy",
            "Belt": "belt",
            "Biswap": "biswap",
            "Blizzard": "blizzard",
            "bunny": "bunny",
            "Bunnypark": "bunnypark",
            "CreamFinance": "cream",
            "Fortress": "fortress",
            "HyperJump": "hyperjump",
            "Jetfuel": "jetfuel",
            "MDex": "mdex",
            "Moonpot": "moonpot",
            "PancakeSwap": "pancake",
            "Qubit": "qubit",
            "Venus": "venus",
            "Wault": "wault",
        }
    elif network == "polygon":
        platforms = {
            "BeefyFinance": "beefy",
            "ApeSwap": "apeswap",
            "Wault": "wault",
            "Sushi": "sushi",
            "QuickSwap": "quickswap",
            "Jetfuel": "jetfuel",
            "CreamFinance": "cream",
            # "Autofarm": "auto",  # Not yet supported
        }
    platforms_str = ",".join(platforms.values())
    which = {"bsc": "all", "polygon": "poly"}[network]
    url = (
        f"https://www.yieldwatch.net/api/{which}/{my_address}?platforms={platforms_str}"
    )
    for i in range(3):
        kwargs = {}
        if bearer_token is not None:
            kwargs["headers"] = {"Authorization": f"Bearer {bearer_token}"}
        req = requests.get(url, **kwargs)
        response = req.json()
        if "result" in response:
            raw_data = response["result"]
            break
        elif i == 2:
            raise RuntimeError("Tried trice and failed getting YieldWatch")
        time.sleep(2)

    balances = defaultdict(lambda: defaultdict(float))
    for k, v in raw_data.items():
        if k in ("watchBalance", "currencies", "walletBalance"):
            continue
        if k not in platforms:
            print(f"the '{k}' platform was not requested in the yieldwatch url!")
        if "vaults" in v:
            for vault in v["vaults"]["vaults"]:
                if (deposit_token := vault.get("depositToken")) is not None:
                    balances[deposit_token]["amount"] += vault["currentTokens"]
                    balances[deposit_token]["price"] = (
                        vault["priceInUSDDepositToken"] * euro_per_dollar()
                    )
                if (reward_token := vault.get("rewardToken")) is not None:
                    balances[reward_token]["amount"] += vault["pendingRewards"]
                    balances[reward_token]["price"] = (
                        vault["priceInUSDRewardToken"] * euro_per_dollar()
                    )
        if "LPVaults" in v:
            for vault in v["LPVaults"]["vaults"]:
                if (deposit_token := vault.get("depositToken")) is not None:
                    balances[deposit_token]["amount"] += vault["currentTokens"]
                    balances[deposit_token]["price"] = (
                        vault["priceInUSDDepositToken"] * euro_per_dollar()
                    )
        if "staking" in v:
            for vault in v["staking"]["vaults"]:
                if (deposit_token := vault.get("depositToken")) is not None:
                    balances[deposit_token]["amount"] += float(vault["depositedTokens"])
                    balances[deposit_token]["price"] = vault["priceInUSDDepositToken"]
                for ext in ["", "1", "2", "3"]:
                    if (reward_token := vault.get(f"rewardToken{ext}")) is not None:
                        balances[reward_token]["amount"] += float(
                            vault[f"pendingRewards{ext}"]
                        )
                        balances[reward_token]["price"] = (
                            float(vault[f"priceInUSDRewardToken{ext}"])
                            * euro_per_dollar()
                        )
        if "barnOfTrust" in v:
            for vault in v["barnOfTrust"]["vaults"]:
                if (deposit_token := vault.get("depositToken")) is not None:
                    balances[deposit_token]["amount"] += float(vault["depositedTokens"])
                    balances[deposit_token]["price"] = vault["priceInUSDDepositToken"]
                if (reward_token := vault.get("rewardToken")) is not None:
                    balances[reward_token]["amount"] += float(vault["pendingRewards"])
                    balances[reward_token]["price"] = (
                        float(vault["priceInUSDRewardToken"]) * euro_per_dollar()
                    )
    balances = {
        RENAMES.get(k, k): dict(v, value=v["amount"] * v["price"])
        for k, v in balances.items()
        if v["amount"] > 0
    }
    if return_raw_data:
        return balances, raw_data
    return balances
