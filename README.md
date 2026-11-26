# rosmarops-web

Static pages of rosmarops.com that live outside WordPress: the English home (`/`), the Spanish home (`/es/`) and `llms.txt`.

- Edit files under `site/`. A push to `main` starts the deploy workflow, which waits for Albert's approval in the `production` environment and then uploads only those three files to OVH over SFTP. Nothing else on the server is changed or deleted.
- Every public sentence is verified by the product advisor before it lands here.
- The blogs (`/blog/`, `/es/blog/`) are WordPress and are not managed from this repo.

## The site's own counters (`wp/mu-plugins/rosmarops-downloads.php`)

What the server keeps, with no IP address, cookie, browser data or identifier (the privacy policy in `site/privacy/`, `site/es/privacidad/` and `site/ca/privadesa/` says the same to visitors):

- **Download clicks:** one count per UTC day, source page, language and system (`rosmarops_downloads`). Kept with no time limit. Public at `/wp-json/rosmarops/v1/downloads` (last 400 days). Clicks from robots, the team, and prefetch or prerender requests (`Sec-Purpose`, `Purpose` or `X-Moz`) are redirected but not counted.
  - **People who download (GTM-200):** each row also has `people`. A counted click adds one to it when the visitor's fingerprint of the day (the same one as the visit counter) already has a visit counted today and no click counted today. A click with no visit before it counts as a click, not a person. The fingerprints of today's clicks are kept in `rosmarops_download_prints` (one column), which is emptied at the same day change as the visit fingerprints. The days before the change carry `people: 0`.
- **Visits:** one count per UTC day, page, language, kind of referrer and channel (`rosmarops_visits`), and different people per UTC day, language, kind of referrer and channel (`rosmarops_people`, from a fingerprint that only exists that day). Kept with no time limit. Public at `/wp-json/rosmarops/v1/visits` (last 400 days).
  - **Channel, `via` (GTM-220):** which channel a shared link came through, when the link says so. Add `?via=` to a page address you share: `li` (LinkedIn), `x`, `yt` (YouTube), `mail`, `wa` (WhatsApp), `hn` (Hacker News), `reddit`, `lobsters`, `awesome` (an awesome list) or `qtorb` (qtorb.com), for example `https://rosmarops.com/?via=hn`. Without `via`, the page reads `utm_source=` instead, with the same values. Upper case is fine. Any other value is kept as `other`, and an address with neither as an empty `via`. It is a column of its own: the kind of referrer is kept as before. A person counts with the channel of their first visit of the day. Rows and people from before the change have `via` empty; the first visit or read after the change adds the column to the two tables. Download clicks do not keep the channel: see vigil `docs/research/2026-11-26-gtm-captacion-propuesta.md` and the GTM-220 PR.
- **Hourly totals (GTM-186):** one total per UTC hour for visits and one for download clicks (`rosmarops_hourly`: the hour, `visit` or `download`, and the count; no page, language, referrer, system or anything about the person). Every visit and click counted above also adds one here. Rows older than 48 hours are deleted when a count is written and when the totals are read; there is no scheduled job for it. Public at `/wp-json/rosmarops/v1/hours`: the last 48 hours, oldest first, `[{"hour": "2026-11-19T10:00:00Z", "visits": n, "downloads": n}, …]`, with an hour at 0 when nothing was counted, and `Cache-Control: max-age=60`.

Tests: `wp/tests/test_downloads.py`, `test_visits.py`, `test_hourly.py` and `test_download_people.py` (see `wp/tests/README.md`).

## The glossary (`tools/glossary/`)

The glossary pages (`/glossary/`, `/es/glosario/`, `/ca/glossari/`), the «i» help next to terms and `site/assets/help/glossary.json` all come from one file, `tools/glossary/terms.json`. To add or change a term, edit that file with the signed texts and run `python3 tools/glossary/build.py` by hand, then commit what it changes under `site/`.

- Each term is listed under its `id`. A term can carry `anchors` with its own address per language (for example `#huella-de-una-clave` in Spanish); without it, the address is the `id` in every language.
- The «i» next to a term on a page links to that same address (GTM-206: before, it always used the `id`, so in Spanish and Catalan it could point to a place that does not exist on the page).
- Tests: `tools/glossary/test_build.py` checks that the «i» uses the term's own address, and that every glossary link on the site points to an address that exists.

## The course (`observatory/course_pages.py`)

Lesson 2 of the public course, «The chain», lives at `/course/the-chain/`, `/es/curso/la-cadena/` and `/ca/curs/la-cadena/` (GTM-206).

- Its texts are in `observatory/data/course/the-chain.json`, copied literally from the signed documents in rosmarops-vigil (see the file's `_source`). Change the signed document first, then this file. `**x**` is bold and `` `x` `` is code. To check that every text is still literal, run `python3 tools/course/check_signed.py <path to a copy of rosmarops-vigil>` by hand (CI cannot read that repository); the footer is checked against `docs/briefs/GTM-215.md`, the eight retouches of `docs/briefs/GTM-217.md` (listed in `RETOUCHES` in the script) against that brief, and the rest against the two lesson documents.
- `observatory/build.py` writes the three pages (or run `python3 observatory/course_pages.py`). Their styles and script are `site/assets/course/chain.css` and `chain.js`, which read the texts from the page itself.
- What a visitor does in the lesson (the permissions they try, their answers in the game and the test) stays in the page: nothing goes into the address, the browser's storage or cookies, and nothing is sent. The page still counts a visit like every page of the site.
- The download button in the exercise sends `from=course`, which the counter keeps as its own source, `course`.
- Not open yet: the pages carry `noindex`, no page or menu links to them, and they are not in the sitemap or `llms.txt`. The deploy fails if the `noindex` goes missing. Opening them is Albert's decision.
- Tests: `observatory/tests/test_course_pages.py`. Captures of this version: `docs/captures/gtm-206-leccion-2/`.

## The GitHub star card (`observatory/star_card.py`)

After a click on a download button, a small card appears under that block: «Thanks for trying it. If you find it useful, a star on GitHub helps others find it.» with a button to https://github.com/qtorb/rosmarops (GTM-206; texts in EN, ES and CA in `star_card.py`, signed by Albert). No star count, no GitHub badge or icon from outside, nothing stored in the browser and nothing sent. Without JavaScript it never appears.

- Pages that take part: the homes (both download blocks), the macOS and Linux pages, the Observatory agent pages, the map, the Sandbox section and the course lesson, in the three languages. Not the FAQ (its download links are inside an answer) or the topic and video pages (a plain link in a list).
- A download block takes part when it carries `data-star-block` (on the map, the whole call-to-action row `.m-cta`, so the card goes under the row; `data-star-block="inside"` would put it inside the block, and no page uses it today). Each page then has one hidden card, `site/assets/star/star.css` and `star.js`; the script moves the card under the block that was clicked and shows it, once per visit to the page.
- Generated pages get it from the generators. For the hand-written pages (homes, macOS, Linux), run `python3 observatory/star_card.py` after editing them; the tests fail if one is missing it.
- Tests: `observatory/tests/test_star_card.py`. Before and after captures: `docs/captures/gtm-206-estrella/`.

## Ownership files at the root of the site

Two files at the root of `site/` prove to search engines that the site is ours. They are not linked from any page, are not in the sitemap, carry no script and are not counted as visits. Each has its own `put` line in `.github/workflows/deploy.yml`. Do not delete them: the search engines check them again.

- `google5cd09a19ba35efb6.html`: verification of the property https://rosmarops.com/ in Google Search Console (GTM-116, 23-11-2026). Its whole content is the line `google-site-verification: google5cd09a19ba35efb6.html`.
- `24a8c2078ff9b0ee590acf6cd5901e32.txt`: the IndexNow key, used by `wp/mu-plugins/rosmarops-seo.php`.
