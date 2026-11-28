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

The public course has two lessons built (GTM-206, GTM-227), each in six steps: before you start, the idea, try it, check it (a game and a test), on your computer, and what you take away.

- Lesson 1, «The inspector»: `/course/the-inspector/`, `/es/curso/el-inspector/`, `/ca/curs/linspector/`. Its piece «Who decides?» shows the same agent (Claude Code) in three modes, Manual, Auto and Bypass permissions, and who gives permission for four actions in each.
- Lesson 2, «The chain»: `/course/the-chain/`, `/es/curso/la-cadena/`, `/ca/curs/la-cadena/`. Its piece is «Break the chain».
- The course has no entry page of its own (GTM-230): the RosmarOps Academy page presents it (see the next section). Nothing is written at `/course/`, `/es/curso/` or `/ca/curs/`.
- Texts: `observatory/data/course/the-inspector.json` and `the-chain.json`, copied literally from the signed documents in rosmarops-vigil (see each file's `_source`). Change the signed document first, then these files. `**x**` is bold and `` `x` `` is code. In English pages the quotes are “ ” (the build stops on a « »). To check that every text is still literal, run `python3 tools/course/check_signed.py <path to a copy of rosmarops-vigil>` by hand (CI cannot read that repository). It compares every text with `docs/research/2026-11-26-curso-publico-textos-finales.md` (and the design document for the step list label), and keeps the retouches of `docs/briefs/GTM-217.md` and the two sentences corrected in GTM-219.
- `observatory/build.py` writes the pages (or run `python3 observatory/course_pages.py`). Their styles and script are `site/assets/course/chain.css` and `chain.js`, which read the texts from the page itself.
- What a visitor does in a lesson (the mode or permissions they try, their answers in the game and the test) stays in the page: nothing goes into the address, the browser's storage or cookies, and nothing is sent. The page still counts a visit like every page of the site.
- The download buttons in step 5 send `from=course`, which the counter keeps as its own source, `course`. In lesson 1, step 5 also links to the sample report of each language.
- Open since 27-11-2026, with RosmarOps Academy (next section): the Academy page links to them, they are in `sitemap-pages.xml` without `noindex`, and they end with «Back to Academy». No other page links to them, and they are not in `llms.txt`. If Academy is closed again, they go back to `noindex`, out of the sitemap, and linked only from lesson 1 to lesson 2.
- Tests: `observatory/tests/test_course_pages.py`. Captures: `docs/captures/gtm-206-leccion-2/` and `docs/captures/gtm-227-curso/`.

## RosmarOps Academy (`observatory/academy.py`)

RosmarOps Academy gathers the course and the videos (GTM-230). Its page is `/academy/`, `/es/academy/` and `/ca/academy/`, and «Academy» goes in the header menu. Everything is behind **one switch**: `"open"` in `observatory/data/academy.json`.

- **Closed** (until 27-11-2026): no Academy page is written, every menu is the one of before, the two lessons keep `noindex`, stay out of the sitemap and show no «Back to Academy» button, and the blog menu is not touched.
- **Open** (since 27-11-2026, Albert's decision, GTM-234): the page exists; «Academy» is in every header menu, marked as the current entry on the Academy page and the lessons; the page and the lessons are in `sitemap-pages.xml` and lose `noindex`; lesson 2 ends with the «Back to Academy» button, and lesson 1 keeps «Next: Lesson 2» with «Back to Academy» as a text link under it; and the next deploy adds «Academy» to the three blog menus.
- **To open it** (Albert's decision): set `"open": true`, run `python3 observatory/site_check.py --stage`, commit and deploy. Closing it again is the same with `false`: the build puts every menu back as it was. The blog menu is the exception: the patch runs once and is then removed from the server, so closing does not take «Academy» out of the blog menu; that has to be done by hand in WordPress.
- **The menu**: «Academy» goes right after «Sandbox». On inner pages it takes the place of «FAQ»/«Preguntas»/«Preguntes», which stays in the footer. On the homes and the blog it is added. Only the header menu changes. The five places the menu comes from all follow the switch:
  - the hand-written pages and the glossary: the build rewrites their header menu in place;
  - the Observatory pages and the daily shells: `build.page()`;
  - the Sandbox section, topic, video and course pages: through the guide's header;
  - the static About pages;
  - the blog: `wp/mu-plugins/rosmarops-menu10-academy.php`. Its `ROSMAROPS_MENU10_OPEN` line is written by the build from the switch. It acts once per site and only on the blog menu as it was on 27-11; the deploy reads its logs and removes it.
- **Texts**: `observatory/data/academy.json`, literal from vigil `docs/research/2026-11-27-academy-portada-y-menu.md` (the painter paragraph and the five lesson lines from the course's final texts). `tools/course/check_signed.py` checks them too. The video cards are the ones of the videos index (`videos_pages.cards`).
- **Checks**:
  - the deploy runs `python3 observatory/academy.py --check-site` and stops if `site/` does not match the switch;
  - `observatory/tests/test_academy.py` tests both states in memory, whichever state the repository is in, and checks that the committed site is the one the switch gives. It also checks that every inner page and every home has the same header menu, hand-written or generated;
  - the menu at 390 px (`Layout390`, in Chromium with `observatory/tests/academy-nav-layout.js`, spec §6.2 and block 219). At 390 px the visitor is on a phone, so the test measures the menu with «Academy» with fonts a phone would use, asked for by name: **Liberation Sans** (the metrics of Windows' Arial) and **Roboto** (Android). With both it must stay on **two lines**, in EN, ES and CA, on an inner page, a home and an Observatory page. Chromium's default font is not measured: it is not a named font and depends on the machine (on the CI runner it is DejaVu Sans). **DejaVu Sans** (desktop Linux) is measured too, pinned to what was measured on 27-11 so it does not get worse: Spanish inner page and home up to three lines, everything else two. CI installs the fonts as system packages (`fonts-roboto`, `fonts-liberation`, `fonts-dejavu-core`); no font file is in the repository;
  - `wp/tests/test_menu10_academy.py` tests the blog patch, closed and open;
  - captures with the switch open: `docs/captures/gtm-230-academy/`.

## The GitHub star card (`observatory/star_card.py`)

After a click on a download button, a small card appears under that block: «Thanks for trying it. If you find it useful, a star on GitHub helps others find it.» with a button to https://github.com/qtorb/rosmarops (GTM-206; texts in EN, ES and CA in `star_card.py`, signed by Albert). No star count, no GitHub badge or icon from outside, nothing stored in the browser and nothing sent. Without JavaScript it never appears.

- Pages that take part: the homes (both download blocks), the macOS and Linux pages, the Observatory agent pages, the map, the Sandbox section and the course lesson, in the three languages. Not the FAQ (its download links are inside an answer) or the topic and video pages (a plain link in a list).
- A download block takes part when it carries `data-star-block` (on the map, the whole call-to-action row `.m-cta`, so the card goes under the row; `data-star-block="inside"` would put it inside the block, and no page uses it today). Each page then has one hidden card, `site/assets/star/star.css` and `star.js`; the script moves the card under the block that was clicked and shows it, once per visit to the page.
- Generated pages get it from the generators. For the hand-written pages (homes, macOS, Linux), run `python3 observatory/star_card.py` after editing them; the tests fail if one is missing it.
- Tests: `observatory/tests/test_star_card.py`. Before and after captures: `docs/captures/gtm-206-estrella/`.

## The Control Baseline (`observatory/minimum.py`)

The RosmarOps Control Baseline: seven yes-or-no criteria about a product that puts AI agents to work, and one result per product measured against them (GTM-223; specification in vigil `docs/research/2026-11-26-minimo-de-control-pagina-publica.md`, texts signed by Albert on 26-11).

- **Results:** `observatory/data/minimum/<id>/<measured_at>.json`, one file per measurement, never deleted. `<id>` is the result's `candidate.id`; a product measured in two ways of use has two ids (`n8n` and `n8n-cloud`). Each file must be valid against `observatory/schema/minim-result.v2.schema.json`, an unchanged copy of the schema in vigil `docs/research/minim/schema/` (checked in CI), and follow the rules the schema does not cover, which `observatory/minimum.py` checks and the build stops on: the folder and the file name, M1 to M7 in order, F1 yes or no and F2 `user_machine` or `vendor_cloud`, M2 not applicable exactly when F1 is no and M3 exactly when F2 is `vendor_cloud`, `total`, `met` and `passes` counted from the criteria, `publish_after` at least 14 days after `notified_at`, `expires_at` 90 days after `measured_at`, and what the page needs to say it (`tested_version` when installed by whoever uses it, `tested_plan` in the vendor's cloud, never `how: none`). `tested_plan` holds only the name of a plan. When the vendor has no named plan we can cite, it is empty, and the page says «In the vendor's cloud» with no plan (`use.cloud.noplan` and `x.meta.cloud.noplan`, vigil `docs/research/2026-11-27-minimo-de-control-fichas-de-familia.md` §5).
- **When a result is published:** only from its `vendor.publish_after` on, compared with the day of the build (UTC; `--today YYYY-MM-DD` to try another day). A result waiting for its date is not copied, has no page and is not counted anywhere. A result appears with the first site build committed to main and deployed on or after that day. Nothing does that on its own: the daily writer only rebuilds the site on a day it changed an agent file.
- **Publication days:** the results in the data today are published on two days, with the same steps:
  - **10-12-2026:** Paperclip, n8n, n8n (Cloud), Gumloop and Dify (cloud), measured on 25-11 (GTM-225).
  - **11-12-2026:** Microsoft Copilot Autopilot and Meta Muse, measured on 27-11, in «Agents on the vendor's computer» (GTM-233).
  - The steps, on each of those days:
    1. Rebuild the site: `python3 observatory/site_check.py --stage`.
    2. Put it on main in a pull request: the advisor reviews it and Albert merges it. A push made by a GitHub workflow with its own token does not start the deploy.
    3. Albert approves the deploy (`deploy.yml`, `production` environment).
  - From each of those days until the rebuilt site is on main, the «Generated pages are up to date» check fails on every pull request.
- **What the build writes:** in `site/observatory/minimum/`, every published result as it is on disk, `latest.json` of each id (a copy of its most recent published file) and the schema; the criterion page at `/observatory/control-baseline/`, `/es/observatorio/minimo-de-control/` and `/ca/observatori/minim-de-control/`, published even with no results; one page per id with a published result under those paths (`…/<id>/`), with its history; both in the sitemap. On the Observatory index, the row of a product with a published result gets one more line linking to it (`row.line`, or `row.line.use` with «installed» or «cloud» when it has two results). A result belongs to the product with the same id, or with the id without `-cloud` at the end. Products with no row (the «other companies» line) do not change.
- **Families** (GTM-232; specification in vigil `docs/research/2026-11-27-minimo-de-control-fichas-de-familia.md`, texts signed by Albert on 27-11):
  - The families are listed in `observatory/data/minimum-families.json`, each with:
    - the `kind` values it groups;
    - its address in each language, one folder under the criterion page;
    - its own texts in the three languages.
  - Today there are two:
    - «Orchestrators and automation»: `orchestrator`, `workflow_automation` and `agent_builder`;
    - «Agents on the vendor's computer»: `hosted_agent`, a value of the schema's `kind` since 27-11.
  - `agent_framework` has no family.
  - Each family has its own page in the three languages, published even with no results and in the sitemap. It shows only the published results whose `kind` is in the family, with the same table as the criterion page, so a result waiting for its `publish_after` is not on any family page either.
  - The criterion page lists the families in its «Families» block, and a result page's breadcrumbs go Observatory › Control Baseline › family › product.
  - The build stops if two families share a `kind` or an address, or if a family's folder is the `candidate.id` of a result on disk. A family and a product never share an address.
  - Adding a family is adding it to the data file with its signed texts; adding a product to a family is giving its result that `kind`.
- **Texts:** all in `observatory/i18n/{en,es,ca}.json` under `minimum.` (the family pages' common headings under `minimum.family.`), literal from the specification (English quotes as “ ”). The contact address in «If you are the vendor» is `MIN_CONTACT` in `observatory/build.py`, shown as plain text. The criteria version on the criterion page is `CRITERIA_VERSION` in `observatory/minimum.py` (4).
- **Deploy:** `deploy.yml` uploads `site/observatory/minimum/` with its subfolders, and the pages with the other published Observatory pages; after deploying it checks the three criterion pages and the schema.
- **Tests:** `observatory/tests/test_minimum.py`, with test results in `observatory/tests/fixture/minimum/` (invented products, never published). Captures: in the GTM-223 pull request.

## Ownership files at the root of the site

Two files at the root of `site/` prove to search engines that the site is ours. They are not linked from any page, are not in the sitemap, carry no script and are not counted as visits. Each has its own `put` line in `.github/workflows/deploy.yml`. Do not delete them: the search engines check them again.

- `google5cd09a19ba35efb6.html`: verification of the property https://rosmarops.com/ in Google Search Console (GTM-116, 23-11-2026). Its whole content is the line `google-site-verification: google5cd09a19ba35efb6.html`.
- `24a8c2078ff9b0ee590acf6cd5901e32.txt`: the IndexNow key, used by `wp/mu-plugins/rosmarops-seo.php`.
