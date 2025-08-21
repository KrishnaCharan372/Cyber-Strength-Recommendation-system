# src/models.py
from __future__ import annotations
import math
from typing import Tuple
try:
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    SKLEARN_OK = True
except Exception:
    SKLEARN_OK = False

RISK_BUCKETS = [
    ("Weak", -1e9,  86400),        # < 1 day
    ("Borderline", 86400, 31557600),  # 1 day .. 1 year
    ("Strong", 31557600, 1e30),    # > 1 year
]

def bucketize(seconds: float) -> str:
    for name, lo, hi in RISK_BUCKETS:
        if lo <= seconds < hi:
            return name
    return "Strong"

def train_or_rule(df):
    # Always compute a rule-based recommendation as a fallback
    df["log_time"] = (df["median_time_seconds"] + 1e-9).apply(math.log10)
    df["risk"] = df["median_time_seconds"].apply(bucketize)
    if not SKLEARN_OK:
        return None, None  # caller should use df["risk"] and df["log_time"]
    # Train small models
    X = df[["key_bits_effective","guesses_per_second","analytical_factor"]].values
    y_reg = df["log_time"].values
    y_cls = df["risk"].values
    reg = RandomForestRegressor(n_estimators=120, random_state=17)
    cls = RandomForestClassifier(n_estimators=120, random_state=17)
    reg.fit(X, y_reg)
    cls.fit(X, y_cls)
    return reg, cls

def predict(reg, cls, key_bits_effective, gps, af) -> Tuple[float, str]:
    if reg is None or cls is None or not SKLEARN_OK:
        # analytic fallback
        seconds = 0.5 * (2 ** key_bits_effective) / (gps * max(1.0, af))
        risk = bucketize(seconds)
        return math.log10(seconds+1e-9), risk
    import numpy as np
    X = np.array([[key_bits_effective, gps, af]])
    logt = reg.predict(X)[0]
    risk = cls.predict(X)[0]
    return logt, risk
