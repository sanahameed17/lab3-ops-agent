"""
prom_range_export.py - our own script (31 Oct 2026). Reads a PAST time window from Prometheus
(query_range API), so before/during/after data of a chaos experiment can be recovered even if
the live monitor was not running at that moment. Standard library only; Clash proxy bypassed.

Usage (Prometheus port-forward on 127.0.0.1:9091):
  uv run python lab2_tools/prom_range_export.py --start "2026-10-31 18:48:00" --end "2026-10-31 19:02:00" --out lab2_tools/cpu_stress_window.csv
"""
import argparse
import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime

PROMETHEUS = "http://127.0.0.1:9091"
QUERIES = {
    "cpu_millicores": 'sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="bookinfo",container!="",container!="POD"}[1m])) * 1000',
    "memory_mib": 'sum by (pod) (container_memory_working_set_bytes{namespace="bookinfo",container!="",container!="POD"}) / 1048576',
}
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # bypass Clash


def query_range(promql, start, end, step):
    params = urllib.parse.urlencode({"query": promql, "start": start, "end": end, "step": step})
    with OPENER.open(f"{PROMETHEUS}/api/v1/query_range?{params}", timeout=60) as resp:
        data = json.load(resp)
    if data.get("status") != "success":
        raise RuntimeError(f"Prometheus error: {data}")
    out = {}
    for series in data["data"]["result"]:
        pod = series["metric"].get("pod", "?")
        for ts, val in series["values"]:
            out[(float(ts), pod)] = float(val)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help='local time, e.g. "2026-10-31 18:48:00"')
    ap.add_argument("--end", required=True)
    ap.add_argument("--step", type=int, default=15)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S").timestamp()
    end = datetime.strptime(args.end, "%Y-%m-%d %H:%M:%S").timestamp()
    data = {name: query_range(q, start, end, args.step) for name, q in QUERIES.items()}

    keys = sorted(set(data["cpu_millicores"]) | set(data["memory_mib"]))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "pod", "cpu_millicores", "memory_mib"])
        for ts, pod in keys:
            w.writerow([datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"), pod,
                        round(data["cpu_millicores"].get((ts, pod), 0.0), 2),
                        round(data["memory_mib"].get((ts, pod), 0.0), 2)])

    pp = [(ts, v) for (ts, pod), v in data["cpu_millicores"].items() if pod.startswith("productpage")]
    for ts, v in sorted(pp):
        print(datetime.fromtimestamp(ts).strftime("%H:%M:%S"), f"productpage CPU = {v:7.1f} m")
    print(f"\nSaved {len(keys)} rows to {args.out}")


if __name__ == "__main__":
    main()