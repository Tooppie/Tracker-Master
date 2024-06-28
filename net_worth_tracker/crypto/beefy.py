from __future__ import annotations

from functools import lru_cache

import js2py
import requests
from web3 import HTTPProvider, Web3
from web3.middleware import geth_poa_middleware

from net_worth_tracker.utils import euro_per_dollar

# from https://github.com/beefyfinance/beefy-app/blob/edbf199aee36728f06e16c05af1a2af36475f068/src/common/networkSetup.js
RPCS = {
    "bsc": "https://bsc-dataseed.binance.org",
    "heco": "https://http-mainnet.hecochain.com",
    "avalanche": "https://api.avax.network/ext/bc/C/rpc",
    "polygon": "https://polygon-rpc.com",
    "fantom": "https://rpc.ftm.tools",
    "harmony": "https://api.s0.t.hmny.io/",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "celo": "https://forno.celo.org",
    "moonriver": "https://rpc.moonriver.moonbeam.network",
}

GITHUB_RAW = "https://raw.githubusercontent.com/beefyfinance/beefy-app/master"


@lru_cache
def get_abis():
    # Get ABIs for Beefy
    r = requests.get(f"{GITHUB_RAW}/src/features/configure/abi.js")

    abis = {}
    for line in r.text.split("\n"):
        name, js = line.split(" = ")
        name = name.replace("export const ", "")
        abis[name] = js2py.eval_js(js).to_list()
    return abis


@lru_cache
def get_prices():
    oracles = {
        "lps": requests.get("https://api.beefy.finance/lps").json(),
        "tokens": requests.get("https://api.beefy.finance/prices").json(),
        "apy": requests.get("https://api.beefy.finance/apy").json(),
    }
    return oracles


@lru_cache
def get_pools():
    networks = [
        "arbitrum",
        "avalanche",
        "bsc",
        "celo",
        "fantom",
        "harmony",
        "heco",
        "moonriver",
        "polygon",
    ]
    base = GITHUB_RAW + "/src/features/configure/vault/{name}_pools.js"
    pools = {}
    for network in networks:
        r = requests.get(base.format(name=network))
        text = r.text.split(" = ")
        assert len(text) == 2
        lst = js2py.eval_js(text[1]).to_list()
        pools[network] = {info["id"]: info for info in lst}
    return pools


@lru_cache
def get_abi_poly(id):
    addr = get_pools()["polygon"][id]["tokenAddress"]
    url = (
        f"https://api.polygonscan.com/api?module=contract&action=getabi&address={addr}"
    )
    r = requests.get(url)
    return r.json()["result"]


def get_web3_and_contract(vault):
    w3 = Web3(
        HTTPProvider(
            endpoint_uri=RPCS[vault["chain"]],
            request_kwargs={"timeout": 10},
        )
    )
    ID = vault["id"]
    pool = get_pools()[vault["chain"]][ID]
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    contract_beefy = w3.eth.contract(
        pool["earnContractAddress"],
        abi=get_abis()[vault["abi"]],
    )
    if vault["chain"] == "polygon":
        # Only works on polygon now
        contract_underlying = w3.eth.contract(
            pool["tokenAddress"],
            abi=get_abi_poly(vault["id"]),
        )
    else:
        contract_underlying = None
    return w3, contract_beefy, contract_underlying


def get_from_blockchain(
    vault,
    w3: Web3 | None = None,
    contract=None,
    blocks_back: int = 0,
    with_timestamp: bool = False,
):
    if w3 is None:
        w3, contract, _ = get_web3_and_contract(vault)
    block = int(w3.eth.get_block_number() - blocks_back)
    kw = dict(block_identifier=block)
    balance = contract.caller.balanceOf(
        vault["my_address"], **kw
    ) * contract.caller.getPricePerFullShare(**kw)
    decimals = contract.caller.decimals()
    balance /= (10**decimals) ** 2
    prices = get_prices()

    # Get price
    pool = get_pools()[vault["chain"]][vault["id"]]
    price = prices[pool["oracle"]][pool["oracleId"]]

    value = balance * price * euro_per_dollar()
    info = {"amount": balance, "value": value, "price": price}
    if with_timestamp:
        info["timestamp"] = w3.eth.get_block(**kw).timestamp
    return info
