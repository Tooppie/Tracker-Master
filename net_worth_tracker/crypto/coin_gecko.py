from collections import defaultdict

from pycoingecko import CoinGeckoAPI


def get_coins(balances, cg: CoinGeckoAPI):
    sym2name = {  # mapping for duplicates
        "auto": "Auto",
        "bifi": "Beefy.Finance",
        "uni": "Uniswap",
        "one": "Harmony",
        "onx": "OnX Finance",
        "bunny": "Pancake Bunny",
        "rune": "THORChain",
        "btcb": "Binance Bitcoin",
        "mash": "MarshmallowDeFi",
        "stx": "Stacks",
        "dot": "Polkadot",
        "ada": "Cardano",
        "xrp": "XRP",
        "tlm": "Alien Worlds",
        "ltc": "Litecoin",
        "bat": "Basic Attention Token",
        "bch": "Bitcoin Cash",
        "ata": "Automata",
        "alpaca": "Alpaca Finance",
        "ica": "Icarus Finance",
        "flux": "Flux",
        "banana": "ApeSwap Finance",
        "ftm": "Fantom",
        "xno": "Nano",
        "luna": "Terra",
        "wmatic": "Wrapped Matic",
        "ust": "TerraUSD",
        "time": "Wonderland",
        "mim": "Magic Internet Money",
        "usdt": "Tether",
        "eth": "Ethereum",
        "usdc": "USD Coin",
        "dai": "Dai",
    }

    symbols = [c.lower() for c in balances]

    coin_list = cg.get_coins_list()

    # Check for duplicate symbols in coin list
    symbol_map = defaultdict(list)
    for c in coin_list:
        symbol_map[c["symbol"]].append(c)
    duplicates = {symbol for symbol, lst in symbol_map.items() if len(lst) > 1}
    duplicates = duplicates.intersection(symbols)
    unknown_duplicates = list(duplicates.difference(sym2name.keys()))
    for symbol in unknown_duplicates:
        infos = symbol_map[symbol]
        print(f"{symbol} appears twice! Edit `sym2name`. " f"Use one of:\n{infos}.")
        # Getting the coin with the largest market cap
        prices = cg.get_price(
            ids=[info["id"] for info in infos],
            vs_currencies="eur",
            include_market_cap="true",
        )
        mc, info = max(
            (
                (prices[info["id"]]["eur_market_cap"], info)
                for info in infos
                if prices[info["id"]]  # sometimes dict is empty
            ),
            key=lambda x: x[0],
        )

        sym2name[symbol] = info["name"]
        print(
            f"Guessing sym2name => '{info['symbol']}': '{info['name']}' because of higher Market Cap (€{mc:.2f})"
        )

    sym2id = {}
    id2sym = {}
    for c in coin_list:
        symbol = c["symbol"].lower()
        if symbol in duplicates and c["name"] != sym2name[symbol]:
            continue
        sym2id[symbol] = c["id"]
        id2sym[c["id"]] = symbol.upper()
    return sym2id, id2sym


def get_prices(balances):
    cg = CoinGeckoAPI()
    sym2id, id2sym = get_coins(balances, cg)
    ids = {sym2id[c.lower()] for c in balances if c.lower() in sym2id}
    ids.add(sym2id["busd"])
    prices = cg.get_price(ids=list(ids), vs_currencies="eur")
    # Sometime the "eur" key is missing, this happens
    # when the ticker is on CoinGecko but without price history
    prices = {id2sym[k]: v.get("eur") for k, v in prices.items()}
    return prices


def add_value_and_price(balances, ignore=("degiro", "brand_new_day")):
    renames = {"IOTA": "MIOTA", "NANO": "XNO", "WETH.E": "ETH"}
    renames_reverse = {v: k for k, v in renames.items()}

    to_fetch = set()
    for where, bals in balances.items():
        for coin, bal in bals.items():
            if "value" not in bal and where not in ignore:
                to_fetch.add(renames.get(coin, coin))

    to_fetch.discard("EUR")
    prices = get_prices(to_fetch)
    for coin, price in list(prices.items()):
        if coin in renames_reverse:
            prices[renames_reverse[coin]] = price

    for where, bals in balances.items():
        for coin, bal in bals.items():
            if "value" not in bal and where not in ignore:
                if coin == "EUR":
                    price = 1
                elif coin in prices:
                    price = prices[coin]
                    if price is None:
                        # Happens when ticker is on CoinGecko but without price history
                        continue
                elif coin.startswith("moo"):
                    continue  # are taking into consideration in YieldWatch
                else:
                    print(f"Fuck, no data for {coin}")
                    continue
                bal["price"] = price
                bal["value"] = bal["amount"] * price
