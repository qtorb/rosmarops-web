# Tests for the WordPress mu-plugins (not deployed)

`rosmarops-downloads.php` against a real MySQL/MariaDB with a minimal WordPress stand-in:

    mysql -e "CREATE DATABASE wptest"
    DB_USER=… DB_PASS=… php -S 127.0.0.1:8899 wp/tests/router.php
    curl -sI "http://127.0.0.1:8899/download?from=home"        # 302 to the latest release, Cache-Control: no-store
    curl -s  "http://127.0.0.1:8899/wp-json/rosmarops/v1/downloads"

The same with migration from the table before the os column, targets per ?os= and HEAD not counted:

    DB_USER=… DB_PASS=… DB_NAME=wptest python3 -m unittest wp/tests/test_downloads.py

People who download (GTM-200): a click after a visit the same day is one person, the second click is not, a click with no visit is a click and not a person, robots and prefetches add nothing, the download fingerprints are emptied at the day change, and `people` comes out in the endpoint:

    DB_USER=… DB_PASS=… DB_NAME=wptest python3 -m unittest wp/tests/test_download_people.py

The REST part of the stand-in only mimics WordPress routing (GET registered, anything else 404); the real check is the post-deploy step in deploy.yml.

`rosmarops-daily.php` (GTM-23), with its own stand-in (`daily-stub.php`, network options in a JSON file) and `php -S`:

    python3 -m unittest wp/tests/test_daily.py

`rosmarops-gtm181-promesa.php` (GTM-181, the 0.15.0 promise in WordPress: the program's privacy policy in EN, ES and a new CA page, a dated line at the start of 14 posts, and four pages the static site already serves set to draft), with its own stand-in (`gtm181-stub.php`):

    python3 -m unittest wp/tests/test_gtm181_promesa.py

The hourly totals (GTM-186: `rosmarops_hourly` and `/wp-json/rosmarops/v1/hours`), with the same stand-in, «now» fixed by `HOURLY_NOW`; the privacy policy paragraphs are checked without a database:

    DB_USER=… DB_PASS=… DB_NAME=wptest python3 -m unittest wp/tests/test_hourly.py

`rosmarops-gtm195-voz.php` (GTM-195, one time per site: puts the worktree post in Albert's voice, from `wp/drafts/worktree-<lang>.json` and `.html`, into the drafts EN 1262, ES 1252 and CA 105, only while they are drafts; the deploy removes it from the server after reading its logs), with its own stand-in (`gtm195-stub.php`):

    python3 -m unittest wp/tests/test_gtm195_voz.py
