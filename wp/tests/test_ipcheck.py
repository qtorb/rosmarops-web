"""Tests for the temporary IP check of GTM-125 in wp/mu-plugins/rosmarops-downloads.php (removed after the test).

Run from the repository root:  python3 -m unittest wp/tests/test_ipcheck.py   (needs php on PATH)
"""

import json
import subprocess
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
PLUGIN = TESTS.parent / "mu-plugins" / "rosmarops-downloads.php"
TOKEN = "ab" * 32  # test-only value; the real token lives only in a GitHub secret and on the server
SERVER = {"REMOTE_ADDR": "198.51.100.4", "HTTP_X_FORWARDED_FOR": "203.0.113.7, 198.51.100.4", "HTTP_USER_AGENT": "Firefox"}


def answer(k, token, server=SERVER):
    code = ("require %s; require %s; echo json_encode(rosmarops_ipcheck_answer(json_decode($argv[1]), json_decode($argv[2], true), json_decode($argv[3])));"
            % (json.dumps(str(TESTS / "wp-stub-min.php")), json.dumps(str(PLUGIN))))
    p = subprocess.run(["php", "-r", code, json.dumps(k), json.dumps(server), json.dumps(token)], capture_output=True, text=True, check=True)
    return json.loads(p.stdout)


class IpCheck(unittest.TestCase):
    def test_right_token_gives_the_four_values_as_they_arrive(self):
        self.assertEqual(answer(TOKEN, TOKEN), {"REMOTE_ADDR": "198.51.100.4", "HTTP_X_FORWARDED_FOR": "203.0.113.7, 198.51.100.4",
                                                "HTTP_X_REAL_IP": None, "HTTP_FORWARDED": None})

    def test_no_or_wrong_token_gives_nothing(self):
        for k in (None, "", "cd" * 32, TOKEN[:-1], TOKEN.upper()):
            self.assertIsNone(answer(k, TOKEN), k)

    def test_not_set_on_the_server_gives_nothing(self):
        for token in (None, "", "short", TOKEN.upper()):
            self.assertIsNone(answer(TOKEN, token), token)

    def test_no_store_and_no_writes(self):
        src = PLUGIN.read_text(encoding="utf-8")
        block = src[src.index("one-time IP check (GTM-125"):]
        self.assertIn("'Cache-Control', 'no-store'", block)
        for w in ("update_option", "add_option", "error_log", "file_put_contents", "$wpdb", "set_transient", "setcookie"):
            self.assertNotIn(w, block, w)

    def test_token_not_in_the_repository(self):
        self.assertNotIn("define('ROSMAROPS_IPCHECK_TOKEN'", PLUGIN.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
