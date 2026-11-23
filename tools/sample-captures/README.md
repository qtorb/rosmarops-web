# Sample report captures

When qtorb/rosmarops publishes a new release, the workflow `.github/workflows/sample-captures.yml` refreshes the sample report on the site and opens a pull request. Nothing is merged or deployed on its own: Albert looks at the captures and merges.

What the workflow does, in order:

1. Downloads `sample-report.en.html` and `sample-report.es.html` from the release.
2. Updates the agent lists and the map for that release (`observatory/agent_lists.py`, `observatory/map_page.py fetch`). Both calls to the GitHub API use the workflow's token.
3. Takes the eight captures with `cap.js`:
   - at 1280 px, the report from the top down to the end of the «Findings» block;
   - at 390 px, from the top down to the end of the «Result» block;
   - each at scale 1 and 2, in English and Spanish.
4. Updates the image sizes in the pages (`update_sizes.py`) and cuts the home thumbnails (`thumbs.py`).
5. Writes the release tag in `site/sample-report/VERSION`. `version_sentence.py` then rewrites the sentence «It was made by RosmarOps … on …» on the three sample report pages, taking the version from that file and the date from the report's own header.
6. Pushes a branch `sample-report-<tag>` and opens the pull request with the captures shown inline.

To try the captures by hand: `node tools/sample-captures/cap.js <folder with the two reports> <output folder>`.
