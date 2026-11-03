"""
chaos_latency_run.py - our own script (31 Oct 2026).
Runs a chaos experiment on a FIXED timeline and measures productpage latency the whole time:
  baseline (no fault) -> kubectl apply <chaos yaml> -> keep measuring -> kubectl delete (cleanup).
Every request is saved to CSV with its time and phase, so before/during/after can be compared.
Requires: kubectl port-forward -n bookinfo svc/productpage 9080:9080
"""
import argparse
import csv
import statistics
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # bypass Clash


def probe(url, timeout):
    t0 = time.perf_counter()
    try:
        with OPENER.open(url, timeout=timeout) as r:
            r.read()
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        code = f"ERR:{type(e).__name__}"
    return (time.perf_counter() - t0) * 1000, code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yaml", required=True)
    ap.add_argument("--baseline", type=int, default=120, help="seconds before the chaos is applied")
    ap.add_argument("--chaos-seconds", type=int, default=120, help="duration written in the YAML")
    ap.add_argument("--after", type=int, default=120, help="seconds measured after the chaos ends")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--timeout", type=float, default=5.0)
    ap.add_argument("--url", default="http://127.0.0.1:9080/productpage")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    total = args.baseline + args.chaos_seconds + args.after
    start = time.time()
    applied = None
    rows = []
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "elapsed_s", "phase", "latency_ms", "http_status"])
        while time.time() - start < total:
            if applied is None and time.time() - start >= args.baseline:
                r = subprocess.run(["kubectl", "apply", "-f", args.yaml], capture_output=True, text=True)
                applied = time.time()
                print(f"\n>>> {datetime.now():%H:%M:%S} CHAOS APPLIED: {(r.stdout + r.stderr).strip()}\n")
            if applied is None:
                phase = "before"
            elif time.time() - applied < args.chaos_seconds:
                phase = "during"
            else:
                phase = "after"
            lat, code = probe(args.url, args.timeout)
            ts = datetime.now().strftime("%H:%M:%S")
            w.writerow([ts, round(time.time() - start, 1), phase, round(lat, 1), code])
            f.flush()
            rows.append((phase, lat, code))
            print(f"{ts}  {phase:6}  {lat:8.1f} ms  {code}")
            time.sleep(max(0.0, args.interval - lat / 1000))

    r = subprocess.run(["kubectl", "delete", "-f", args.yaml, "--wait=false"], capture_output=True, text=True)
    print(f"\n>>> cleanup: {(r.stdout + r.stderr).strip()}")

    print("\nphase    n    mean_ms   p50_ms   p95_ms   errors")
    for phase in ("before", "during", "after"):
        lats = sorted(l for p, l, c in rows if p == phase and c == 200)
        errs = sum(1 for p, l, c in rows if p == phase and c != 200)
        if lats:
            p95 = lats[min(len(lats) - 1, int(0.95 * len(lats)))]
            print(f"{phase:6} {len(lats):4} {statistics.mean(lats):9.1f} {statistics.median(lats):8.1f} {p95:8.1f} {errs:8}")
    print(f"\nSaved: {args.out}")


if __name__ == "__main__":
    main()