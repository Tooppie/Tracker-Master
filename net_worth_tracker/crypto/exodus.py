import math
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd


@lru_cache
def get_exodus(
    csv_fname: Optional[str] = None,
    csv_folder: str = "~/Desktop/exodus-exports/",
):
    if csv_fname is None:
        csv_fname = sorted(Path(csv_folder).expanduser().glob("*all-txs-*.csv"))[-1]
    balances = defaultdict(float)
    df = pd.read_csv(Path(csv_fname).expanduser())
    for i, row in df.iterrows():
        if isinstance(row.INCURRENCY, str) or not math.isnan(row.INCURRENCY):
            balances[row.INCURRENCY] += row.INAMOUNT

        if isinstance(row.OUTCURRENCY, str) or not math.isnan(row.OUTCURRENCY):
            balances[row.OUTCURRENCY] += row.OUTAMOUNT

        if isinstance(row.FEECURRENCY, str) or not math.isnan(row.FEECURRENCY):
            balances[row.FEECURRENCY] += row.FEEAMOUNT

    return {k: dict(amount=v) for k, v in balances.items() if v > 1e-12}
