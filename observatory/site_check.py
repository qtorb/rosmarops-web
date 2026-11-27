"""Are the generated pages up to date? (advisor, 17-11, after the daily of 2026-11-17)

The daily writer commits observatory/data/agents/*.json straight to main, without a pull request, so the CI check
«Generated pages are up to date» never ran on it: on 16-11 (qwen-code) and 17-11 (kiro) main was left with site/ out
of date and every open pull request went red. This script is that same check, for the writer to run before pushing
(observatory/rules/daily.md, registry rule 9) and for the CI.

    python3 observatory/site_check.py          build, then exit 1 if a generated path differs from what is staged
    python3 observatory/site_check.py --stage  build and stage the generated paths, then check

A generated path counts as out of date when the build leaves it different from the index (unstaged change) or
untracked. What is staged counts as up to date: the writer stages the regenerated pages with its daily commit.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ["site", "wp/daily", "wp/pages", "wp/mu-plugins/rosmarops-downloads.php",
             "wp/mu-plugins/rosmarops-menu10-academy.php"]  # GTM-230: its switch line follows observatory/data/academy.json
BUILD = [sys.executable, "observatory/build.py"]


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout


def stale(root=ROOT, build=BUILD, stage=False):
    """Runs the build in root and returns the generated paths it left unstaged or untracked."""
    subprocess.run(build, cwd=root, check=True, stdout=subprocess.DEVNULL)
    if stage:
        # Only the paths that exist or are tracked: git add stops on a pathspec that matches nothing.
        paths = [p for p in GENERATED if (Path(root) / p).exists() or git(root, "ls-files", "--", p)]
        if paths:
            git(root, "add", "-A", "--", *paths)
    out = git(root, "status", "--porcelain", "--untracked-files=all", "--", *GENERATED)
    # Porcelain v1: XY path. Y is the work tree against the index; «??» is untracked. A staged-only change («M »,
    # «A ») is up to date.
    return [line for line in out.splitlines() if line[1] != " "]


def main(argv):
    lines = stale(stage="--stage" in argv)
    for line in lines:
        print(line)
    if lines:
        print("site/, wp/daily/, wp/pages/ or the download sources are out of date: run "
              "python3 observatory/site_check.py --stage and commit them with the change", file=sys.stderr)
        return 1
    print("generated pages: up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
