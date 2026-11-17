"""GTM-176: the «Sandbox» section of rosmarops.com (/sandbox/, /es/sandbox/, /ca/sandbox/) as a step-by-step guide.

It replaces the cards of GTM-175 and keeps their data (the "templates" field of each agent file, schema v1.14 with
checks from CTO-61), their watch and their incoming links. Texts: observatory/i18n/sandbox-guide.json (GTM-176 §3 and
§5) and observatory/i18n/sandbox-section.json (GTM-175: template sentences, uncovered, session, source). Page shell: the
guide «How to try an AI agent in a test environment» of the same language. A template shows «Por revisar» when the
latest raw file of the collector says one of its pages lost a watched string. Lab screenshots (§5) come from
observatory/data/lab/manifest.json once BV-250 brings it in; until then there is none and no gap is drawn. Called by
build.py.

GTM-176 §4: agents without a sandbox on a system get the steps with another user account (menu paths checked by the
advisor against the official help on 16-11).
"""

import html
import json
import re
from pathlib import Path

import company_page
import map_page
import sandbox_page

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
TEXTS = ROOT / "observatory" / "i18n" / "sandbox-section.json"
SOURCES = ROOT / "observatory" / "sources.json"
RAW_DIR = ROOT / "observatory" / "raw"
LANGS = ("en", "es", "ca")
SECTION_PATH = {"en": "/sandbox/", "es": "/es/sandbox/", "ca": "/ca/sandbox/"}
GUIDE_FILE = {"en": "try-an-ai-agent/index.html", "es": "es/probar-un-agente-de-ia/index.html",
              "ca": "ca/provar-un-agent-dia/index.html"}
OBS_PATH = {"en": "/observatory/", "es": "/es/observatorio/", "ca": "/ca/observatori/"}
METHOD_PATH = {"en": "/methodology/", "es": "/es/metodologia/", "ca": "/ca/metodologia/"}
LOCALE = {"en": "en_US", "es": "es_ES", "ca": "ca_ES"}
DOWNLOAD = {
    "en": ("/download", "en", "Download from the Microsoft Store", "/macos/", "Mac (preview)", "/linux/"),
    "es": ("/es/descargar", "es", "Descargar desde Microsoft Store", "/es/macos/", "Mac (vista previa)", "/es/linux/"),
    "ca": ("/ca/descarregar", "ca", "Descarrega del Microsoft Store", "/ca/macos/", "Mac (vista prèvia)", "/ca/linux/"),
}
# The signed placeholders, as they read in each language of the brief, all filled from one name.
PLACEHOLDER = re.compile(r"\{(agent|file|system|maker|date|list)\}")
COMMENT = {"json": "//", "toml": "#", "yaml": "#"}

def esc(s):
    return html.escape(str(s), quote=True)


def texts():
    return json.loads(TEXTS.read_text(encoding="utf-8"))["texts"]


def fill(s, **kw):
    return PLACEHOLDER.sub(lambda m: str(kw[m.group(1)]), s)


def code(s):
    """Escaped text with `...` painted as <code> (GTM-175 §1)."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(s))


def with_templates(agents):
    """The agent files with templates, in the Observatory's alphabetical order (the comparison table's)."""
    items = [a for a in agents if a.get("templates")]
    names = map_page.agent_names([a["agent"] for a in items], "en")
    return sorted(items, key=lambda a: names[a["agent"]["id"]].lower())


def template_urls(t):
    urls = [t["source"]["url"]] + [s["url"] for s in t.get("extra_sources", [])]
    if "session" in t:
        urls.append(t["session"]["source"]["url"])
    return urls


def watch_map(agents):
    """{url: watch strings} of every template page, in the order they first appear: what sources.json must watch."""
    out = {}
    for a in agents:
        for s in ("windows", "macos", "linux"):
            t = (a.get("templates") or {}).get(s)
            if not t:
                continue
            pairs = [(t["source"]["url"], t["watch"])] + [(x["url"], x.get("watch", [])) for x in t.get("extra_sources", [])]
            if "session" in t:
                pairs.append((t["session"]["source"]["url"], t["session"]["source"].get("watch", [])))
            for url, watch in pairs:
                if watch:
                    lst = out.setdefault(url, [])
                    lst += [w for w in watch if w not in lst]
    return out


def to_review(raw_dir=RAW_DIR, sources_file=SOURCES):
    """URLs whose page lost a watched string in the latest raw file of the collector (empty if there is none).

    Only strings still watched count: a string replaced in sources.json since that reading (F49, signed by Albert
    17-11) stops marking its template «Por revisar» at the next build, not at the next reading."""
    files = sorted(Path(raw_dir).glob("????-??-??.json"))
    if not files:
        return set()
    raw = json.loads(files[-1].read_text(encoding="utf-8"))
    read = {s["id"]: s.get("read", {}) for s in json.loads(Path(sources_file).read_text(encoding="utf-8"))["sources"]}
    out = set()
    for s in raw.get("sources", []):
        r = read.get(s["id"], {})
        if r.get("url") and set(s.get("missing") or []) & set(r.get("watch", [])):
            out.add(r["url"])
    return out


def maker(a):
    return a["agent"]["vendor"].split(" (")[0]


GUIDE_TEXTS = ROOT / "observatory" / "i18n" / "sandbox-guide.json"
LAB_MANIFEST = ROOT / "observatory" / "data" / "lab" / "manifest.json"
LAB_IMG = "/assets/sandbox-lab/"
SYSTEMS = ("windows", "macos", "linux")
GPH = re.compile(r"\{(agent|system|cmd|n|date|version|os_version|command|when)\}")

GUIDE_CSS = """
:root{--paper:#FFFFFF;--brand:#2346B8;--on-brand:#FFFFFF}
.sg{display:flex;flex-direction:column;min-width:0}
.sg-head{display:flex;flex-direction:column;gap:16px;max-width:760px}
.sg-head h1{margin:0;font-size:clamp(30px,5vw,44px);line-height:1.12;font-weight:700;letter-spacing:-.02em}
.sg-lead{margin:0;font-size:19px;line-height:1.5;color:var(--ink2);max-width:760px}
.sg-sel{margin-top:36px;background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:28px 32px;display:flex;flex-direction:column;gap:22px}
.sg-sel[hidden]{display:none}
.sg-grp{display:flex;flex-direction:column}
.sg-lab{margin:0 0 12px;font-size:15px;font-weight:600;color:var(--ink)}
.sg-picked{font-weight:400;color:var(--muted)}
.sg-btns{display:flex;flex-wrap:wrap;gap:8px}
.sg-btn{font:inherit;font-size:14px;font-weight:500;padding:10px 14px;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
.sg-btn[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.sg-btn:focus-visible,.sg-mob select:focus-visible,.tb-copy:focus-visible,.hbtn:focus-visible,.sg summary:focus-visible{outline:3px solid var(--brand);outline-offset:2px}
.sg-mob{display:none;flex-direction:column;gap:8px}
.sg-mob label{font-size:14px;font-weight:600}
.sg-mob select{width:100%;height:44px;font:inherit;font-size:15px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);padding:0 10px}
.sg-status{margin:0;padding-top:16px;border-top:1px solid var(--line);font-size:16px;line-height:1.45;color:var(--ink2)}
.sg-status:empty{display:none}
.sg-status strong,.sg-cstatus strong{font-weight:600;color:var(--ink)}
.sg-status .sg-sub,.sg-cstatus .sg-sub{display:block;margin-top:6px;font-size:14px;color:var(--muted)}
.sg-combo{margin-top:48px;min-width:0;scroll-margin-top:16px}
.sg-combo-h{margin:0 0 8px;font-size:26px;line-height:1.2;font-weight:700}
.sg-cstatus{margin:0 0 24px;font-size:16px;line-height:1.45;color:var(--ink2)}
.js .sg-combo,.js .sg-combo-h,.js .sg-cstatus{display:none}
.js .sg-combo.on{display:block}
.sg-none{display:none;margin-top:48px}
.js .sg-none.on{display:block}
.sg-cols{display:flex;flex-wrap:wrap;gap:48px;align-items:flex-start}
.sg-main{flex:1 1 640px;min-width:0;display:flex;flex-direction:column;gap:40px}
.sg-side{flex:0 0 280px;display:flex;flex-direction:column;gap:16px;min-width:0}
.sg-noneline{margin:0;font-size:16px;color:var(--ink2)}
.sg-steps{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:40px}
.sg-step{display:grid;grid-template-columns:40px minmax(0,1fr);column-gap:20px;align-items:start}
.sg-num{grid-row:1;width:40px;height:40px;border-radius:50%;background:var(--ink);color:var(--paper);display:grid;place-items:center;font-size:18px;font-weight:600}
.sg-num.opt{background:transparent;border:2px solid var(--ink);color:var(--ink);box-sizing:border-box}
.sg h2{text-transform:none;letter-spacing:0;color:var(--ink)}
.sg-step h2{grid-row:1;grid-column:2;margin:0;align-self:center;font-size:24px;line-height:1.25;font-weight:600}
.sg-sbody{grid-column:2;display:flex;flex-direction:column;gap:14px;margin-top:14px;min-width:0}
.sg-sbody>p,.sg-sbody li{margin:0;font-size:16px;line-height:1.55;color:var(--ink2)}
.sg-test{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:18px 20px;display:flex;flex-direction:column;gap:10px;min-width:0}
.sg-cmdrow{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.sg-cmdrow span{font-size:15px;color:var(--ink);overflow-wrap:anywhere}
.sg code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.92em}
.sg-cmdrow code{font-size:13px;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:8px 10px;display:inline-block}
.sg-exp{margin:0;font-size:15px;line-height:1.5;color:var(--ink2)}
.sg-muted{margin:0;font-size:14px;line-height:1.5;color:var(--muted)}
.sg-small{margin:0;font-size:14px;line-height:1.55;color:var(--ink2)}
.sg-noline{margin:0;font-size:15px;line-height:1.55;color:var(--ink2)}
.sg details{border:1px solid var(--line);border-radius:12px;min-width:0}
.sg summary{font-size:15px;font-weight:500;padding:16px 20px;cursor:pointer;list-style:none;color:var(--ink)}
.sg summary::-webkit-details-marker{display:none}
.sg summary::after{content:" ▸"}
.sg details[open]>summary::after{content:" ▾"}
.sg-dbody{padding:0 20px 18px;font-size:15px;line-height:1.55;color:var(--ink2);display:flex;flex-direction:column;gap:10px;min-width:0}
.sg-dbody p{margin:0}
.sg-dbody ul{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:6px;list-style:disc}
.sg pre{margin:0;background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:12px 14px;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12.5px;line-height:1.5;white-space:pre-wrap;overflow-wrap:anywhere;max-height:360px;overflow:auto;color:var(--ink)}
.tb-copy{align-self:flex-start;font:inherit;font-size:14px;font-weight:600;padding:6px 14px;border:1px solid var(--ink);border-radius:8px;background:transparent;color:var(--ink);cursor:pointer;flex:none}
.tb-copy:hover{background:var(--card)}
.hbtn{display:inline-flex;align-items:center;min-height:44px;padding:12px 20px;border:1.5px solid var(--ink);border-radius:10px;color:var(--ink);font-weight:700;line-height:1.2;text-decoration:none;font-family:inherit;font-size:16px;cursor:pointer;background:transparent}
.hbtn.primary,.hbtn.primary:hover{background:var(--brand);border-color:var(--brand);color:var(--on-brand);align-self:flex-start}
.sg figure{margin:0}
.sg figure img{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:12px}
.sg figcaption{margin-top:8px;font-size:13px;line-height:1.45;color:var(--muted)}
.sg-foot{border-top:1px solid var(--line);padding-top:8px;display:flex;flex-direction:column;gap:10px}
.sg-src{margin:0;font-size:13px;color:var(--muted)}.sg-src a{color:var(--muted)}
.sg-rev{margin:0;font-size:13px;color:var(--ink);font-weight:600}
.sg-box{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:20px;display:flex;flex-direction:column;gap:6px}
.sg-box h3{margin:0;font-size:15px;font-weight:600;color:var(--ink)}
.sg-box p{margin:0;font-size:14px;line-height:1.55;color:var(--ink2)}
.sg-box a{font-size:14px}
.sg-note{margin:48px 0 0;font-size:13px;color:var(--muted)}
.dlrow{display:flex;flex-wrap:wrap;align-items:center;gap:12px}
.sbadge{display:inline-block;line-height:0;flex:none}.sbadge img{display:block;height:52px;width:auto}
.hbtn.sec{height:52px;padding:0 24px;border:1px solid var(--ink);border-radius:12px;background:transparent;color:var(--ink);font-size:17px;justify-content:center}
.hbtn.sec:hover{color:var(--ink);background:var(--card)}
.sg-anchor{display:block;scroll-margin-top:16px}
@media (max-width:759px){
.sg-sel{padding:18px;gap:14px}
.sg-btns{display:none}.sg-grp>.sg-lab{display:none}.sg-mob{display:flex}
.sg-status{font-size:15px}
.sg-combo{margin-top:32px}
.sg-cols{flex-direction:column;gap:32px}.sg-side{flex:none;width:100%}.sg-main{flex:none;width:100%;gap:32px}
.sg-steps{gap:32px}
.sg-step{grid-template-columns:32px minmax(0,1fr);column-gap:12px}
.sg-num{width:32px;height:32px;font-size:15px}
.sg-step h2{font-size:20px}
.sg-sbody{grid-column:1 / -1}
.sg-sbody>p,.sg-sbody li{font-size:15px}
.sg-test{padding:14px}
.sg-cmdrow{flex-direction:column;align-items:stretch}.sg-cmdrow .tb-copy{align-self:flex-end}
.sg-exp{font-size:14px}
.sg summary{padding:14px 16px}
.sg-dbody{padding:0 16px 16px}
.dlrow{flex-direction:column;align-items:stretch;width:100%}.dlrow .sbadge{align-self:flex-start}
}
""".strip()

GUIDE_SCRIPT = """<script>
(function(){
var root=document.documentElement;root.classList.add('js');
var sel=document.querySelector('.sg-sel');if(!sel)return;sel.hidden=false;
var combos={};document.querySelectorAll('.sg-combo').forEach(function(c){combos[c.id]=c;});
var agents=[].map.call(document.querySelectorAll('.sg-btn[data-agent]'),function(b){return b.getAttribute('data-agent');});
var none=document.querySelector('.sg-none'),status=document.querySelector('.sg-status'),picked=document.querySelector('.sg-picked');
var sa=document.getElementById('sg-sel-agent'),ss=document.getElementById('sg-sel-system');
var st={agent:'',system:''};
function detect(){var p='';try{p=(navigator.userAgentData&&navigator.userAgentData.platform)||'';}catch(e){}
var u=(p+' '+navigator.userAgent).toLowerCase();
if(/android|iphone|ipad|ipod/.test(u))return '';if(/win/.test(u))return 'windows';if(/mac/.test(u))return 'macos';if(/linux|x11|cros/.test(u))return 'linux';return '';}
function render(push){
document.querySelectorAll('.sg-btn').forEach(function(b){var on=b.getAttribute('data-agent')?b.getAttribute('data-agent')===st.agent:b.getAttribute('data-system')===st.system;b.setAttribute('aria-pressed',on?'true':'false');});
if(sa)sa.value=st.agent;if(ss)ss.value=st.system;
Object.keys(combos).forEach(function(k){combos[k].classList.remove('on');});
var c=st.agent&&st.system?combos[st.agent+'-'+st.system]:null;
if(c){c.classList.add('on');none.classList.remove('on');var s=c.querySelector('.sg-cstatus');status.innerHTML=s?s.innerHTML:'';}
else{none.classList.add('on');status.innerHTML='';}
if(push){var h=st.agent?(st.system?st.agent+'-'+st.system:st.agent):'';try{history.replaceState(null,'',h?'#'+h:location.pathname+location.search);}catch(e){}}}
function fromHash(){var h=decodeURIComponent((location.hash||'').slice(1));
if(combos[h]){var i=h.lastIndexOf('-');st.agent=h.slice(0,i);st.system=h.slice(i+1);if(picked)picked.hidden=true;return true;}
if(agents.indexOf(h)>=0){st.agent=h;return true;}return false;}
st.system=detect();if(picked)picked.hidden=!st.system;
fromHash();render(false);
document.querySelectorAll('.sg-btn').forEach(function(b){b.addEventListener('click',function(){
if(b.getAttribute('data-agent'))st.agent=b.getAttribute('data-agent');else{st.system=b.getAttribute('data-system');if(picked)picked.hidden=true;}render(true);});});
if(sa)sa.addEventListener('change',function(){st.agent=sa.value;render(true);});
if(ss)ss.addEventListener('change',function(){st.system=ss.value;if(picked)picked.hidden=true;render(true);});
window.addEventListener('hashchange',function(){if(fromHash())render(false);});
})();
document.querySelectorAll('.tb-copy,.sg-copytpl').forEach(function(b){b.addEventListener('click',function(){
var pre=document.getElementById(b.getAttribute('data-copy'));if(!pre)return;
var label=b.textContent;
function done(){b.textContent=b.getAttribute('data-copied');setTimeout(function(){b.textContent=label;},2000);}
function select(){var r=document.createRange();r.selectNodeContents(pre);var s=window.getSelection();s.removeAllRanges();s.addRange(r);}
try{navigator.clipboard.writeText(pre.textContent).then(done,select);}catch(e){select();}});});
</script>"""


def gtexts():
    return json.loads(GUIDE_TEXTS.read_text(encoding="utf-8"))["texts"]


def gfill(s, **kw):
    return GPH.sub(lambda m: str(kw[m.group(1)]), s)


def rich(s):
    """Escaped text with **…** as <strong> and `…` as <code>."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", code(s))


def lab_entries(path=LAB_MANIFEST):
    """GTM-176 §5: the concluyente entries of the lab manifest (BV-250), or [] while no release has been brought in."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entries = data.get("entries", data) if isinstance(data, dict) else data
    return [e for e in entries if isinstance(e, dict) and e.get("result") == "concluyente"]


class Combo:
    """One agent on one system: the steps of GTM-176 §3, or the account variant of §4."""

    def __init__(self, a, system, lang, review, lab):
        self.a, self.s, self.lang, self.review = a, system, lang, review
        self.T, self.G = texts()[lang], gtexts()[lang]
        self.aid = a["agent"]["id"]
        self.cid = f"{self.aid}-{system}"
        self.name = map_page.agent_names([a["agent"]], lang)[self.aid]
        self.sysname = company_page.SYSTEM_NAME[system]
        self.t = a["templates"][system]
        self.lab = [e for e in lab if e.get("agent") == self.aid and e.get("system") == system]
        self.n = 0

    def g(self, key, **kw):
        return gfill(self.G[key], agent=self.name, system=self.sysname, **kw)

    def pid(self):
        self.n += 1
        return f"{self.cid}-c{self.n}"

    def copy_btn(self, pid):
        return (f'<button type="button" class="tb-copy" data-copy="{pid}" data-copied="{esc(self.G["copied"])}">'
                f'{esc(self.T["copy"])}</button>')

    def pre(self, text):
        pid = self.pid()
        return f'<pre id="{pid}">{esc(text)}</pre>{self.copy_btn(pid)}'

    # -- status line (§3.2)
    def status(self):
        if self.t["kind"] == "separate_account":
            key = "status.separate_account"
        else:
            v = self.a["protections"]["sandbox"][self.s]["value"]
            if v not in ("off_by_default", "on_by_default", "container_only"):
                raise ValueError(f"{self.cid}: protections sandbox value {v!r} has no status line (GTM-176 §3.2: PARA)")
            key = "status." + v
        out = rich(self.g(key))
        if "gemini_replaced" in self.t.get("checks", {}).get("notes", []):
            out += f'<span class="sg-sub">{esc(self.G["status.gemini_replaced"])}</span>'
        return out

    # -- captures (§5)
    def figure(self, step, test=None, when=None):
        out = []
        for e in self.lab:
            if e.get("step") != step or (test and e.get("test") != test) or (when and e.get("when") != when):
                continue
            w = self.G["lab.after" if e.get("when") == "despues" else "lab.before"]
            date = map_page.fmt_date(e["date"], self.lang)
            alt = self.g("lab.alt", command=e.get("command", ""), when=w)
            cap = self.g("lab.caption", version=e.get("agent_version", ""), os_version=e.get("os_version", ""), date=date)
            out.append(f'<figure><img src="{esc(LAB_IMG + e["file"])}" alt="{esc(alt)}" loading="lazy">'
                       f'<figcaption>{esc(cap)}</figcaption></figure>')
        return out

    def lab_checked(self, test):
        for e in self.lab:
            if e.get("step") == 3 and e.get("test") == test and e.get("when") == "despues":
                return map_page.fmt_date(e["date"], self.lang)
        return None

    # -- test boxes
    def box(self, check, expected, muted=None):
        if check["kind"] == "copilot_policy":
            label, cmd = self.G["chat"], "/sandbox policy"
            line = rich(label)
        else:
            cmd = check["cmd"] if check["kind"] == "cmd" else "hostname"
            line = rich(gfill(self.G["run"], cmd=f"`{cmd}`"))
        pid = self.pid()
        out = (f'<div class="sg-test"><div class="sg-cmdrow"><span>{line}</span><span hidden id="{pid}">{esc(cmd)}</span>'
               f'{self.copy_btn(pid)}</div>')
        if expected:
            out += f'<p class="sg-exp">{esc(expected)}</p>'
        if muted:
            out += f'<p class="sg-muted">{esc(muted)}</p>'
        return out + "</div>"

    def now(self, test, c):
        if test == "read":
            return self.g({"cmd": "now.read_cmd", "hostname": "now.read_hostname", "copilot_policy": "now.read_copilot_policy"}[c["kind"]])
        if c["status"] == "before_also_fails":
            return self.g("now.before_also_fails")
        return self.g("now.network_git" if c["cmd"].startswith("git ") else "now.network_curl")

    def after(self, test, c):
        """(expected line, muted line or None) after the template."""
        st = c["status"]
        muted = None
        if st == "unconfirmed":
            d = self.lab_checked(test)
            muted = self.g("lab.checked", date=d) if d else self.G["after.unconfirmed"]
        if st in ("works_by_design", "before_also_fails", "not_documented"):
            return self.g("after." + st), None
        if test == "network":
            return self.G["after.network"], muted
        key = {"cmd": "after.read_cmd", "hostname": "after.read_hostname", "copilot_policy": "after.read_copilot_policy"}[c["kind"]]
        return self.G[key], muted

    def boxes(self, when):
        ch = self.t["checks"]
        out = []
        if ch["read"]["kind"] == "none" and ch["network"]["kind"] == "none":
            return [f'<p class="sg-noline">{esc(self.g("no_test"))}</p>']
        for test in ("read", "network"):
            c = ch[test]
            if c["kind"] == "none":
                out.append(f'<p class="sg-noline">{esc(self.g("no_test"))}</p>')
                continue
            if when == "before":
                out.append(self.box(c, self.now(test, c)))
            else:
                exp, muted = self.after(test, c)
                out.append(self.box(c, exp or "", muted))
        return out

    # -- steps
    def step(self, n, title, body, optional=False):
        cls = "sg-num opt" if optional else "sg-num"
        return (f'<li class="sg-step"><span class="{cls}" aria-hidden="true">{n}</span><h2>{esc(title)}</h2>'
                f'<div class="sg-sbody">{"".join(body)}</div></li>')

    def template_text(self):
        T = self.T
        files = [b for b in self.t["blocks"] if b["format"] in COMMENT]
        if self.t.get("intro") == "paste_many":
            blocks = "\n\n".join(f'{COMMENT[b["format"]]} {b["file"]}\n{b["value"]}' for b in files)
            return fill(T["paste.many"], agent=self.name) + "\n\n" + blocks
        if self.t.get("intro") == "vscode_settings":
            return "\n\n".join(b["value"] for b in files)
        return fill(T["paste.one"], agent=self.name, file=files[0]["file"]) + "\n\n" + files[0]["value"]

    def step2(self):
        T, G = self.T, self.G
        body = []
        if self.t.get("intro") == "vscode_settings":
            body.append(f'<p>{esc(T["paste.vscode"])}</p>')
            body.append(self.pre(self.template_text()))
        else:
            body.append(f'<p>{esc(G["s2.p"])}</p>')
            for b in self.t["blocks"]:
                if b["format"] == "ui":
                    body.append(f'<p>{esc(T["ui." + b["value"]])}</p>')
            pid = self.pid()
            body.append(f'<button type="button" class="hbtn primary sg-copytpl" data-copy="{pid}" '
                        f'data-copied="{esc(G["copied"])}">{esc(G["s2.button"])}</button>')
            body.append(f'<details><summary>{esc(G["s2.see"])}</summary><div class="sg-dbody">'
                        f'<pre id="{pid}">{esc(self.template_text())}</pre></div></details>')
            for b in self.t["blocks"]:
                if b["format"] == "env":
                    body.append(f'<p>{esc(T["env." + b["note"]])}</p>')
                    body.append(self.pre(b["value"]))
        body += self.figure(2)
        return self.step(2, self.g("s2.h"), body)

    def step3(self):
        G = self.G
        notes = [n for n in self.t["checks"]["notes"] if n != "gemini_replaced"]
        body = [f'<p>{esc(G["s3.p_agy"] if "agy_ask_means_off" in notes else G["s3.p"])}</p>']
        body += [f'<p class="sg-small">{esc(G["note." + n])}</p>' for n in notes]
        body += self.boxes("after")
        body.append(f'<p class="sg-small">{esc(G["s3.fixed"])}</p>')
        body += self.figure(3, when="despues")
        ts = "".join(f'<li>{code(G["ts." + c])}</li>' for c in self.t["checks"]["troubleshoot"])
        body.append(f'<details><summary>{esc(G["s3.worked"])}</summary><div class="sg-dbody">'
                    f'<p>{esc(G["s3.worked_p"])}</p><ul>{ts}</ul></div></details>')
        return self.step(3, self.g("s3.h"), body)

    def foot(self):
        T, G = self.T, self.G
        out = []
        if "session" in self.t:
            s = self.t["session"]
            parts = [f'<p>{esc(fill(T["session.p"], agent=self.name))}</p>', self.pre(s["command"])]
            for c in s["requires"]:
                parts.append(f'<p>{esc(fill(T["session.requires"], list=T["requires." + c]))}</p>')
            if "/RUTA/DEL/PROYECTO" in s["command"]:
                parts.append(f'<p>{esc(T["session.path"])}</p>')
            out.append(f'<details><summary>{esc(G["fold.session"])}</summary><div class="sg-dbody">{"".join(parts)}</div></details>')
        unc = self.t["uncovered"]
        if unc:
            lis = "".join(f'<li>{code(T["uncovered." + c])}</li>' for c in unc)
            out.append(f'<details><summary>{esc(self.g("fold.uncovered", n=len(unc)))}</summary>'
                       f'<div class="sg-dbody"><ul>{lis}</ul></div></details>')
        out += self.source()
        return f'<div class="sg-foot">{"".join(out)}</div>'

    def source(self):
        T = self.T
        date = map_page.fmt_date(self.t["source"]["accessed_at"], self.lang)
        mk = f'<a href="{esc(self.t["source"]["url"])}" rel="noopener">{esc(maker(self.a))}</a>'
        out = [f'<p class="sg-src">{fill(esc(T["source"]), maker=mk, date=esc(date))}</p>']
        if any(u in self.review for u in template_urls(self.t)):
            out.append(f'<p class="sg-rev">{esc(T["review"])}</p>')
        return out

    def main(self):
        G = self.G
        if self.t["kind"] == "separate_account":
            return self.account()
        s1 = [f'<p>{esc(self.g("s1.p"))}</p>'] + self.boxes("before") + self.figure(1, when="antes")
        steps = [self.step(1, G["s1.h"], s1), self.step2(), self.step3(),
                 self.step(4, self.g("s4.h"), [f'<p>{esc(self.g("s4.p"))}</p>', download(self.lang)], optional=True)]
        return f'<div class="sg-main"><ol class="sg-steps">{"".join(steps)}</ol>{self.foot()}</div>'

    def account(self):
        """GTM-176 §4: no sandbox on this system, another user account (paths checked by the advisor against the
        official help on 16-11)."""
        G = self.G
        home = "dir ~" if self.s == "windows" else "ls ~"
        yours = {"macos": "ls /Users/tu-usuario", "linux": "ls /home/tu-usuario", "windows": r"dir C:\Users\tu-usuario"}[self.s]
        muted = G["after.unconfirmed"] if self.s in ("macos", "windows") else None
        s3 = [f'<p>{esc(G["acc.s3.p"])}</p>', self.box({"kind": "cmd", "cmd": home}, G["acc.home"]),
              self.box({"kind": "cmd", "cmd": yours}, G["acc.yours"], muted), f'<p class="sg-small">{esc(G["acc.net"])}</p>']
        steps = [self.step(1, G["acc.s1.h"], [f'<p>{code(G["acc.s1." + self.s])}</p>']),
                 self.step(2, G["acc.s2.h"], [f'<p>{esc(G["acc.s2.p"])}</p>']),
                 self.step(3, self.g("acc.s3.h"), s3),
                 self.step(4, G["acc.s4.h"], [f'<p>{esc(self.g("acc.s4.p"))}</p>', download(self.lang)], optional=True)]
        return f'<div class="sg-main"><ol class="sg-steps">{"".join(steps)}</ol><div class="sg-foot">{"".join(self.source())}</div></div>'

    def html(self):
        side = side_boxes(self.lang, self.t["kind"] == "separate_account")
        return (f'<section class="sg-combo" id="{self.cid}" data-agent="{self.aid}" data-system="{self.s}">'
                f'<h2 class="sg-combo-h">{esc(self.g("combo"))}</h2><p class="sg-cstatus">{self.status()}</p>'
                f'<div class="sg-cols">{self.main()}{side}</div></section>')


def side_boxes(lang, account=False):
    G = gtexts()[lang]
    first = (f'<div class="sg-box"><h3>{esc(G["side.why.h"])}</h3><p>{esc(G["side.why.p"])}</p></div>' if account else
             f'<div class="sg-box"><h3>{esc(G["side.what.h"])}</h3><p>{esc(G["side.what.p"])}</p></div>')
    return (f'<aside class="sg-side">{first}'
            f'<div class="sg-box"><h3>{esc(G["side.which.h"])}</h3><a href="{sandbox_page.SANDBOX_PATH[lang]}">{esc(G["side.which.link"])}</a></div>'
            f'<div class="sg-box"><h3>{esc(G["side.try.h"])}</h3><a href="{company_page.GUIDE_PATH[lang]}">{esc(G["side.try.link"])}</a></div>'
            "</aside>")


def selector(lang, agents):
    G = gtexts()[lang]
    names = map_page.agent_names([a["agent"] for a in agents], lang)
    ab = "".join(f'<button type="button" class="sg-btn" data-agent="{a["agent"]["id"]}" aria-pressed="false">'
                 f'{esc(names[a["agent"]["id"]])}</button>' for a in agents)
    sb = "".join(f'<button type="button" class="sg-btn" data-system="{s}" aria-pressed="false">{company_page.SYSTEM_NAME[s]}</button>'
                 for s in SYSTEMS)
    ao = f'<option value="">{esc(G["sel.choose"])}</option>' + "".join(
        f'<option value="{a["agent"]["id"]}">{esc(names[a["agent"]["id"]])}</option>' for a in agents)
    so = '<option value=""></option>' + "".join(f'<option value="{s}">{company_page.SYSTEM_NAME[s]}</option>' for s in SYSTEMS)
    picked = f' <span class="sg-picked" hidden>{esc(G["sel.picked"])}</span>'
    return f"""<div class="sg-sel" hidden>
<div class="sg-grp"><p class="sg-lab" id="sg-lab-agent">{esc(G["sel.agent"])}</p><div class="sg-btns" role="group" aria-labelledby="sg-lab-agent">{ab}</div>
<div class="sg-mob"><label for="sg-sel-agent">{esc(G["sel.agent"])}</label><select id="sg-sel-agent">{ao}</select></div></div>
<div class="sg-grp"><p class="sg-lab" id="sg-lab-system">{esc(G["sel.system"])}{picked}</p><div class="sg-btns" role="group" aria-labelledby="sg-lab-system">{sb}</div>
<div class="sg-mob"><label for="sg-sel-system">{esc(G["sel.system"])}{picked}</label><select id="sg-sel-system">{so}</select></div></div>
<p class="sg-status" aria-live="polite"></p>
</div>"""


def article(lang, agents, review, lab=None):
    G = gtexts()[lang]
    T = texts()[lang]
    lab = lab_entries() if lab is None else lab
    items = with_templates(agents)
    combos = []
    for a in items:
        combos.append(f'<span class="sg-anchor" id="{a["agent"]["id"]}"></span>')
        combos += [Combo(a, s, lang, review, lab).html() for s in SYSTEMS]
    none = (f'<div class="sg-none"><div class="sg-cols"><div class="sg-main">'
            f'<p class="sg-noneline">{esc(G["none_chosen"])}</p></div>{side_boxes(lang)}</div></div>')
    return f"""<article class="sg">
<header class="sg-head"><h1>{esc(G["h1"])}</h1><p class="sg-lead">{esc(G["lead"])}</p></header>
{selector(lang, items)}
{none}
{chr(10).join(combos)}
<p class="sg-note">{esc(T["note"])}</p>
</article>"""


def download(lang):
    route, l, alt, mac, mac_label, linux = DOWNLOAD[lang]
    return (f'<div class="dlrow"><a class="sbadge" href="{route}?from=sandbox&amp;os=store" target="_blank" rel="nofollow noopener">'
            f'<img src="/assets/store/microsoft-store-{l}.svg" width="161" height="44" alt="{esc(alt)}"></a>'
            f'<a class="hbtn sec" href="{mac}">{esc(mac_label)}</a><a class="hbtn sec" href="{linux}">Linux</a></div>')


def shell_parts(lang):
    """(head styles and links, header, footer, scripts) of the guide page of the language."""
    s = (SITE / GUIDE_FILE[lang]).read_text(encoding="utf-8")
    style = s[s.index('<link rel="stylesheet"'):s.index("</head>")]
    header = s[s.index("<header>"):s.index("</header>") + len("</header>")]
    footer = s[s.index("<footer>"):s.index("</footer>") + len("</footer>")]
    scripts = s[s.index("</footer>") + len("</footer>"):s.index("</body>")].strip()
    return style, header, footer, scripts


def nav_for_section(block, lang):
    """The guide's navigation with the language links pointing to this section and «Sandbox» as the current page."""
    for o in LANGS:
        if o != lang:
            block = re.sub(r'<a href="[^"]*" hreflang="%s"' % o, f'<a href="{SECTION_PATH[o]}" hreflang="{o}"', block)
    return block.replace(f'<a href="{SECTION_PATH[lang]}">', f'<a href="{SECTION_PATH[lang]}" aria-current="page">')


def page(lang, agents, review):
    G = gtexts()[lang]
    style, header, footer, scripts = shell_parts(lang)
    url = "https://rosmarops.com" + SECTION_PATH[lang]
    title = G["h1"] + " · RosmarOps"
    desc = G["lead"]
    alts = "".join(f'<link rel="alternate" hreflang="{o}" href="https://rosmarops.com{SECTION_PATH[o]}">\n' for o in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="https://rosmarops.com{SECTION_PATH["en"]}">\n'
    ld = json.dumps({"@context": "https://schema.org", "@type": "WebPage", "@id": url + "#page", "url": url, "name": G["h1"],
                     "inLanguage": lang, "isPartOf": {"@id": "https://rosmarops.com/#website"}}, ensure_ascii=False)
    alt = {"en": "RosmarOps logo", "es": "Logotipo de RosmarOps", "ca": "Logotip de RosmarOps"}[lang]
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
{alts}<meta property="og:type" content="article">
<meta property="og:site_name" content="RosmarOps">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="{LOCALE[lang]}">
<meta property="og:image" content="https://rosmarops.com/assets/brand/rosmarops-social.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(alt)}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{ld}</script>
{style.strip()}
<style>
{GUIDE_CSS}
</style>
</head>
<body>
{nav_for_section(header, lang)}

<main><div class="wrap">
{article(lang, agents, review)}
</div></main>

{nav_for_section(footer, lang)}
{scripts}
{GUIDE_SCRIPT}
</body>
</html>
"""


def build(agents, site=SITE):
    review = to_review()
    for lang in LANGS:
        out = Path(site) / SECTION_PATH[lang].strip("/") / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(lang, agents, review), encoding="utf-8")
