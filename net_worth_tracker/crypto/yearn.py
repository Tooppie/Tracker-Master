from functools import lru_cache

import requests
from web3 import HTTPProvider, Web3

RPCS = {
    "fantom": "https://rpc.ftm.tools",
}

GITHUB_RAW = "https://raw.githubusercontent.com/yearn/yearn-finance-v3/d3c24208191f17df5e98df0f946fc284c803aacb/"


@lru_cache
def get_abi():
    r = requests.get(f"{GITHUB_RAW}/src/core/services/contracts/vault.json")
    return r.json()


@lru_cache
def get_pools():
    return {
        "fantom": {
            # https://beta.yearn.finance/#/vault/0x0DEC85e74A92c52b7F708c4B10207D9560CEFaf0
            "ftm": {"earnContractAddress": "0x0DEC85e74A92c52b7F708c4B10207D9560CEFaf0"}
        }
    }


def get_from_blockchain(vault):
    w3 = Web3(
        HTTPProvider(
            endpoint_uri=RPCS[vault["chain"]],
            request_kwargs={"timeout": 10},
        )
    )
    ID = vault["id"]
    pool = get_pools()[vault["chain"]][ID]
    c = w3.eth.contract(
        pool["earnContractAddress"],
        abi=get_abi(),
    )
    balance = c.caller.balanceOf(vault["my_address"]) * c.caller.pricePerShare()
    decimals = c.caller.decimals()
    balance /= (10**decimals) ** 2
    return {"amount": balance}
