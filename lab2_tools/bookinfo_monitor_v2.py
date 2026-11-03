"""
bookinfo_monitor_v2.py - RE-IMPLEMENTED on 31 Oct 2026 for the Lab 2 re-runs.
The original bookinfo_monitor.py used in Lab 2 could not be found on the computer, so this
new script was written; it is NOT presented as the original.

Standard library only (urllib). The Windows system proxy (Clash) is bypassed for the local
Prometheus port-forward. Every sample is printed and appended to a CSV file, so the data can
be plotted as a time series (before / during / after a Chaos Mesh experiment).

Usage (with `kubectl port-forward -n monitoring svc/<prometheus-service> 9091:9090` running):
    uv run python lab2_tools/bookinfo_monitor_v2.py --minutes 1 --interval 15 --out lab2_tools/test.csv
"""
import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime

PROMETHEUS = "http://127.0.0.1:9091"
QUERIES = {
    "cpu_millicores": 'sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="bookinfo",container!="",container!="POD"}[1m])) * 1000',
    "memory_mib": 'sum by (pod) (container_memory_working_set_bytes{namespace="bookinfo",container!="",container!="POD"}) / 1048576',
    "restarts": 'sum by (pod) (kube_pod_container_status_restarts_total{namespace="bookinfo"})',
}
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # bypass Clash


def query(promql):
    url = f"{PROMETHEUS}/api/v1/query?" + urllib.parse.urlencode({"query": promql})
    with OPENER.open(url, timeout=15) as resp:
        data = json.load(resp)
    if data.get("status") != "success":
        raise RuntimeError(f"Prometheus error: {data}")
    return {r["metric"].get("pod", "?"): float(r["value"][1]) for r in data["data"]["result"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=1.0)
    ap.add_argument("--interval", type=int, default=15)
    ap.add_argument("--out", default="lab2_tools/monitor.csv")
    args = ap.parse_args()

    end = time.time() + args.minutes * 60
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "pod", "cpu_millicores", "memory_mib", "restarts"])
        while time.time() < end:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            values = {name: query(q) for name, q in QUERIES.items()}
            pods = sorted(set().union(*values.values()))
            print(f"\n=== {ts} ===")
            print(f"{'pod':45} {'CPU (m)':>9} {'Mem (MiB)':>10} {'Restarts':>9}")
            for pod in pods:
                cpu = values["cpu_millicores"].get(pod, 0.0)
                mem = values["memory_mib"].get(pod, 0.0)
                rst = values["restarts"].get(pod, 0.0)
                print(f"{pod:45} {cpu:9.1f} {mem:10.1f} {rst:9.0f}")
                writer.writerow([ts, pod, round(cpu, 2), round(mem, 2), int(rst)])
            f.flush()
            time.sleep(args.interval)
    print(f"\nSaved: {args.out}")


if __name__ == "__main__":
    main()