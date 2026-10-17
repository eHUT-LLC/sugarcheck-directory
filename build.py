#!/usr/bin/env python3
"""
Turn listings.csv into sugarcheck-directory.json.

    python build.py            # writes sugarcheck-directory.json next to this file
    python build.py --check    # validate only

Upload the JSON to the URL in lib/directory.ts (DIRECTORY_URL). The app refreshes once a day.

Who is on and who is off is decided here, not in the app:
  active   = yes/no   (blank = yes). "no" keeps the row for your records but leaves it out of the JSON.
  expires  = YYYY-MM-DD (blank = never). After that date the row is left out automatically —
             set it to the last day a sponsor has paid for, and it falls off on its own.
The script prints which rows were skipped and why, so nothing disappears silently.
"""
import csv, json, re, sys, datetime, pathlib

HERE = pathlib.Path(__file__).parent
SRC = HERE / "listings.csv"
OUT = HERE / "sugarcheck-directory.json"
CATS = {"pharmacy","clinic","dietitian","podiatrist","eye","support","dental","other"}
TIERS = {"free","basic","featured","founding","county"}
HOURS_RE = re.compile(r"^\d{1,2}:\d{2}-\d{1,2}:\d{2}$")
DAYS = ["sun","mon","tue","wed","thu","fri","sat"]

def num(v):
    v = (v or "").strip()
    return float(v) if v else None

def main(check_only=False):
    rows, errors, ids, skipped = [], [], set(), []
    today = datetime.date.today().isoformat()
    with SRC.open(newline="", encoding="utf-8") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            rid = (r.get("id") or "").strip()
            if not rid: errors.append(f"line {n}: missing id"); continue
            if rid in ids: errors.append(f"line {n}: duplicate id {rid}")
            ids.add(rid)
            active = (r.get("active") or "yes").strip().lower()
            if active not in ("yes", "no", ""): errors.append(f"{rid}: active must be yes or no, got '{active}'")
            expires = (r.get("expires") or "").strip()
            if expires and not re.match(r"^\d{4}-\d{2}-\d{2}$", expires): errors.append(f"{rid}: expires must be YYYY-MM-DD, got '{expires}'")
            if active == "no": skipped.append(f"{rid}: active = no"); continue
            if expires and expires < today: skipped.append(f"{rid}: expired {expires}"); continue
            if r["category"] not in CATS: errors.append(f"{rid}: bad category '{r['category']}'")
            if r["tier"] not in TIERS: errors.append(f"{rid}: bad tier '{r['tier']}'")
            hours = []
            for d in DAYS:
                h = (r.get(d) or "").strip()
                if h and not HOURS_RE.match(h): errors.append(f"{rid}: bad {d} hours '{h}' (use HH:MM-HH:MM or blank)")
                hours.append(h)
            phone = re.sub(r"\D", "", r.get("phone") or "")
            if phone and len(phone) not in (10, 11): errors.append(f"{rid}: phone should be 10 digits")
            rows.append({
                "id": rid, "name": r["name"].strip(), "category": r["category"], "tier": r["tier"],
                "address": r["address"].strip(), "city": r["city"].strip(), "county": r["county"].strip(),
                "state": (r.get("state") or "MS").strip(), "zip": (r.get("zip") or "").strip(),
                "lat": num(r.get("lat")), "lng": num(r.get("lng")),
                "phone": phone, "website": (r.get("website") or "").strip(), "email": (r.get("email") or "").strip(),
                "hours": hours, "note": (r.get("note") or "").strip()[:120],
                **({"logo": r["logo"].strip()} if (r.get("logo") or "").strip() else {}),
            })
    if errors:
        print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
    for sk in skipped: print("skipped " + sk)
    doc = {"version": 1, "updated": datetime.date.today().isoformat(), "listings": rows}
    if check_only:
        print(f"OK: {len(rows)} listings"); return
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.name}: {len(rows)} listings, updated {doc['updated']}")

if __name__ == "__main__":
    main("--check" in sys.argv)
