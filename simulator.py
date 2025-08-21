# src/simulator.py
from __future__ import annotations
import math, random, time
from dataclasses import dataclass, asdict
from typing import Dict, List
from .config import ALGORITHMS, EFFECTIVE_OVERRIDES, HARDWARE_GUESS_RATES, THREAT_LEVEL_MULTIPLIER, ANALYTICAL_SHORTCUT

SECONDS_IN = {"minute":60, "hour":3600, "day":86400, "year": 31557600}

@dataclass
class Scenario:
    algorithm: str
    hardware: str          # CPU/GPU/CLUSTER
    threat: str            # Low/Medium/High
    attack_type: str       # "brute" or "analytical"

def effective_bits(alg_name: str, nominal_bits: int) -> int:
    if alg_name in EFFECTIVE_OVERRIDES and "effective_bits" in EFFECTIVE_OVERRIDES[alg_name]:
        return EFFECTIVE_OVERRIDES[alg_name]["effective_bits"]
    return nominal_bits

def guesses_per_second(hardware: str, threat: str) -> float:
    base = HARDWARE_GUESS_RATES[hardware]
    return base * THREAT_LEVEL_MULTIPLIER[threat]

def analytical_factor(alg_name: str, attack_type: str) -> float:
    if attack_type == "analytical":
        return ANALYTICAL_SHORTCUT.get(alg_name, 1.0)
    return 1.0

def median_bruteforce_time_seconds(bits: int, gps: float, factor: float) -> float:
    # Median guess is half the keyspace; divide by analytical factor
    eff_space = (2 ** bits) / factor
    return 0.5 * eff_space / gps

def humanize_seconds(s: float) -> str:
    if s < 1: return f"{s*1000:.2f} ms"
    if s < 60: return f"{s:.2f} s"
    if s < 3600: return f"{s/60:.2f} min"
    if s < 86400: return f"{s/3600:.2f} h"
    if s < SECONDS_IN["year"]: return f"{s/86400:.2f} days"
    return f"{s/SECONDS_IN['year']:.2f} years"

def simulate_one(scn: Scenario) -> Dict:
    spec = next(a for a in ALGORITHMS if a.name == scn.algorithm)
    bits = effective_bits(spec.name, spec.key_bits)
    gps = guesses_per_second(scn.hardware, scn.threat)
    af = analytical_factor(spec.name, scn.attack_type)
    tsec = median_bruteforce_time_seconds(bits, gps, af)
    return {
        "algorithm": spec.name,
        "family": spec.family,
        "key_bits_nominal": spec.key_bits,
        "key_bits_effective": bits,
        "hardware": scn.hardware,
        "threat": scn.threat,
        "attack_type": scn.attack_type,
        "guesses_per_second": gps,
        "analytical_factor": af,
        "median_time_seconds": tsec,
        "median_time_human": humanize_seconds(tsec),
    }

def generate_scenarios(n: int, seed: int = 42) -> List[Scenario]:
    random.seed(seed)
    algs = [a.name for a in ALGORITHMS]
    hardware = list(HARDWARE_GUESS_RATES.keys())
    threats = list(THREAT_LEVEL_MULTIPLIER.keys())
    attacks = ["brute", "analytical"]
    out = []
    for _ in range(n):
        out.append(Scenario(random.choice(algs), random.choice(hardware), random.choice(threats), random.choice(attacks)))
    return out
