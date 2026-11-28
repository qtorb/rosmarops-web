"""The RosmarOps Control Baseline (GTM-223, block 206): data rules, what is published and when, the two pages, the line
on the Observatory index and the public copies of the data. Texts are the literal ones of vigil
docs/research/2026-11-26-minimo-de-control-pagina-publica.md §3 and §4, in observatory/i18n/{en,es,ca}.json."""
import copy
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import build  # noqa: E402
import minimum  # noqa: E402

FIX = ROOT / "observatory" / "tests" / "fixture" / "minimum"
PASS = FIX / "example-orchestrator" / "2026-11-01.json"
FAIL = FIX / "example-builder-cloud" / "2026-11-01.json"
CRIT = {"en": "observatory/control-baseline/", "es": "es/observatorio/minimo-de-control/", "ca": "ca/observatori/minim-de-control/"}


def cat(lang):
    return json.loads((ROOT / "observatory" / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def text(html_s):
    return html.unescape(re.sub(r"<[^>]+>", " ", html_s))


def run_build(out, minimum_dir, today, data=None):
    cmd = [sys.executable, str(ROOT / "observatory" / "build.py"), "--out", str(out), "--minimum", str(minimum_dir), "--today", today]
    if data:
        cmd += ["--data", str(data)]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


class Rules(unittest.TestCase):
    """Point 1: what the schema does not cover."""

    def test_fixtures_and_data_follow_the_rules(self):
        for f in minimum.files(FIX) + minimum.files():
            self.assertEqual(minimum.problems(load(f), f), [], str(f))

    def test_schema_is_vigils_copy(self):
        self.assertEqual(load(minimum.SCHEMA)["$id"], "https://rosmarops.com/observatory/minimum/minim-result.v2.schema.json")

    def test_schema_validates_fixtures_and_data(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema is installed only in the CI")
        v = Draft202012Validator(load(minimum.SCHEMA))
        for f in minimum.files(FIX) + minimum.files():
            self.assertEqual([e.message for e in v.iter_errors(load(f))], [], str(f))

    def broken(self, change, path=FAIL):
        r = load(path)
        change(r)
        return minimum.problems(r, path)

    def test_total_met_passes(self):
        self.assertTrue(any("total" in p for p in self.broken(lambda r: r.update(total=7))))
        self.assertTrue(any("met" in p for p in self.broken(lambda r: r.update(met=4))))
        self.assertTrue(any("passes" in p for p in self.broken(lambda r: r.update(passes=True))))

    def test_m2_only_if_third_party_agents(self):
        def f(r):
            r["applies"]["third_party_agents"]["value"] = "yes"
        self.assertTrue(any(p.startswith("M2 ") for p in self.broken(f)))

    def test_m3_only_if_user_machine(self):
        def f(r):
            r["criteria"][2]["result"] = "unknown"
            r["criteria"][2]["unknown_reason"] = "x"
        self.assertTrue(any(p.startswith("M3 ") for p in self.broken(f)))

    def test_no_other_criterion_is_not_applicable(self):
        def f(r):
            r["criteria"][4]["result"] = "not_applicable"
        self.assertTrue(any(p.startswith("M5 ") for p in self.broken(f)))

    def test_unknown_facts_are_refused(self):
        def f(r):
            r["applies"]["runs_on"]["value"] = "unknown"
        self.assertTrue(any("runs_on" in p for p in self.broken(f)))

    def test_fourteen_days(self):
        def f(r):
            r["vendor"]["publish_after"] = "2026-11-15"
        self.assertTrue(any("14 days" in p for p in self.broken(f)))
        def ok(r):
            r["vendor"]["publish_after"] = "2026-11-16"
        self.assertEqual(self.broken(ok), [])

    def test_ninety_days(self):
        self.assertTrue(any("90 days" in p for p in self.broken(lambda r: r.update(expires_at="2027-01-31"))))

    def test_name_and_folder(self):
        r = load(FAIL)
        self.assertTrue(minimum.problems(r, FIX / "other" / "2026-11-01.json"))
        self.assertTrue(minimum.problems(r, FIX / "example-builder-cloud" / "2026-11-02.json"))

    def test_texts_the_page_needs(self):
        self.assertTrue(any("tested_plan" in p for p in self.broken(lambda r: r.pop("tested_plan"))))
        self.assertEqual(self.broken(lambda r: r.update(tested_plan="")), [])  # no named plan to cite (family spec §5)
        self.assertTrue(any("tested_version" in p for p in self.broken(lambda r: r.pop("tested_version"), PASS)))
        def f(r):
            r["criteria"][3]["how"] = "none"
        self.assertTrue(any("how is none" in p for p in self.broken(f)))


class Published(unittest.TestCase):
    """Point 2: only results whose vendor.publish_after is the day of the build or earlier."""

    def test_publish_after(self):
        res = minimum.load(FIX)
        self.assertEqual(minimum.published(res, "2026-09-15"), {})
        self.assertEqual(list(minimum.published(res, "2026-09-16")), ["example-orchestrator"])
        self.assertEqual(len(minimum.published(res, "2026-09-16")["example-orchestrator"]), 1)
        later = minimum.published(res, "2026-11-16")
        self.assertEqual(sorted(later), ["example-builder-cloud", "example-orchestrator"])
        self.assertEqual([r["measured_at"] for r in later["example-orchestrator"]], ["2026-09-01", "2026-11-01"])

    def test_owner_agent(self):
        ids = {"n8n", "dify"}
        self.assertEqual(minimum.owner_agent("n8n", ids), "n8n")
        self.assertEqual(minimum.owner_agent("n8n-cloud", ids), "n8n")
        self.assertEqual(minimum.owner_agent("dify-cloud", ids), "dify")
        self.assertIsNone(minimum.owner_agent("gumloop", ids))

    def test_data_waits_for_publish_after(self):
        """GTM-225: the five results of 25-11 are in the data from 26-11, to be published on 10-12-2026.
        GTM-233: the two agents on the vendor's computer, measured on 27-11, are published on 11-12-2026."""
        res = minimum.load()
        first = ["dify-cloud", "gumloop", "n8n", "n8n-cloud", "paperclip"]
        second = ["copilot-autopilot", "meta-muse"]
        self.assertEqual(sorted(r["candidate"]["id"] for _, r in res), sorted(first + second))
        after = {r["candidate"]["id"]: r["vendor"]["publish_after"] for _, r in res}
        self.assertEqual({after[i] for i in first}, {"2026-12-10"})
        self.assertEqual({after[i] for i in second}, {"2026-12-11"})
        self.assertEqual(minimum.published(res, "2026-12-09"), {})
        self.assertEqual(sorted(minimum.published(res, "2026-12-10")), first)
        self.assertEqual(sorted(minimum.published(res, "2026-12-11")), sorted(first + second))
        fam = {i: minimum.family_of(r, minimum.families())["id"] for i, r in ((r["candidate"]["id"], r) for _, r in res)}
        self.assertEqual({fam[i] for i in second}, {"agents-on-the-vendors-computer"})
        self.assertEqual({fam[i] for i in first}, {"orchestrators-and-automation"})


def committed_day():
    """The day the committed site was built for: the criterion page carries «meta.none» until a result is published."""
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


class Site(unittest.TestCase):
    """The committed site, before 10-12-2026: the criterion page is published, with no results yet, and in the
    sitemap. From the day the first results publish, the committed site is the one the build of that day writes,
    which Pages checks with the fixture."""

    def setUp(self):
        if minimum.published(minimum.load(), committed_day()):
            self.skipTest("results are published from their publish_after on; site_check checks the committed site")

    def test_criterion_page_published_empty(self):
        for lang, p in CRIT.items():
            s = (ROOT / "site" / p / "index.html").read_text(encoding="utf-8")
            c = cat(lang)
            self.assertNotIn('content="noindex"', s)
            self.assertIn(html.escape(c["minimum.r.empty"], quote=True), s)
            self.assertIn(html.escape(c["minimum.meta.none"].replace("{v}", "4"), quote=True), s)
            self.assertIn("albert@rosmarops.com", text(s))
            self.assertIn(f"<loc>https://rosmarops.com/{p}</loc>", (ROOT / "site" / "sitemap-pages.xml").read_text(encoding="utf-8"))

    def test_schema_published_and_nothing_else(self):
        d = ROOT / "site" / "observatory" / "minimum"
        self.assertEqual(sorted(x.name for x in d.iterdir()), ["minim-result.v2.schema.json"])
        self.assertEqual((d / "minim-result.v2.schema.json").read_bytes(), minimum.SCHEMA.read_bytes())


class Pages(unittest.TestCase):
    """Points 2 to 5, built from the test fixture into a temporary folder."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.out = cls.tmp / "out"
        p = run_build(cls.out, FIX, "2026-12-01")
        assert p.returncode == 0, p.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def page(self, lang, rid=""):
        return (self.out / CRIT[lang] / rid / "index.html").read_text(encoding="utf-8")

    def test_data_copies(self):
        d = self.out / "observatory" / "minimum"
        self.assertEqual((d / "example-orchestrator" / "latest.json").read_bytes(), PASS.read_bytes())
        self.assertEqual((d / "example-orchestrator" / "2026-09-01.json").read_bytes(), (FIX / "example-orchestrator" / "2026-09-01.json").read_bytes())
        self.assertEqual((d / "example-builder-cloud" / "latest.json").read_bytes(), FAIL.read_bytes())
        self.assertTrue((d / "minim-result.v2.schema.json").exists())

    def test_not_published_before_publish_after(self):
        out = self.tmp / "early"
        p = run_build(out, FIX, "2026-11-15")
        self.assertEqual(p.returncode, 0, p.stderr)
        d = out / "observatory" / "minimum"
        self.assertTrue((d / "example-orchestrator" / "2026-09-01.json").exists())
        self.assertFalse((d / "example-orchestrator" / "2026-11-01.json").exists())
        self.assertFalse((d / "example-builder-cloud").exists())
        self.assertFalse((out / CRIT["en"] / "example-builder-cloud").exists())
        latest = (d / "example-orchestrator" / "latest.json").read_bytes()
        self.assertEqual(latest, (FIX / "example-orchestrator" / "2026-09-01.json").read_bytes())

    def test_block_order_criterion(self):
        for lang in ("en", "es", "ca"):
            c, s = cat(lang), self.page(lang)
            ids = re.findall(r'<h2 id="([a-z-]+)-h">', s)
            self.assertEqual(ids, ["criteria", "who-meets", "families", "how", "results", "vendor", "not", "who", "data"])  # GTM-232
            for k in ["c.h2", "p.h2", "m.h2", "r.h2", "f.h2", "n.h2", "w.h2", "d.h2"]:
                self.assertIn(f'>{html.escape(c["minimum." + k], quote=True)}</h2>', s)

    def test_results_table_alphabetical_with_vendor_state(self):
        c, s = cat("es"), self.page("es")
        rows = re.findall(r'<a href="/es/observatorio/minimo-de-control/([a-z-]+)/">', s.split('id="results-h"')[1].split("</section>")[0])
        self.assertEqual(rows, ["example-builder-cloud", "example-orchestrator"])  # Example Builder, Example Orchestrator
        self.assertIn(html.escape(c["minimum.r.note"]), s)
        self.assertIn("Avisado el 2 de noviembre de 2026; sin respuesta", text(s))
        self.assertIn(c["minimum.use.cloud"].replace("{plan}", "Pro"), text(s))
        self.assertIn("3 de 5", text(s))

    def test_result_page_fail(self):
        for lang in ("en", "es", "ca"):
            c, s = cat(lang), self.page(lang, "example-builder-cloud")
            t = text(s)
            self.assertIn(c["minimum.x.fail"].replace("{k}", "2"), t)
            for k in ("res.yes", "res.no", "res.unknown", "res.na"):
                self.assertIn(f'<strong>{html.escape(c["minimum." + k], quote=True)}</strong>', s)
            self.assertIn('<span lang="en">The documentation describes the feature but not how to limit it per agent.</span>', s)
            self.assertIn(html.escape(c["minimum.ev.reason"], quote=True), s)
            self.assertIn(c["minimum.a.f1.no"], t)
            self.assertIn(c["minimum.a.f2.cloud"], t)
            self.assertIn('href="/observatory/minimum/example-builder-cloud/2026-11-01.json"', s)
            self.assertEqual(re.findall(r'<h2 id="([a-z-]+)-h">', s), ["measured", "criteria", "reply", "history", "data"])
            self.assertIn('<p class="disclaimer">', s)

    def test_result_page_pass_and_history(self):
        c, s = cat("en"), self.page("en", "example-orchestrator")
        t = text(s)
        self.assertIn(c["minimum.x.pass"], t)
        self.assertIn("Installed by whoever uses it · version 1.4.0 · measured on 1 November 2026 · expires on 30 January 2027", t)
        self.assertIn("1 November 2026: 7 of 7 (this one)", t)
        self.assertIn("1 September 2026: 6 of 7", t)
        self.assertIn("Changed the product or its documentation on 10 November 2026", t)
        self.assertIn(c["minimum.y.link"], t)
        self.assertIn(c["minimum.y.notice"], t)

    def test_one_criterion_missing(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            d = tmp / "min" / "example-orchestrator"
            d.mkdir(parents=True)
            shutil.copy(FIX / "example-orchestrator" / "2026-09-01.json", d)
            p = run_build(tmp / "out", tmp / "min", "2026-12-01")
            self.assertEqual(p.returncode, 0, p.stderr)
            s = (tmp / "out" / CRIT["es"] / "example-orchestrator" / "index.html").read_text(encoding="utf-8")
            self.assertIn(cat("es")["minimum.x.fail.one"], text(s))
        finally:
            shutil.rmtree(tmp)

    def test_gtm224_criteria_widths(self):
        """GTM-224 point 1: 8, 24, 44 and 24 % from 700 px (the colgroup, which the CSS hides below 700 px)."""
        for lang in ("en", "es", "ca"):
            crit = self.page(lang).split('id="criteria-h"')[1].split("</section>")[0]
            self.assertIn('<colgroup><col style="width:8%"><col style="width:24%"><col style="width:44%"><col style="width:24%"></colgroup>', crit)

    def test_gtm224_not_applicable_how_is_a_dash(self):
        """GTM-224 point 2: «No aplica» has «—» in «How it was checked», like in «Evidence»."""
        for lang in ("en", "es", "ca"):
            c, s = cat(lang), self.page(lang, "example-builder-cloud")
            na = html.escape(c["minimum.res.na"], quote=True)
            for row in re.findall(r"<tr>(.*?)</tr>", s):
                if f"<strong>{na}</strong>" in row:
                    cells = re.findall(r"<td[^>]*>(.*?)</td>", row)
                    self.assertEqual(cells[1:], [c["minimum.ev.na"], c["minimum.ev.na"]], lang)

    def test_gtm224_count_is_h2_in_the_box(self):
        """GTM-224 point 3: x.count is the box's h2; the two other lines stay paragraphs."""
        c, s = cat("es"), self.page("es", "example-builder-cloud")
        box = s.split('<div class="box panel summary">')[1].split("</div>")[0]
        self.assertIn("<h2>3 de 5 criterios</h2>", box)
        self.assertIn(f'<p>{html.escape(c["minimum.x.what"], quote=True)}</p>', box)

    def test_english_quotes_are_curly(self):
        for k, v in cat("en").items():
            if k.startswith("minimum."):
                self.assertNotIn('"', v, k)

    def test_titles(self):
        s = self.page("es")
        self.assertIn("<title>El mínimo de control · Observatorio RosmarOps</title>", s)
        s = self.page("en", "example-orchestrator")
        self.assertIn("<title>Example Orchestrator: Control Baseline · RosmarOps Observatory</title>", s)


FAMS = minimum.families()
FAM_A, FAM_B = FAMS


def fam_page(out, fam, lang):
    return (Path(out) / fam["path"][lang].strip("/") / "index.html").read_text(encoding="utf-8")


class Families(unittest.TestCase):
    """GTM-232: the two family pages, the «Families» block of the criterion page and the family in a result's crumbs."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        # The fixture plus two hosted agents: one published on 2026-11-16, one notified later and not yet published.
        cls.data = cls.tmp / "minimum"
        shutil.copytree(FIX, cls.data)
        for rid, notified, after in (("example-hosted", "2026-11-02", "2026-11-16"), ("example-hosted-later", "2026-11-25", "2026-12-09")):
            r = load(FAIL)
            r["candidate"] = {"id": rid, "name": rid.replace("-", " ").title()}
            r["kind"] = "hosted_agent"
            r["vendor"]["notified_at"], r["vendor"]["publish_after"] = notified, after
            (cls.data / rid).mkdir()
            (cls.data / rid / "2026-11-01.json").write_text(json.dumps(r), encoding="utf-8")
        cls.out = cls.tmp / "out"
        p = run_build(cls.out, cls.data, "2026-12-01")
        assert p.returncode == 0, p.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_two_families_with_their_kinds(self):
        self.assertEqual([f["kinds"] for f in FAMS], [["orchestrator", "workflow_automation", "agent_builder"], ["hosted_agent"]])
        self.assertIsNone(minimum.family_of({"kind": "agent_framework"}, FAMS))
        for f in FAMS:
            for lang, p in f["path"].items():
                self.assertTrue(p.startswith("/" + CRIT[lang]), p)

    def test_the_schema_accepts_hosted_agent(self):
        self.assertIn("hosted_agent", load(minimum.SCHEMA)["properties"]["kind"]["enum"])
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema not installed")
        r = load(self.data / "example-hosted" / "2026-11-01.json")
        self.assertEqual(list(Draft202012Validator(load(minimum.SCHEMA)).iter_errors(r)), [])

    def test_committed_pages_exist_without_results(self):
        """Before 10-12 the committed site has the two family pages in three languages, with the «no results yet» line,
        in the sitemap, and nothing of the five results of 25-11."""
        if minimum.published(minimum.load(), committed_day()):
            self.skipTest("results are published from their publish_after on")
        sm = (ROOT / "site" / "sitemap-pages.xml").read_text(encoding="utf-8")
        for f in FAMS:
            for lang in ("en", "es", "ca"):
                s = fam_page(ROOT / "site", f, lang)
                self.assertIn(html.escape(cat(lang)["minimum.r.empty"], quote=True), s)
                self.assertNotIn('content="noindex"', s)
                self.assertIn(f"<loc>https://rosmarops.com{f['path'][lang]}</loc>", sm)
                for rid in ("paperclip", "n8n", "gumloop", "dify", "copilot", "muse"):
                    self.assertNotIn(rid, text(s).lower())

    def test_block_order_and_texts(self):
        for f in FAMS:
            for lang in ("en", "es", "ca"):
                c, s, F = cat(lang), fam_page(self.out, f, lang), f[lang]
                ids = re.findall(r'<h2 id="([a-z-]+)-h">', s)
                want = ["what", "why", "measure"] + (["notyet"] if "notyet.h2" in F else []) + ["results", "vendor"]
                self.assertEqual(ids, want)
                self.assertEqual(re.findall(r'<section id="([a-z-]+)" class="box panel"', s), [i for i in want if i != "results"])
                for key in ("h1", "lead", "what.p", "why.p", "measure.p") + (("notyet.h2", "notyet.p") if "notyet.h2" in F else ()):
                    self.assertIn(html.escape(F[key], quote=True), s, (f["id"], lang, key))
                for key in ("family.what.h2", "family.why.h2", "family.measure.h2", "family.results.h2", "f.h2", "f.1", "f.4"):
                    self.assertIn(html.escape(c["minimum." + key], quote=True), s)
                self.assertIn(f'<a href="/{CRIT[lang]}">{html.escape(c["minimum.family.measure.link"], quote=True)}</a>', s)
                self.assertIn(f'<title>{html.escape(F["h1"], quote=True)} · {html.escape(c["minimum.crumb"], quote=True)}</title>', s)
                self.assertIn(f'<meta name="description" content="{html.escape(F["lead"], quote=True)}">', s)
                self.assertIn(f'<a href="/{CRIT[lang]}">{html.escape(c["minimum.crumb"], quote=True)}</a> › {html.escape(F["h1"], quote=True)}</p>', s)

    def test_a_published_result_shows_only_in_its_family(self):
        for lang in ("en", "es", "ca"):
            a, b = fam_page(self.out, FAM_A, lang), fam_page(self.out, FAM_B, lang)
            self.assertIn('href="/' + CRIT[lang] + 'example-hosted/"', b)
            self.assertNotIn("example-hosted/", a)
            self.assertIn('href="/' + CRIT[lang] + 'example-orchestrator/"', a)
            self.assertIn('href="/' + CRIT[lang] + 'example-builder-cloud/"', a)
            self.assertNotIn("example-orchestrator", b)
            self.assertNotIn(html.escape(cat(lang)["minimum.r.empty"], quote=True), b)

    def test_an_unpublished_result_shows_in_no_family_page(self):
        for lang in ("en", "es", "ca"):
            for f in FAMS:
                self.assertNotIn("example-hosted-later", fam_page(self.out, f, lang))
            self.assertNotIn("example-hosted-later", (self.out / CRIT[lang] / "index.html").read_text(encoding="utf-8"))
            self.assertFalse((self.out / CRIT[lang] / "example-hosted-later").exists())

    def test_families_block_on_the_criterion_page(self):
        for lang in ("en", "es", "ca"):
            s = (self.out / CRIT[lang] / "index.html").read_text(encoding="utf-8")
            block = s[s.index('<section id="families" class="box panel"'):]
            block = block[:block.index("</section>")]
            self.assertIn(html.escape(cat(lang)["minimum.family.fam.h2"], quote=True) + "</h2>", block)
            for f in FAMS:
                self.assertIn(f'<li><strong><a href="{f["path"][lang]}">{html.escape(f[lang]["h1"], quote=True)}</a></strong>'
                              f'<span class="fam-line">{html.escape(f[lang]["fam.line"], quote=True)}</span></li>', block)
            self.assertIn(".fam-line{display:block;margin-top:2px}", s)  # §4: on the next line, 2 px below
            self.assertLess(s.index('id="who-meets-h"'), s.index('id="families-h"'))
            self.assertLess(s.index('id="families-h"'), s.index('id="how-h"'))

    def test_result_crumbs_carry_the_family(self):
        for lang in ("en", "es", "ca"):
            for rid, f in (("example-hosted", FAM_B), ("example-orchestrator", FAM_A)):
                s = (self.out / CRIT[lang] / rid / "index.html").read_text(encoding="utf-8")
                crumbs = s[s.index('<p class="crumbs">'):]
                crumbs = crumbs[:crumbs.index("</p>")]
                self.assertIn(f'<a href="/{CRIT[lang]}">{html.escape(cat(lang)["minimum.crumb"], quote=True)}</a> › '
                              f'<a href="{f["path"][lang]}">{html.escape(f[lang]["h1"], quote=True)}</a> › ', crumbs)
                self.assertIn(f'"item":"https://rosmarops.com{f["path"][lang]}"', s)

    def test_no_outside_resources(self):
        for f in FAMS:
            for lang in ("en", "es", "ca"):
                s = fam_page(self.out, f, lang)
                for u in re.findall(r'(?:src|href)="((?:https?:)?//[^"]+)"', s):
                    self.assertTrue(u.startswith("https://rosmarops.com/"), u)

    def test_a_family_and_a_product_never_share_an_address(self):
        res = [(None, {"candidate": {"id": "orchestrators-and-automation"}})]
        self.assertTrue(minimum.clashes(FAMS, res, {l: "/" + p for l, p in CRIT.items()}))
        self.assertEqual(minimum.clashes(FAMS, minimum.load(), {l: "/" + p for l, p in CRIT.items()}), [])
        # The build stops on such a clash.
        data = self.tmp / "clash"
        shutil.copytree(FIX, data)
        r = load(FAIL)
        r["candidate"]["id"] = "orchestrators-and-automation"
        (data / "orchestrators-and-automation").mkdir()
        (data / "orchestrators-and-automation" / "2026-11-01.json").write_text(json.dumps(r), encoding="utf-8")
        p = run_build(self.tmp / "clash-out", data, "2026-12-01")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("is also the page of the result 'orchestrators-and-automation'", p.stderr)


class IndexLine(unittest.TestCase):
    """Point 5: row.line under a product's row, one per published result; row.line.use when there are two."""

    def build(self, results):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        for rid, src in results:
            r = load(src)
            r["candidate"]["id"] = rid
            d = tmp / "min" / rid
            d.mkdir(parents=True)
            (d / f'{r["measured_at"]}.json').write_text(json.dumps(r), encoding="utf-8")
        p = run_build(tmp / "out", tmp / "min", "2026-12-01", data=ROOT / "observatory" / "tests" / "fixture")
        self.assertEqual(p.returncode, 0, p.stderr)
        s = (tmp / "out" / "es" / "observatorio" / "index.html").read_text(encoding="utf-8")
        return s.split('id="p-example-agent"')[1].split("</li>")[0]

    def test_one_result(self):
        row = self.build([("example-agent", PASS)])
        self.assertIn('<p class="co-meta"><a href="/es/observatorio/minimo-de-control/example-agent/">Mínimo de control: 7 de 7 · 1 de noviembre de 2026</a></p>', row)
        self.assertTrue(row.endswith("</a></p>"))

    def test_two_results(self):
        row = self.build([("example-agent", PASS), ("example-agent-cloud", FAIL)])
        self.assertIn("Mínimo de control (instalado): 7 de 7 · 1 de noviembre de 2026", row)
        self.assertIn("Mínimo de control (nube): 3 de 5 · 1 de noviembre de 2026", row)

    def test_none(self):
        row = self.build([])
        self.assertNotIn("minimo-de-control", row)


if __name__ == "__main__":
    unittest.main()


class NoPlan(unittest.TestCase):
    """A result in the vendor's cloud with an empty tested_plan names no plan: use.cloud.noplan and x.meta.cloud.noplan
    (vigil docs/research/2026-11-27-minimo-de-control-fichas-de-familia.md §5, GTM-233)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.data = cls.tmp / "minimum"
        shutil.copytree(FIX, cls.data)
        r = load(FAIL)
        r["candidate"] = {"id": "example-noplan", "name": "Example Noplan"}
        r["kind"] = "hosted_agent"
        r["tested_plan"] = ""
        (cls.data / "example-noplan").mkdir()
        (cls.data / "example-noplan" / "2026-11-01.json").write_text(json.dumps(r), encoding="utf-8")
        cls.out = cls.tmp / "out"
        p = run_build(cls.out, cls.data, "2026-12-01")
        assert p.returncode == 0, p.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def row(self, s, rid):
        return text([x for x in re.findall(r"<tr>(.*?)</tr>", s, re.S) if f"/{rid}/" in x][0])

    def test_use_cloud_noplan_in_the_tables(self):
        for lang in ("en", "es", "ca"):
            c = cat(lang)
            for s in ((self.out / CRIT[lang] / "index.html").read_text(encoding="utf-8"), fam_page(self.out, FAM_B, lang)):
                row = self.row(s, "example-noplan")
                self.assertIn(c["minimum.use.cloud.noplan"], row)
                self.assertNotIn(c["minimum.use.cloud"].split("{plan}")[0].rstrip(), row.replace(c["minimum.use.cloud.noplan"], ""))
            # a result with a plan keeps the sentence with its plan
            self.assertIn(c["minimum.use.cloud"].replace("{plan}", "Pro"), self.row((self.out / CRIT[lang] / "index.html").read_text(encoding="utf-8"), "example-builder-cloud"))

    def test_x_meta_cloud_noplan_on_the_result_page(self):
        want = {"en": "In the vendor's cloud · measured on 1 November 2026 · expires on 30 January 2027",
                "es": "En la nube del fabricante · medido el 1 de noviembre de 2026 · caduca el 30 de enero de 2027",
                "ca": "Al núvol del fabricant · mesurat el 1 de novembre de 2026 · caduca el 30 de gener de 2027"}
        for lang in ("en", "es", "ca"):
            s = (self.out / CRIT[lang] / "example-noplan" / "index.html").read_text(encoding="utf-8")
            meta = text(re.search(r'<p class="pagemeta">(.*?)</p>', s, re.S).group(1)).strip()
            self.assertEqual(meta, want[lang])
        # a result with a plan keeps the sentence with its plan
        s = (self.out / CRIT["en"] / "example-builder-cloud" / "index.html").read_text(encoding="utf-8")
        meta = text(re.search(r'<p class="pagemeta">(.*?)</p>', s, re.S).group(1)).strip()
        self.assertEqual(meta, "In the vendor's cloud · Pro plan · measured on 1 November 2026 · expires on 30 January 2027")
