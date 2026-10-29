# Tests for the WordPress mu-plugins (not deployed)

`rosmarops-downloads.php` against a real MySQL/MariaDB with a minimal WordPress stand-in:

    mysql -e "CREATE DATABASE wptest"
    DB_USER=… DB_PASS=… php -S 127.0.0.1:8899 wp/tests/router.php
    curl -sI "http://127.0.0.1:8899/download?from=home"        # 302 to the latest release, Cache-Control: no-store
    curl -s  "http://127.0.0.1:8899/wp-json/rosmarops/v1/downloads"

The REST part of the stand-in only mimics WordPress routing (GET registered, anything else 404); the real check is the post-deploy step in deploy.yml.

`rosmarops-daily.php` (GTM-23), with its own stand-in (`daily-stub.php`, network options in a JSON file) and `php -S`:

    python3 -m unittest wp/tests/test_daily.py
