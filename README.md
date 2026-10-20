# SugarCheck directory data

1. Edit `listings.csv` in Excel or Google Sheets. One row per business. Keep the header row.
   - `category`: pharmacy · clinic · dietitian · podiatrist · eye · support · dental · other
   - `tier`: free · basic · featured  (featured sorts first and shows the note + logo)
   - hours columns: `08:30-17:30` 24-hour, blank = closed that day
   - `lat`/`lng`: paste from Google Maps (right-click the pin → copy coordinates). Blank is fine; the app falls back to the address for directions and sorts by name.
   - `phone`: digits only
2. `python build.py --check` to validate, then `python build.py` to write `sugarcheck-directory.json`.
3. Upload the JSON to the URL set in `lib/directory.ts` → `DIRECTORY_URL`. WordPress: Media → Add New (allow .json in settings, or host on GitHub Pages).
4. Phones pick up the change within 24 hours, or immediately on pull-to-refresh.

No build or app-store update is needed to change listings.


## The other two files (0.4.16)

`build.py` reads up to three CSVs and `config.json`, and writes **one** JSON. Only `listings.csv` is required.

### `announcements.csv` — What's happening

| column | meaning |
| --- | --- |
| `id` | unique across all three files, lowercase-with-dashes |
| `title`, `description` | plain words; title ≤ 80 chars, description ≤ 600 |
| `org`, `area` | who is running it; "Clarke County", "Meridian", "Statewide" |
| `event_date` | YYYY-MM-DD, or blank for a standing notice |
| `publish_date` | YYYY-MM-DD (defaults to the build date) |
| `expires` | **required**, YYYY-MM-DD — the row disappears the day after |
| `image_url` | https, ending .png/.jpg/.webp, or blank |
| `url` | https or blank |
| `sponsored` | yes/no — yes shows a "Sponsored" label |
| `sponsor_id` | the sponsor's `id` from listings.csv when sponsored |
| `approved` | **yes** or it is held back. eHUT sets this after reading the row |

Submissions arrive by email (the app's "Send it to us" link). Paste into the CSV with `approved=no`, read it, set `yes`, run the script.

### `resources.csv` — Find help

| column | meaning |
| --- | --- |
| `id` | unique across all three files |
| `title`, `why` | title ≤ 80; `why` is one plain line, no advice ("you should…" fails review) |
| `url` | https, required |
| `category` | one of `food`, `education`, `clinic`, `pharmacy`, `rx-assist`, `supplies`, `nutrition`, `activity`, `support` |
| `state` | `MS`, `AL`, … or blank for national |
| `county` | blank for statewide/national |
| `essential` | yes/no — yes always sorts first (food, clinics, prescription help) |
| `reviewed` | YYYY-MM-DD, the day someone last checked the link |
| `active` | yes/no |

Nobody pays to be in this file, ever. Paid listings are `listings.csv`; the two never mix.

### `config.json`

```json
{ "weights": { "county": 6, "featured": 3, "founding": 1, "basic": 1, "free": 0 },
  "badges":  { "basic": "Community Supporter", "featured": "Featured Supporter", "county": "Community Impact Partner", "founding": "Founding Sponsor" } }
```

Weights 0–20; badges ≤ 32 characters. `free` is forced to 0 by the app whatever this says. Change a number here, rebuild, commit — no app release needed.

### What the script refuses

Duplicate ids across files · any link that isn't plain `https://` (no http, javascript:, intent:) · logos and images that aren't png/jpg/webp · phones that aren't 10 digits · dates not in YYYY-MM-DD · a sponsored announcement whose `sponsor_id` isn't an active listing · weights outside 0–20. It prints every row it skipped and why, so nothing disappears silently.
