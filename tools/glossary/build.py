#!/usr/bin/env python3
"""AP-25 glossary and «i» help (signed by Albert 07-11 12:48).

One source: tools/glossary/terms.json. This script:
  1. writes site/assets/help/glossary.json for the «i» help;
  2. writes the glossary pages (EN /glossary/, ES /es/glosario/, CA /ca/glossari/),
     using the methodology page of each language as the page shell;
  3. adds an «i» after the first use of each term in the pages listed in PAGES
     (body text only, never in headings, links or figures; at most two per block);
  4. links help.css and help.js in every page it touches.

Safe to run again: pages that already carry an «i» for a term are left as they are.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITE = os.path.join(ROOT, 'site')
TERMS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'terms.json'), encoding='utf-8'))['terms']

GLOSS = {'en': '/glossary/', 'es': '/es/glosario/', 'ca': '/ca/glossari/'}
METHOD = {'en': 'methodology/index.html', 'es': 'es/metodologia/index.html', 'ca': 'ca/metodologia/index.html'}
LABEL = {'en': 'What is “{t}”?', 'es': '¿Qué es «{t}»?', 'ca': 'Què és «{t}»?'}
PAGE = {
    'en': ('Glossary', 'The terms RosmarOps uses, in plain words.',
           'The terms RosmarOps uses, in plain words. Next to them on this website you’ll see an «i»: press it and the explanation opens right there, without leaving the page.'),
    'es': ('Glosario', 'Los términos que usa RosmarOps, en palabras llanas.',
           'Los términos que usa RosmarOps, en palabras llanas. En esta web verás una «i» junto a ellos: al pulsarla, la explicación se abre ahí mismo, sin salir de la página.'),
    'ca': ('Glossari', 'Els termes que fa servir RosmarOps, en paraules planeres.',
           'Els termes que fa servir RosmarOps, en paraules planeres. En aquest web veuràs una «i» al costat: si la prems, l’explicació s’obre allà mateix, sense sortir de la pàgina.'),
}
OG_LOCALE = {'en': 'en_US', 'es': 'es_ES', 'ca': 'ca_ES'}

# First use of each term, per language. Matched case-insensitively in body text.
PATTERNS = {
    'en': {'agent': r'AI (?:coding )?agents?', 'credential': r'\bkeys?\b', 'band': r'\bbands?\b',
           'mcp': r'MCP servers?', 'connector': r'\bconnectors?\b', 'repo': r'\brepositor(?:y|ies)\b',
           'training': r'train its models', 'encrypted': r'\bencrypted\b', 'ask': r'without asking'},
    'es': {'agent': r'agentes? de IA', 'credential': r'\bclaves?\b', 'band': r'\bbandas?\b',
           'mcp': r'servidor(?:es)? MCP', 'connector': r'\bconector(?:es)?\b', 'repo': r'\brepositorios?\b',
           'training': r'entrenar sus modelos', 'encrypted': r'\bcifrad[oa]s?\b', 'ask': r'sin preguntarte'},
    'ca': {'agent': r'agents? d(?:\'|&#x27;|’)IA', 'credential': r'\bclaus?\b', 'band': r'\bband(?:a|es)\b',
           'mcp': r'servidors? MCP', 'connector': r'\bconnectors?\b', 'repo': r'\brepositoris?\b',
           'training': r'entrenar els seus models', 'encrypted': r'\bxifra(?:t|da|ts|des)\b', 'ask': r'sense preguntar-te'},
}
# Pages that get the «i», with the terms each one explains.
PAGES = {
    'index.html': ('en', ['agent', 'encrypted']),
    'es/index.html': ('es', ['agent', 'encrypted']),
    'ca/index.html': ('ca', ['agent', 'encrypted']),
    'methodology/index.html': ('en', ['agent', 'credential', 'band', 'mcp', 'connector', 'repo', 'training', 'encrypted']),
    'es/metodologia/index.html': ('es', ['agent', 'credential', 'band', 'mcp', 'connector', 'repo', 'training', 'encrypted']),
    'ca/metodologia/index.html': ('ca', ['agent', 'credential', 'band', 'mcp', 'connector', 'repo', 'training', 'encrypted']),
}
EXCLUDED = {'h1', 'h2', 'h3', 'a', 'figure', 'script', 'style', 'button', 'title', 'nav', 'header', 'footer', 'figcaption', 'code'}
BLOCKS = {'p', 'li', 'dd', 'td'}
ASSETS = ('<link rel="stylesheet" href="/assets/help/help.css?v=1">\n',
          '<script src="/assets/help/help.js?v=1" defer></script>\n')


def term(tid, lang):
    for t in TERMS:
        if t['id'] == tid:
            return t[lang]
    raise KeyError(tid)


def add_assets(s):
    if '/assets/help/help.css' not in s:
        s = s.replace('</head>', ASSETS[0] + '</head>', 1)
    if '/assets/help/help.js' not in s:
        s = s.replace('</body>', ASSETS[1] + '</body>', 1)
    return s


def mark(s, lang, tids):
    start = s.index('<main')
    end = s.index('</main>')
    done = {m for m in re.findall(r'data-gi="([a-z]+)"', s)}
    todo = [t for t in tids if t not in done]
    if not todo:
        return s, []
    # Walk tags and text inside <main>, tracking excluded tags and the current block.
    tok = re.compile(r'<(/?)([a-zA-Z0-9]+)[^>]*?(/?)>')
    stack, inserts, per_block, block_id = [], [], {}, 0
    found = {}
    pos = start
    for m in tok.finditer(s, start, end):
        text = s[pos:m.start()]
        if text and not (set(stack) & EXCLUDED):
            for tid in todo:
                if tid in found:
                    continue
                mm = re.search(PATTERNS[lang][tid], text, re.I)
                if mm and per_block.get(block_id, 0) < 2:
                    found[tid] = (pos + mm.start(), pos + mm.end())
                    per_block[block_id] = per_block.get(block_id, 0) + 1
        closing, name, selfclose = m.group(1), m.group(2).lower(), m.group(3)
        if name in ('br', 'img', 'source', 'meta', 'link', 'input') or selfclose:
            pass
        elif closing:
            if name in stack:
                while stack and stack.pop() != name:
                    pass
        else:
            stack.append(name)
            if name in BLOCKS:
                block_id += 1
        pos = m.end()
    missing = [t for t in todo if t not in found]
    # Apply from the end so positions stay valid; avoid overlaps.
    spans = sorted(found.items(), key=lambda kv: kv[1][0], reverse=True)
    for tid, (a, b) in spans:
        name = term(tid, lang)[0]
        shown = name if len(name) > 1 and name[1].isupper() else name[0].lower() + name[1:]
        label = html.escape(LABEL[lang].format(t=shown), quote=True)
        i = ('<a class="gi" href="%s#%s" data-gi="%s" aria-label="%s"><span aria-hidden="true">i</span></a>'
             % (GLOSS[lang], tid, tid, label))
        s = s[:a] + '<span class="gt">' + s[a:b] + i + '</span>' + s[b:]
    return s, missing


def glossary_page(lang):
    shell = open(os.path.join(SITE, METHOD[lang]), encoding='utf-8').read()
    title, desc, intro = PAGE[lang]
    url = 'https://rosmarops.com' + GLOSS[lang]
    s = shell
    s = re.sub(r'<title>.*?</title>', '<title>%s</title>' % html.escape(title + ' · RosmarOps'), s, count=1)
    s = re.sub(r'(<meta name="description" content=")[^"]*(")', lambda m: m.group(1) + html.escape(desc, quote=True) + m.group(2), s, count=1)
    s = re.sub(r'(<meta property="og:description" content=")[^"]*(")', lambda m: m.group(1) + html.escape(desc, quote=True) + m.group(2), s, count=1)
    s = re.sub(r'(<meta property="og:title" content=")[^"]*(")', lambda m: m.group(1) + html.escape(title, quote=True) + m.group(2), s, count=1)
    s = re.sub(r'(<meta property="og:type" content=")[^"]*(")', r'\1website\2', s, count=1)
    s = re.sub(r'(<meta property="og:url" content=")[^"]*(")', r'\g<1>' + url + r'\2', s, count=1)
    s = re.sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="%s">' % url, s, count=1)
    for l2 in ('en', 'es', 'ca'):
        s = re.sub(r'<link rel="alternate" hreflang="%s" href="[^"]*">' % l2,
                   '<link rel="alternate" hreflang="%s" href="https://rosmarops.com%s">' % (l2, GLOSS[l2]), s, count=1)
    s = re.sub(r'<link rel="alternate" hreflang="x-default" href="[^"]*">',
               '<link rel="alternate" hreflang="x-default" href="https://rosmarops.com%s">' % GLOSS['en'], s, count=1)
    ld = {"@context": "https://schema.org", "@type": "DefinedTermSet", "@id": url + "#set", "name": title,
          "inLanguage": lang, "url": url,
          "hasDefinedTerm": [{"@type": "DefinedTerm", "@id": url + "#" + t['id'], "name": t[lang][0],
                              "description": t[lang][1]} for t in TERMS]}
    s = re.sub(r'<script type="application/ld\+json">.*?</script>',
               lambda m: '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>', s, count=1, flags=re.S)
    # Language links in header and footer point to the other glossaries.
    meth = {'en': ['https://rosmarops.com/methodology/', '/methodology/'], 'es': ['/es/metodologia/'], 'ca': ['/ca/metodologia/']}
    for l2, hrefs in meth.items():
        for h in hrefs:
            s = s.replace('href="%s" hreflang="%s"' % (h, l2), 'href="%s" hreflang="%s"' % (GLOSS[l2], l2))
    items = ''.join('<dt id="%s">%s</dt>\n<dd>%s</dd>\n' % (t['id'], html.escape(t[lang][0]), html.escape(t[lang][1])) for t in TERMS)
    body = ('<article class="doc"><h1>%s</h1>\n<p>%s</p>\n<dl class="gloss">\n%s</dl>\n</article>\n'
            % (html.escape(title), html.escape(intro), items))
    s = re.sub(r'<article class="doc">.*?</article>\n?', lambda m: body, s, count=1, flags=re.S)
    s = s.replace('<link rel="stylesheet" href="/assets/help/help.css?v=1">\n', '')
    s = s.replace('<script src="/assets/help/help.js?v=1" defer></script>\n', '')
    s = s.replace('</head>', ASSETS[0] + '</head>', 1)
    out = os.path.join(SITE, GLOSS[lang].strip('/'), 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(s)
    return out


def sitemap():
    p = os.path.join(SITE, 'sitemap-pages.xml')
    s = open(p, encoding='utf-8').read()
    if '/glossary/</loc>' in s:
        return
    alts = ''.join('<xhtml:link rel="alternate" hreflang="%s" href="https://rosmarops.com%s"/>' % (l, GLOSS[l]) for l in ('en', 'es', 'ca'))
    rows = ''.join('  <url><loc>https://rosmarops.com%s</loc><lastmod>2026-11-07</lastmod>%s</url>\n' % (GLOSS[l], alts) for l in ('en', 'es', 'ca'))
    s = s.replace('</urlset>', rows + '</urlset>', 1)
    open(p, 'w', encoding='utf-8').write(s)


def main():
    out = {l: {t['id']: t[l] for t in TERMS} for l in ('en', 'es', 'ca')}
    json.dump(out, open(os.path.join(SITE, 'assets/help/glossary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for l in ('en', 'es', 'ca'):
        print('glossary', glossary_page(l))
    sitemap()
    bad = 0
    for rel, (lang, tids) in PAGES.items():
        p = os.path.join(SITE, rel)
        s = open(p, encoding='utf-8').read()
        s, missing = mark(s, lang, tids)
        s = add_assets(s)
        open(p, 'w', encoding='utf-8').write(s)
        print(rel, 'missing:' if missing else 'ok', ' '.join(missing))
        bad += bool(missing)
    return 0


if __name__ == '__main__':
    sys.exit(main())
