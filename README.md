# rosmarops-web

Static pages of rosmarops.com that live outside WordPress: the English home (`/`), the Spanish home (`/es/`) and `llms.txt`.

- Edit files under `site/`. A push to `main` starts the deploy workflow, which waits for Albert's approval in the `production` environment and then uploads only those three files to OVH over SFTP. Nothing else on the server is changed or deleted.
- Every public sentence is verified by the product advisor before it lands here.
- The blogs (`/blog/`, `/es/blog/`) are WordPress and are not managed from this repo.

## The site's own counters (`wp/mu-plugins/rosmarops-downloads.php`)

What the server keeps, with no IP address, cookie, browser data or identifier (the privacy policy in `site/privacy/`, `site/es/privacidad/` and `site/ca/privadesa/` says the same to visitors):

- **Download clicks:** one count per UTC day, source page, language and system (`rosmarops_downloads`). Kept with no time limit. Public at `/wp-json/rosmarops/v1/downloads` (last 400 days). Clicks from robots, the team, and prefetch or prerender requests (`Sec-Purpose`, `Purpose` or `X-Moz`) are redirected but not counted.
  - **People who download (GTM-200):** each row also has `people`. A counted click adds one to it when the visitor's fingerprint of the day (the same one as the visit counter) already has a visit counted today and no click counted today. A click with no visit before it counts as a click, not a person. The fingerprints of today's clicks are kept in `rosmarops_download_prints` (one column), which is emptied at the same day change as the visit fingerprints. The days before the change carry `people: 0`.
- **Visits:** one count per UTC day, page, language and kind of referrer (`rosmarops_visits`), and different people per UTC day, language and kind of referrer (`rosmarops_people`, from a fingerprint that only exists that day). Kept with no time limit. Public at `/wp-json/rosmarops/v1/visits` (last 400 days).
- **Hourly totals (GTM-186):** one total per UTC hour for visits and one for download clicks (`rosmarops_hourly`: the hour, `visit` or `download`, and the count; no page, language, referrer, system or anything about the person). Every visit and click counted above also adds one here. Rows older than 48 hours are deleted when a count is written and when the totals are read; there is no scheduled job for it. Public at `/wp-json/rosmarops/v1/hours`: the last 48 hours, oldest first, `[{"hour": "2026-11-19T10:00:00Z", "visits": n, "downloads": n}, …]`, with an hour at 0 when nothing was counted, and `Cache-Control: max-age=60`.

Tests: `wp/tests/test_downloads.py`, `test_visits.py`, `test_hourly.py` and `test_download_people.py` (see `wp/tests/README.md`).

## Ownership files at the root of the site

Two files at the root of `site/` prove to search engines that the site is ours. They are not linked from any page, are not in the sitemap, carry no script and are not counted as visits. Each has its own `put` line in `.github/workflows/deploy.yml`. Do not delete them: the search engines check them again.

- `google5cd09a19ba35efb6.html`: verification of the property https://rosmarops.com/ in Google Search Console (GTM-116, 23-11-2026). Its whole content is the line `google-site-verification: google5cd09a19ba35efb6.html`.
- `24a8c2078ff9b0ee590acf6cd5901e32.txt`: the IndexNow key, used by `wp/mu-plugins/rosmarops-seo.php`.
