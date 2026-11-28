#!/usr/bin/env python3
"""Pilih topik yang perlu Ringkasan AI, sesuai yang tampil di aplikasi.

Kandidat = 30 topik terpopuler + 30 topik terbaru dalam rentang (bawaan 12 jam),
yang belum punya ringkasan di data/ringkasan.json dan bukan topik kembar (kunci merge).
Urutan keluaran: artikel terbaru dulu. Keluaran: JSON array ke stdout.

Pakai: python3 scripts/pick_for_summary.py [--hours 12] [--limit 15]
"""
import argparse
import json
import os
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATS = {"Aksi korporasi": 0, "Regulasi": 1, "Kinerja": 2, "Makro": 3}


def load(name, default):
    try:
        with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=12)
    ap.add_argument("--limit", type=int, default=15)
    args = ap.parse_args()

    live = load("live.json", {"topics": []})
    ai = load("ringkasan.json", {"items": {}, "merge": {}})
    items, merge = ai.get("items", {}), ai.get("merge", {})
    covered_urls = {u for it in items.values() for u in it.get("urls", [])}

    start = datetime.fromisoformat(live["updated"]) - timedelta(hours=args.hours)
    rows = []
    for t in live.get("topics", []):
        if t["id"] in merge:
            continue
        src = [s for s in t["sources"] if datetime.fromisoformat(s["time"]) >= start]
        if not src:
            continue
        latest = max(datetime.fromisoformat(s["time"]) for s in src)
        first = min(datetime.fromisoformat(s["time"]) for s in t["sources"])
        rows.append((t, len({s["media"] for s in src}), len(src), latest, first))

    popular = sorted(rows, key=lambda r: (-r[1], -r[2], CATS.get(r[0]["category"], 9), -r[3].timestamp()))[:30]
    newest = sorted(rows, key=lambda r: -r[4].timestamp())[:30]
    seen, picked = set(), []
    for r in sorted(popular + newest, key=lambda r: -r[3].timestamp()):
        t = r[0]
        if t["id"] in seen:
            continue
        seen.add(t["id"])
        if t["id"] in items or any(s["url"] in covered_urls for s in t["sources"]):
            continue
        picked.append({
            "id": t["id"],
            "title": t["title"],
            "tickers": t.get("tickers", []),
            "latest": r[3].isoformat(),
            "sources": [{"media": s["media"], "title": s.get("title", ""), "url": s["url"], "time": s["time"]} for s in t["sources"]],
        })
        if len(picked) >= args.limit:
            break
    print(json.dumps(picked, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
