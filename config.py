# src/config.py
from dataclasses import dataclass

@dataclass(frozen=True)
class AlgorithmSpec:
    name: str
    family: str          # 'symmetric' or 'asymmetric'
    key_bits: int
    block_bits: int | None
    analytical_reduction: float  # >=1, how much easier than pure brute force (1 = no shortcut)

ALGORITHMS = [
    AlgorithmSpec("AES-128",  "symmetric", 128, 128, 1.0),
    AlgorithmSpec("AES-192",  "symmetric", 192, 128, 1.0),
    AlgorithmSpec("AES-256",  "symmetric", 256, 128, 1.0),
    AlgorithmSpec("3DES-168", "symmetric", 168, 64,  1.0),  # effective ~112 bits in practice but we keep 168 and use reduction below
    AlgorithmSpec("DES-56",   "symmetric", 56,  64,  1.0),
    # RSA modeled via equivalent symmetric security bits; block_bits N/A
    AlgorithmSpec("RSA-1024", "asymmetric", 80,  None, 1.0),   # ≈80-bit security
    AlgorithmSpec("RSA-2048", "asymmetric", 112, None, 1.0),   # ≈112-bit security
    AlgorithmSpec("RSA-3072", "asymmetric", 128, None, 1.0),   # ≈128-bit security
]

# Practical reductions:
# - 3DES effective security often ~112 bits: model via reduction factor against its nominal 168-bit key
EFFECTIVE_OVERRIDES = {
    "3DES-168": {"effective_bits": 112},
    "DES-56":   {"effective_bits": 56},
}

# Attacker hardware profiles (very rough orders of magnitude)
HARDWARE_GUESS_RATES = {
    "CPU":     2**28,   # ~268M guesses/sec
    "GPU":     2**34,   # ~17B guesses/sec
    "CLUSTER": 2**40,   # ~1T guesses/sec
}

THREAT_LEVEL_MULTIPLIER = {
    "Low": 0.5,
    "Medium": 1.0,
    "High": 2.0,
}

# Map of algorithm-specific analytical shortcuts (toy values; keep 1.0 unless modeling known weakness)
ANALYTICAL_SHORTCUT = {
    "DES-56": 2.0,      # DES easier than pure brute force due to known cryptanalysis
    "3DES-168": 1.5,
}
