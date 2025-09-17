#!/usr/bin/env python3
"""
main.py

Minimal script that hardcodes the Bearer token so you can run:

    python3 main.py

Produces:
 - users.csv
 - users.xlsx

Dependencies:
    pip install requests pandas openpyxl
"""

from __future__ import annotations
import json
import sys
from itertools import islice
from typing import Any, Dict, List

import pandas as pd
import requests

# ----------------- CONFIG: edit these values if needed -----------------
# Put your token here (hardcoded as requested)
TOKEN = "eyJraWQiOiIxIiwiYWxnIjoiRWREU0EifQ.eyJpc3MiOiJraWNrYm94LWltcHJvdmUiLCJzdWIiOiJhNjE0ZWZjOC0zMmI4LTRjYjItYjgwYi1iYzRiZDAxOGVkOWQiLCJhdWQiOiJQQVNIQUhvbGRpbmciLCJjb250ZXh0cyI6WyJQQVNIQUhvbGRpbmciXSwiZXhwIjoxNzYwNjc3Mjg1fQ.GXMVeQ8gFXvzsV97V_NQ5adDW27AN-CmHFHbeIsoArKU4UoeXAc8RQnInoK_a_hjgJJ7PoJLCiae5ZGlMC6IDQ"   # <-- replace with your full bearer token string

SEARCH_URL = "https://api.rready.com/PASHAHolding/global-search/users"
BATCH_URL = "https://api.rready.com/PASHAHolding/users/fetchByBatch"

# Default search payload used by your example
SEARCH_PAYLOAD = {
    "query": "*",
    "order": {"field": "firstName.keyword", "direction": "DESC"},
    "where": [
        {"field": "deleted", "match": [False], "matchMode": "EQUAL"},
        {"field": "enabled", "match": [True], "matchMode": "EQUAL"},
    ],
    "limit": 500,
}

# How many UUIDs to send per batch request to /fetchByBatch
BATCH_SIZE = 100

# Output filenames
CSV_OUTPUT = "users.csv"
XLSX_OUTPUT = "users.xlsx"
# ----------------------------------------------------------------------

def chunked_iterable(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk

def flatten_dict(d: Dict[str, Any], parent: str = "") -> Dict[str, Any]:
    out = {}
    for k, v in d.items():
        key = f"{parent}.{k}" if parent else k
        if isinstance(v, dict):
            out.update(flatten_dict(v, key))
        else:
            out[key] = v
    return out

def normalize_users(users: List[Dict]) -> pd.DataFrame:
    rows = []
    keys = set()
    for u in users:
        flat = {}
        for k, v in u.items():
            if isinstance(v, dict):
                flat.update(flatten_dict(v, parent=k))
            elif isinstance(v, list):
                # simple lists -> comma-joined; complex -> json string
                if all(not isinstance(x, (dict, list)) for x in v):
                    flat[k] = ", ".join(str(x) for x in v)
                else:
                    try:
                        flat[k] = json.dumps(v, ensure_ascii=False)
                    except Exception:
                        flat[k] = str(v)
            else:
                flat[k] = v
        rows.append(flat)
        keys.update(flat.keys())

    preferred = ["id", "email", "firstName", "lastName", "username", "language", "unit"]
    rest = sorted(k for k in keys if k not in preferred)
    ordered = [k for k in preferred if k in keys] + rest

    df = pd.DataFrame([{k: r.get(k, "") for k in ordered} for r in rows])
    return df

def main():
    if not TOKEN or TOKEN.startswith("eyJYOUR"):
        print("ERROR: Please open main.py and set TOKEN to your Bearer token string.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        # If you normally use app-id header, enable it here:
        # "app-id": "app",
    }

    session = requests.Session()
    session.headers.update(headers)

    print("1) Requesting UUIDs from search endpoint...")
    try:
        r = session.post(SEARCH_URL, json=SEARCH_PAYLOAD, timeout=30)
    except Exception as e:
        print("Network error when calling search endpoint:", e)
        sys.exit(2)

    if r.status_code == 401:
        print("Unauthorized (401). Token invalid or expired.")
        sys.exit(3)
    if r.status_code != 200:
        print(f"Search endpoint returned {r.status_code}: {r.text[:300]}")
        sys.exit(4)

    try:
        uuids = r.json()
    except Exception as e:
        print("Failed to parse JSON from search response:", e)
        sys.exit(5)

    if not isinstance(uuids, list) or len(uuids) == 0:
        print("Search did not return UUID list or returned empty list.")
        sys.exit(6)

    # dedupe preserving order
    seen = set()
    deduped = []
    for u in uuids:
        if u not in seen:
            seen.add(u)
            deduped.append(u)

    print(f"Found {len(deduped)} UUIDs. Fetching users in batches of {BATCH_SIZE}...")

    all_users: List[Dict] = []
    for idx, chunk in enumerate(chunked_iterable(deduped, BATCH_SIZE), start=1):
        payload = {"targets": chunk}
        try:
            resp = session.post(BATCH_URL, json=payload, timeout=60)
        except Exception as e:
            print(f"Network error during batch {idx}:", e)
            sys.exit(7)

        if resp.status_code == 401:
            print("Unauthorized (401) during batch fetch. Token invalid or expired.")
            sys.exit(8)
        if resp.status_code != 200:
            print(f"Batch endpoint returned {resp.status_code} for chunk {idx}: {resp.text[:300]}")
            sys.exit(9)

        try:
            data = resp.json()
        except Exception as e:
            print(f"Failed to parse JSON for chunk {idx}:", e)
            sys.exit(10)

        if not isinstance(data, list):
            print(f"Unexpected batch response format for chunk {idx}. Expected list, got {type(data)}")
            sys.exit(11)

        print(f"  chunk {idx}: fetched {len(data)} users")
        all_users.extend(data)

    print(f"Total user objects fetched: {len(all_users)}")
    if not all_users:
        print("No users returned. Exiting.")
        sys.exit(0)

    print("Normalizing and flattening user objects...")
    df = normalize_users(all_users)

    print(f"Writing CSV -> {CSV_OUTPUT}")
    df.to_csv(CSV_OUTPUT, index=False, encoding="utf-8")

    print(f"Writing Excel -> {XLSX_OUTPUT}")
    df.to_excel(XLSX_OUTPUT, index=False)

    print("Done.")
    print("Created files:")
    print(" -", CSV_OUTPUT)
    print(" -", XLSX_OUTPUT)

if __name__ == "__main__":
    main()
