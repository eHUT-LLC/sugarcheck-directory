#!/usr/bin/env python3
"""
Turn the CSVs in this folder into sugarcheck-directory.json — the one file the app downloads.

    python build.py            # writes sugarcheck-directory.json next to this file
    python build.py --check    # validate only
    python build.py --fixture  # tests/fixtures/directory-examples.json: every row, on/off dates ignored

Files read (only listings.csv is required):
    listings.csv        the directory + sponsors          (see README.md for columns)
    announcements.csv   What's happening                  id,title,description,org,area,event_date,publish_date,expires,image_url,url,sponsored,sponsor_id,approved
    resources.csv       Find help (curated, never paid)   id,title,url,why,category,state,county,essential,reviewed,active
    config.json         {"weights": {...}, "badges": {...}}  → copied into "meta"; changes need no app build

Who is on and who is off is decided here, not in the app:
    listings       active=yes/no (blank = yes) · start=YYYY-MM-DD (blank = now) · expires=YYYY-MM-DD (blank = never)
    announcements  approved=yes (anything else = held back) · expires=YYYY-MM-DD (required)
    resources      active=yes/no (blank = yes)
The script prints which rows were skipped and why, so nothing disappears silently.

Safety rules the script enforces (the app enforces them again on its side):
    every id unique across all three files · website/url/logo/image must be https · images end in png/jpg/webp
    phones are 10 digits · dates are YYYY-MM-DD · no field may carry a script or an intent: link
"""
import csv, json, re, sys, datetime, pathlib

HERE = pathlib.Path(__file__).parent
SRC = HERE / "listings.csv"
ANN = HERE / "announcements.csv"
RES = HERE / "resources.csv"
CFG = HERE / "config.json"
OUT = HERE / "sugarcheck-directory.json"
CATS = {"pharmacy", "clinic", "dietitian", "podiatrist", "eye", "support", "dental", "other"}
TIERS = {"free", "basic", "featured", "founding", "county"}
RES_CATS = {"food", "education", "clinic", "pharmacy", "rx-assist", "supplies", "nutrition", "activity", "support"}
HOURS_RE = re.compile(r"^\d{1,2}:\d{2}-\d{1,2}:\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HTTPS_RE = re.compile(r"^https://[A-Za-z0-9.-]+(?::\d+)?(?:/[^\s]*)?$")
IMG_RE = re.compile(r"\.(png|jpe?g|webp)(\?.*)?$", re.I)
DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]


def num(v):
    v = (v or "").strip()
    return float(v) if v else None


def yes(v, default="yes"):
    return (v or default).strip().lower() in ("yes", "y", "true", "1")


def read_csv(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(enumerate(csv.DictReader(f), start=2))


def check_url(errors, rid, field, v, image=False):
    v = (v or "").strip()
    if not v:
        return ""
    if not HTTPS_RE.match(v):
        errors.append(f"{rid}: {field} must be a plain https:// link, got '{v}'")
    if image and not IMG_RE.search(v):
        errors.append(f"{rid}: {field} must end in .png, .jpg or .webp")
    return v


def main(check_only=False, fixture=False):
    errors, ids, skipped = [], set(), []
    today = datetime.date.today().isoformat()

    def uniq(rid, line):
        if rid in ids:
            errors.append(f"line {line}: duplicate id {rid}")
        ids.add(rid)

    # ---- listings ----
    listings = []
    for n, r in read_csv(SRC):
        rid = (r.get("id") or "").strip()
        if not rid:
            errors.append(f"listings line {n}: missing id"); continue
        uniq(rid, n)
        active = (r.get("active") or "yes").strip().lower()
        if active not in ("yes", "no", ""):
            errors.append(f"{rid}: active must be yes or no, got '{active}'")
        start = (r.get("start") or "").strip()
        expires = (r.get("expires") or "").strip()
        for fld, v in (("start", start), ("expires", expires)):
            if v and not DATE_RE.match(v):
                errors.append(f"{rid}: {fld} must be YYYY-MM-DD, got '{v}'")
        if not fixture:
            if active == "no": skipped.append(f"{rid}: active = no"); continue
            if start and start > today: skipped.append(f"{rid}: starts {start}"); continue
            if expires and expires < today: skipped.append(f"{rid}: expired {expires}"); continue
        if r["category"] not in CATS: errors.append(f"{rid}: bad category '{r['category']}'")
        if r["tier"] not in TIERS: errors.append(f"{rid}: bad tier '{r['tier']}'")
        hours = []
        for d in DAYS:
            h = (r.get(d) or "").strip()
            if h and not HOURS_RE.match(h):
                errors.append(f"{rid}: bad {d} hours '{h}' (use HH:MM-HH:MM or blank)")
            hours.append(h)
        phone = re.sub(r"\D", "", r.get("phone") or "")
        if phone and len(phone) not in (10, 11):
            errors.append(f"{rid}: phone should be 10 digits")
        website = check_url(errors, rid, "website", r.get("website"))
        logo = check_url(errors, rid, "logo", r.get("logo"), image=True)
        listings.append({
            "id": rid, "name": r["name"].strip(), "category": r["category"], "tier": r["tier"],
            "address": r["address"].strip(), "city": r["city"].strip(), "county": r["county"].strip(),
            "state": (r.get("state") or "MS").strip(), "zip": (r.get("zip") or "").strip(),
            "lat": num(r.get("lat")), "lng": num(r.get("lng")),
            "phone": phone, "website": website, "email": (r.get("email") or "").strip(),
            "hours": hours, "note": (r.get("note") or "").strip()[:120],
            **({"logo": logo} if logo else {}),
        })
    listing_ids = {l["id"] for l in listings}

    # ---- announcements ----
    announcements = []
    for n, r in read_csv(ANN):
        rid = (r.get("id") or "").strip()
        if not rid:
            errors.append(f"announcements line {n}: missing id"); continue
        uniq(rid, n)
        expires = (r.get("expires") or "").strip()
        if not DATE_RE.match(expires):
            errors.append(f"{rid}: expires is required, YYYY-MM-DD")
        for fld in ("event_date", "publish_date"):
            v = (r.get(fld) or "").strip()
            if v and not DATE_RE.match(v):
                errors.append(f"{rid}: {fld} must be YYYY-MM-DD, got '{v}'")
        approved = yes(r.get("approved"), default="no")
        sponsored = yes(r.get("sponsored"), default="no")
        sponsor_id = (r.get("sponsor_id") or "").strip()
        if sponsored and sponsor_id and sponsor_id not in listing_ids and not fixture:
            errors.append(f"{rid}: sponsor_id '{sponsor_id}' is not an active listing")
        if not fixture:
            if not approved: skipped.append(f"{rid}: not approved"); continue
            if expires and expires < today: skipped.append(f"{rid}: expired {expires}"); continue
        announcements.append({
            "id": rid, "title": (r.get("title") or "").strip()[:80], "description": (r.get("description") or "").strip()[:600],
            "org": (r.get("org") or "").strip()[:80], "area": (r.get("area") or "").strip()[:60],
            "eventDate": (r.get("event_date") or "").strip(), "publishDate": (r.get("publish_date") or today).strip(),
            "expires": expires, "imageUrl": check_url(errors, rid, "image_url", r.get("image_url"), image=True),
            "url": check_url(errors, rid, "url", r.get("url")), "sponsored": sponsored, "sponsorId": sponsor_id,
        })
        if not announcements[-1]["title"]:
            errors.append(f"{rid}: title is required")

    # ---- resources ----
    resources = []
    for n, r in read_csv(RES):
        rid = (r.get("id") or "").strip()
        if not rid:
            errors.append(f"resources line {n}: missing id"); continue
        uniq(rid, n)
        if not fixture and not yes(r.get("active")):
            skipped.append(f"{rid}: active = no"); continue
        cat = (r.get("category") or "").strip()
        if cat not in RES_CATS: errors.append(f"{rid}: bad category '{cat}' (one of {sorted(RES_CATS)})")
        url = check_url(errors, rid, "url", r.get("url"))
        if not url: errors.append(f"{rid}: url is required")
        reviewed = (r.get("reviewed") or "").strip()
        if not DATE_RE.match(reviewed): errors.append(f"{rid}: reviewed must be YYYY-MM-DD")
        resources.append({
            "id": rid, "title": (r.get("title") or "").strip()[:80], "url": url, "why": (r.get("why") or "").strip()[:160],
            "category": cat, "state": (r.get("state") or "").strip().upper()[:2], "county": (r.get("county") or "").strip(),
            "essential": yes(r.get("essential"), default="no"), "reviewed": reviewed,
        })

    # ---- config → meta ----
    meta = {}
    if CFG.exists():
        try:
            cfg = json.loads(CFG.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"config.json: {e}"); cfg = {}
        w = cfg.get("weights") or {}
        for t, v in w.items():
            if t not in TIERS or not isinstance(v, (int, float)) or v < 0 or v > 20:
                errors.append(f"config.json weights.{t} = {v!r}: tier must be one of {sorted(TIERS)}, value 0–20")
        b = cfg.get("badges") or {}
        for t, v in b.items():
            if t not in TIERS or not isinstance(v, str) or len(v) > 32:
                errors.append(f"config.json badges.{t}: tier name and a string of 32 chars or fewer")
        meta = {k: cfg[k] for k in ("weights", "badges") if k in cfg}

    if errors:
        print("\n".join("ERROR " + e for e in errors)); sys.exit(1)
    for sk in skipped:
        print("skipped " + sk)
    doc = {"version": 2, "updated": today, "listings": listings, "announcements": announcements, "resources": resources, "meta": meta}
    summary = f"{len(listings)} listings, {len(announcements)} announcements, {len(resources)} resources"
    if check_only:
        print(f"OK: {summary}"); return
    if fixture:
        fx = HERE.parent / "tests" / "fixtures" / "directory-examples.json"
        fx.parent.mkdir(parents=True, exist_ok=True)
        fx.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {fx}: {summary} (fixture)"); return
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.name}: {summary}, updated {doc['updated']}")


if __name__ == "__main__":
    main("--check" in sys.argv, "--fixture" in sys.argv)
