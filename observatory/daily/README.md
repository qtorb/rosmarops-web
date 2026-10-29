# Daily synopsis files (GTM-23)

One file per day, `AAAA-MM-DD.json`, written by the daily review task after checking the rules signed in GTM-22.
Schema: `observatory/schema/daily.v1.schema.json`. Mechanical checks: `python3 observatory/daily_check.py <file>`.

Pushing a file here does not deploy anything: `.github/workflows/daily.yml` checks it and, if something was held,
the review was incomplete or the file is invalid, emails Albert. The `rosmarops-daily` mu-plugin on rosmarops.com
fetches the file from this public repository every hour, validates it again and renders the pages.

Never put HTML, scripts or anything other than these JSON files in this folder.
