# src/main.py
import argparse, sys, math, json
from .simulator import generate_scenarios, simulate_one, humanize_seconds
from .config import ALGORITHMS, HARDWARE_GUESS_RATES, THREAT_LEVEL_MULTIPLIER, EFFECTIVE_OVERRIDES
from .models import train_or_rule, predict

def cmd_simulate(args):
    scenarios = generate_scenarios(args.scenarios, seed=args.seed)
    rows = [simulate_one(s) for s in scenarios]
    rows.sort(key=lambda r: r["median_time_seconds"])
    print(f"[i] Simulated {len(rows)} scenarios. Weakest to strongest:")
    for r in rows[:10]:
        print(f" - {r['algorithm']:10s} | {r['hardware']:7s} | {r['threat']:6s} | {r['attack_type']:10s} | "
              f"{r['median_time_human']:>12s} (gps={r['guesses_per_second']:.2e})")
    print("...")
    for r in rows[-3:]:
        print(f" + Strong: {r['algorithm']:10s} | {r['median_time_human']}")

def cmd_train(args):
    scenarios = generate_scenarios(args.scenarios, seed=args.seed)
    rows = [simulate_one(s) for s in scenarios]
    try:
        import pandas as pd
        df = pd.DataFrame(rows)
    except Exception as e:
        print("pandas not available; training aborted.", file=sys.stderr); return
    reg, cls = train_or_rule(df)
    # Evaluate quick
    df["log_time_true"] = (df["median_time_seconds"]+1e-9).apply(math.log10)
    if reg is not None:
        pred = reg.predict(df[["key_bits_effective","guesses_per_second","analytical_factor"]].values)
        mae = (abs(pred - df["log_time_true"])).mean()
        print(f"[i] Trained RF regressor. MAE on log10(seconds): {mae:.3f}")
    if cls is not None:
        acc = (cls.predict(df[["key_bits_effective","guesses_per_second","analytical_factor"]].values) == df["median_time_seconds"].apply(lambda s: 'Weak' if s<86400 else ('Borderline' if s<31557600 else 'Strong'))).mean()
        print(f"[i] Trained RF classifier. Accuracy: {acc:.3f}")
    if args.save and reg is not None and cls is not None:
        import joblib, os
        os.makedirs(args.model_dir, exist_ok=True)
        joblib.dump(reg, f"{args.model_dir}/time_reg.joblib")
        joblib.dump(cls, f"{args.model_dir}/risk_cls.joblib")
        print(f"[i] Saved models to {args.model_dir}/")

def cmd_recommend(args):
    # Build candidate rows (one per algorithm) under the given constraints
    import pandas as pd
    rows = []
    for a in ALGORITHMS:
        # Equivalent bits override
        bits = a.key_bits
        if a.name in EFFECTIVE_OVERRIDES and "effective_bits" in EFFECTIVE_OVERRIDES[a.name]:
            bits = EFFECTIVE_OVERRIDES[a.name]["effective_bits"]
        gps = HARDWARE_GUESS_RATES[args.max_compute] * (2.0 if args.threat == "High" else (0.5 if args.threat=="Low" else 1.0))
        af = 1.0 if args.attack == "brute" else 1.5
        logt, risk = predict(None, None, bits, gps, af)  # uses analytic fallback unless sklearn models are loaded manually
        seconds = (10 ** logt)
        rows.append({
            "algorithm": a.name,
            "family": a.family,
            "effective_bits": bits,
            "estimated_time": seconds,
            "estimated_time_human": humanize_seconds(seconds),
            "risk": risk
        })
    df = pd.DataFrame(rows).sort_values("estimated_time", ascending=False)
    # Filter by time threshold
    thr = args.max_time_days * 86400.0
    ok = df[df["estimated_time"] >= thr]
    print("[i] Recommendation (meeting threshold):" if not ok.empty else "[!] No algorithm meets the threshold. Showing strongest anyway:")
    print((ok if not ok.empty else df).head(10).to_string(index=False))

def build_parser():
    p = argparse.ArgumentParser(description="Cyber Strength Recommender")
    sub = p.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("simulate", help="Run random simulations")
    s1.add_argument("--scenarios", type=int, default=200)
    s1.add_argument("--seed", type=int, default=42)
    s1.set_defaults(func=cmd_simulate)

    s2 = sub.add_parser("train", help="Train (optional) ML models")
    s2.add_argument("--scenarios", type=int, default=1000)
    s2.add_argument("--seed", type=int, default=42)
    s2.add_argument("--save", action="store_true")
    s2.add_argument("--model-dir", type=str, default="models")
    s2.set_defaults(func=cmd_train)

    s3 = sub.add_parser("recommend", help="Recommend algorithms under constraints")
    s3.add_argument("--max-time-days", type=float, default=365.0)
    s3.add_argument("--max-compute", choices=list(HARDWARE_GUESS_RATES.keys()), default="GPU")
    s3.add_argument("--threat", choices=["Low","Medium","High"], default="Medium")
    s3.add_argument("--attack", choices=["brute","analytical"], default="brute")
    s3.set_defaults(func=cmd_recommend)
    return p

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)

if __name__ == "__main__":
    main()
