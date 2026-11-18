# Tests for the WordPress mu-plugins (not deployed)

`rosmarops-downloads.php` against a real MySQL/MariaDB with a minimal WordPress stand-in:

    mysql -e "CREATE DATABASE wptest"
    DB_USER=… DB_PASS=… php -S 127.0.0.1:8899 wp/tests/router.php
    curl -sI "http://127.0.0.1:8899/download?from=home"        # 302 to the latest release, Cache-Control: no-store
    curl -s  "http://127.0.0.1:8899/wp-json/rosmarops/v1/downloads"

The same with migration from the table before the os column, targets per ?os= and HEAD not counted:

    DB_USER=… DB_PASS=… DB_NAME=wptest python3 -m unittest wp/tests/test_downloads.py

The REST part of the stand-in only mimics WordPress routing (GET registered, anything else 404); the real check is the post-deploy step in deploy.yml.

`rosmarops-daily.php` (GTM-23), with its own stand-in (`daily-stub.php`, network options in a JSON file) and `php -S`:

    python3 -m unittest wp/tests/test_daily.py

`rosmarops-gtm181-promesa.php` (GTM-181, the 0.15.0 promise in WordPress: the program's privacy policy in EN, ES and a new CA page, a dated line at the start of 14 posts, and four pages the static site already serves set to draft), with its own stand-in (`gtm181-stub.php`):

    python3 -m unittest wp/tests/test_gtm181_promesa.py
