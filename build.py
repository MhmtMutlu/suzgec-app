#!/usr/bin/env python3
"""Builds the İçgör website into static HTML at the repository root (GitHub Pages serves it as is).

    python3 build.py            # build + check every internal link and anchor
    python3 build.py --sync     # first copy the legal texts from ../suzgec/docs/legal/v2

Pages: landing (/), gizlilik, kosullar, katki-kosullari, kvkk, destek, 404. Legal bodies are Markdown in src/legal/
(written with the lawyers in the app repo) and rendered by the small converter below: headings, paragraphs, lists,
tables, bold/italic, links and code. Paths are relative so the site works on icgor.mm-apps.com (GitHub Pages, custom domain) and on a
custom domain. No cookies, no analytics, no third-party requests (system fonts only).
"""
from __future__ import annotations

import datetime
import hashlib
import html
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "src"
LEGAL_SRC = ROOT.parent / "suzgec" / "docs" / "legal" / "v2"

# Name in one place. Renamed from "Süzgeç" on 8 November 2026 (no trademark filing).
APP_NAME = "İçgör"
SITE_URL = "https://icgor.mm-apps.com/"
CONTACT = "destek@mm-apps.com"
UPDATED = "16 Kasım 2026"

APP_STORE_LIVE = True  # 1.0.0 approved and live (14 Nov 2026)
APP_ID = "6830374026"
APP_STORE_URL = f"https://apps.apple.com/tr/app/id{APP_ID}"
STORE_NAME = "İçgör: Katkı Maddesi & Barkod"
DEVELOPER = "mm-apps"
DEVELOPER_URL = "https://mm-apps.com/"

# Two separate switches, because they go live on different days (App Review vs. Apple's scheduled price change):
# APP_RELEASE: the app version on the App Store; FEATURES are what it really does.
# PRICE_SET: the price the App Store charges today (the 1.1 prices start 18 Nov 2026 at the earliest).
# When APP_RELEASE becomes "1.1", also run `python3 build.py --sync` so the legal texts match the app.
APP_RELEASE = "1.0"
PRICE_SET = "1.0"
FEATURES = {
    "1.0": {"free": 3, "profiles": 6, "tracking": False},
    "1.1": {"free": 10, "profiles": 10, "tracking": True},
}
PRICES = {"1.0": ("₺84,99", "₺499,99"), "1.1": ("₺49,99", "₺299,99")}
PRICE_MONTHLY, PRICE_YEARLY = PRICES[PRICE_SET]
FREE_MONTHLY_NEW = FEATURES[APP_RELEASE]["free"]
FAMILY_PROFILES = FEATURES[APP_RELEASE]["profiles"]
TRACKING = FEATURES[APP_RELEASE]["tracking"]

# One definition sentence, reused on the home page, JSON-LD, llms.txt and the press page (GEO: same facts everywhere).
DEFINITION = (f"{APP_NAME}, iPhone için ücretsiz indirilebilen bir barkod ve etiket okuyucudur: gıda, kozmetik, temizlik "
              "ürünü ve kıyafet etiketini okur; katkı maddelerini (E kodları) ve 14 alerjeni kaynağıyla gösterir, "
              "Beslenme Skoru'nu hesaplar ve sonucu ailedeki her kişi için ayrı verir.")

# The app's own rule files (written and source-checked in the app repo); `--sync` copies them to data/rules.
RULES_SRC = ROOT.parent / "suzgec" / "Suzgec" / "Resources" / "Rules"
RULES = ROOT / "data" / "rules"
RULE_FILES = ("additives_tr.json", "allergens_eu14.json", "sources.json", "beslenme_skoru_tr.json")
CSS_VERSION = hashlib.sha256((ROOT / "assets" / "site.css").read_bytes()).hexdigest()[:10]

LEGAL_PAGES = [
    # (slug, source file, nav label, description)
    ("gizlilik", "gizlilik-politikasi.md", "Gizlilik", "İçgör gizlilik politikası: hangi bilgi nerede kalır, ne kadar tutulur."),
    ("kosullar", "kullanim-kosullari.md", "Kullanım koşulları", "İçgör kullanım koşulları: hizmetin kapsamı, abonelik, ödeme ve iptal, sorumluluk ve iletişim."),
    ("katki", "katki-kosullari.md", "Katkı koşulları", "İçgör'e ürün bilgisi ve fotoğrafı gönderme koşulları."),
    ("kvkk", "kvkk-aydinlatma.md", "KVKK", "İçgör için 6698 sayılı KVKK kapsamında aydınlatma metni: hangi veri, hangi amaçla, ne kadar süre işlenir."),
]


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


# ------------------------------------------------------------------------------------------------ markdown
INLINE_CODE = re.compile(r"`([^`]+)`")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
BOLD = re.compile(r"\*\*(.+?)\*\*")
ITALIC = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")
BARE_URL = re.compile(r"(?<![\"'>(=])\b(https://[^\s<)]+[^\s<).,;:])")
EMAIL = re.compile(r"(?<![\w.:/>-])([\w.+-]+@[\w-]+\.[\w.-]+\w)")
PLACEHOLDER = re.compile(r"\[([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ0-9 /.,-]{2,})\]")


def site_href(url: str, depth: int) -> str:
    """Absolute links to this site become relative, so the build works on any host."""
    if url.startswith(SITE_URL):
        rest = url[len(SITE_URL):]
        return "../" * depth + rest if rest else ("../" * depth or "./")
    return url


def inline(text: str, depth: int) -> str:
    codes: list[str] = []

    def keep_code(match: re.Match) -> str:
        codes.append(f"<code>{esc(match.group(1))}</code>")
        return f"\x00{len(codes) - 1}\x00"

    text = INLINE_CODE.sub(keep_code, text)
    links: list[str] = []

    def keep_link(match: re.Match) -> str:
        label, url = match.group(1), site_href(match.group(2), depth)
        external = url.startswith("http")
        attrs = ' rel="noopener"' if external else ""
        links.append(f'<a href="{esc(url)}"{attrs}>{esc(label)}</a>')
        return f"\x01{len(links) - 1}\x01"

    text = LINK.sub(keep_link, text)
    text = esc(text)
    text = PLACEHOLDER.sub(lambda m: f'<mark class="todo">[{m.group(1)}]</mark>', text)
    text = BOLD.sub(r"<strong>\1</strong>", text)
    text = ITALIC.sub(r"<em>\1</em>", text)
    text = BARE_URL.sub(lambda m: f'<a href="{m.group(1)}" rel="noopener">{m.group(1)}</a>', text)
    text = EMAIL.sub(lambda m: f'<a href="mailto:{m.group(1)}">{m.group(1)}</a>', text)
    text = re.sub("\x01(\\d+)\x01", lambda m: links[int(m.group(1))], text)
    return re.sub("\x00(\\d+)\x00", lambda m: codes[int(m.group(1))], text)


def slug(text: str, used: set[str]) -> str:
    table = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    base = re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", text).translate(table).lower()).strip("-") or "bolum"
    candidate, n = base, 2
    while candidate in used:
        candidate, n = f"{base}-{n}", n + 1
    used.add(candidate)
    return candidate


def markdown(source: str, depth: int) -> tuple[str, str, list[tuple[str, str]]]:
    """Returns (title, body html, [(anchor, h2 text)]). The first H1 is the page title."""
    lines = source.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    toc: list[tuple[str, str]] = []
    used: set[str] = set()
    title = APP_NAME
    i = 0
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            out.append(f"<p>{inline(' '.join(paragraph), depth)}</p>")
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        heading = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if not stripped:
            flush()
            i += 1
        elif heading:
            flush()
            level, text = len(heading.group(1)), heading.group(2).strip()
            if level == 1 and title == APP_NAME:
                title = text
            else:
                level = max(level, 2)
                anchor = slug(text, used)
                if level == 2:
                    toc.append((anchor, text))
                out.append(f'<h{level} id="{anchor}">{inline(text, depth)}</h{level}>')
            i += 1
        elif stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-{3,}", lines[i + 1].strip()):
            flush()
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head = "".join(f'<th scope="col">{inline(c, depth)}</th>' for c in header)
            body = "".join("<tr>" + "".join(f"<td>{inline(c, depth)}</td>" for c in row) + "</tr>" for row in rows)
            out.append(f'<div class="table"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
        elif re.match(r"^([-*]|\d+[.)])\s+", stripped):
            flush()
            ordered = bool(re.match(r"^\d", stripped))
            items: list[str] = []
            while i < len(lines) and re.match(r"^\s*([-*]|\d+[.)])\s+", lines[i]):
                item = re.sub(r"^\s*([-*]|\d+[.)])\s+", "", lines[i]).strip()
                i += 1
                while i < len(lines) and lines[i].startswith("  ") and lines[i].strip() and not re.match(r"^\s*([-*]|\d+[.)])\s+", lines[i]):
                    item += " " + lines[i].strip()
                    i += 1
                items.append(f"<li>{inline(item, depth)}</li>")
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>{''.join(items)}</{tag}>")
        elif stripped.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f"<blockquote><p>{inline(' '.join(quote), depth)}</p></blockquote>")
        elif re.match(r"^-{3,}$", stripped):
            flush()
            out.append("<hr>")
            i += 1
        else:
            paragraph.append(stripped)
            i += 1
    flush()
    return title, "\n".join(out), toc


# ------------------------------------------------------------------------------------------------ layout
def store_badge(depth: int, compact: bool = False) -> str:
    label = "App Store'dan indir" if APP_STORE_LIVE else "App Store'da çok yakında"
    icon = (
        '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M16.4 12.6c0-2.4 2-3.5 2.1-3.6-1.1-1.7-2.9-1.9-3.5-1.9-1.5-.2-2.9.9-3.7.9-.8 0-1.9-.9-3.2-.8-1.6 0-3.1 1-4 2.4-1.7 3-.4 7.4 1.2 9.8.8 1.2 1.8 2.5 3 2.4 1.2 0 1.7-.8 3.1-.8 1.5 0 1.9.8 3.2.8 1.3 0 2.1-1.2 2.9-2.4.9-1.4 1.3-2.7 1.3-2.8 0 0-2.4-1-2.4-4zM14 5.4c.7-.8 1.1-1.9 1-3-1 0-2.1.7-2.8 1.5-.6.7-1.2 1.8-1 2.9 1.1.1 2.1-.6 2.8-1.4z"/></svg>'
    )
    cls = "badge-store" + (" compact" if compact else "")
    if APP_STORE_LIVE:
        return f'<a class="{cls}" href="{APP_STORE_URL}" rel="noopener">{icon}<span>{label}</span></a>'
    return f'<span class="{cls} soon" aria-label="{label}">{icon}<span>{label}</span></span>'


def mark_svg(size: int = 28) -> str:
    """The eye mark ("İçini gör."): the app icon's eye and iris (suzgec/design/DESIGN.md 6)."""
    return (
        f'<svg class="mark" viewBox="0 0 48 48" width="{size}" height="{size}" aria-hidden="true">'
        '<rect width="48" height="48" rx="13" fill="currentColor"/>'
        '<path d="M7 24C13 12.5 35 12.5 41 24C35 35.5 13 35.5 7 24Z" fill="none" stroke="var(--on-mark)" stroke-width="3" stroke-linejoin="round"/>'
        '<circle cx="24" cy="24" r="6.6" fill="var(--wheat)"/><circle cx="24" cy="24" r="2.9" fill="currentColor"/></svg>'
    )


def jsonld(nodes: list[dict]) -> str:
    """One @graph per page; `</` is escaped so text can never close the script element."""
    data = json.dumps({"@context": "https://schema.org", "@graph": nodes}, ensure_ascii=False, separators=(",", ":"))
    data = data.replace("</", "<\\/")
    return f'<script type="application/ld+json">{data}</script>'


ORG_ID = f"{DEVELOPER_URL}#org"
APP_NODE_ID = f"{SITE_URL}#app"


def common_nodes(title: str, description: str, canonical: str, crumbs: list[tuple[str, str]],
                 page_type: str | list[str] = "WebPage", extra: dict | None = None) -> list[dict]:
    """Organization, WebSite, WebPage and BreadcrumbList; every text here is also visible on the page."""
    url = f"{SITE_URL}{canonical}"
    page_node = {"@type": page_type, "@id": f"{url}#webpage", "url": url, "name": title, "description": description,
                 "inLanguage": "tr", "isPartOf": {"@id": f"{SITE_URL}#site"}, "about": {"@id": APP_NODE_ID}}
    nodes = [
        {"@type": "Organization", "@id": ORG_ID, "name": DEVELOPER, "url": DEVELOPER_URL, "email": CONTACT},
        {"@type": "WebSite", "@id": f"{SITE_URL}#site", "url": SITE_URL, "name": APP_NAME, "inLanguage": "tr",
         "publisher": {"@id": ORG_ID}},
        page_node,
    ]
    if crumbs:
        page_node["breadcrumb"] = {"@id": f"{url}#breadcrumb"}
        items = []
        for i, (name, path) in enumerate(crumbs, start=1):
            item = {"@type": "ListItem", "position": i, "name": name}
            if i < len(crumbs):
                item["item"] = f"{SITE_URL}{path}"
            items.append(item)
        nodes.append({"@type": "BreadcrumbList", "@id": f"{url}#breadcrumb", "itemListElement": items})
    if extra:
        page_node.update(extra)
    return nodes


def breadcrumb_html(crumbs: list[tuple[str, str]], depth: int) -> str:
    up = "../" * depth
    parts = [f'<a href="{up}{path}">{esc(name)}</a>' if i < len(crumbs) - 1 else f'<span aria-current="page">{esc(name)}</span>'
             for i, (name, path) in enumerate(crumbs)]
    sep = ' <span aria-hidden="true">›</span> '
    return f'<nav class="crumbs" aria-label="Sayfa yolu">{sep.join(parts)}</nav>'


def page(title: str, description: str, body: str, depth: int, canonical: str, active: str | None = None,
         absolute: bool = False, graph: list[dict] | None = None, noindex: bool = False) -> str:
    """`absolute` is for 404.html, which GitHub Pages serves at whatever path was requested."""
    up = SITE_URL if absolute else "../" * depth
    home = up or "./"
    nav = [("", "Ürün"), ("katki-maddeleri/", "Katkı maddeleri"), ("beslenme-skoru/", "Beslenme Skoru"),
           ("destek/", "Destek")]
    links = "".join(
        f'<a href="{up}{path}"{" aria-current=\"page\"" if active == path else ""}>{label}</a>' for path, label in nav
    )
    legal_links = "".join(f'<a href="{up}{s}/">{label}</a>' for s, _, label, _ in LEGAL_PAGES)
    guide_links = "".join(f'<a href="{up}{path}">{esc(name)}</a>' for path, name, _ in GUIDES)
    full_title = title if title.startswith(APP_NAME) else f"{title} · {APP_NAME}"
    robots = ('<meta name="robots" content="noindex">\n' if noindex
              else f'<link rel="canonical" href="{SITE_URL}{canonical}">\n')
    structured = "" if noindex or graph is None else jsonld(graph) + "\n"
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#0D4A4C">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'self'; img-src 'self' data:; script-src 'self'; base-uri 'none'; form-action 'none'">
{robots}<meta name="apple-itunes-app" content="app-id={APP_ID}">
<meta property="og:site_name" content="{APP_NAME}">
<meta property="og:locale" content="tr_TR">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_URL}{canonical}">
<meta property="og:image" content="{SITE_URL}assets/og.png">
<meta property="og:image:alt" content="{APP_NAME} logosu: İçini gör.">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{up}assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{up}assets/apple-touch-icon.png">
<link rel="stylesheet" href="{up}assets/site.css?v={CSS_VERSION}">
{structured}</head>
<body>
<a class="skip" href="#icerik">İçeriğe geç</a>
<header class="top">
  <div class="wrap top-row">
    <a class="brand" href="{home}">{mark_svg()}<span>{APP_NAME}</span></a>
    <nav aria-label="Site">{links}</nav>
  </div>
</header>
<main id="icerik">
{body}
</main>
<footer class="foot">
  <div class="wrap foot-grid">
    <div>
      <a class="brand" href="{home}">{mark_svg(24)}<span>{APP_NAME}</span></a>
      <p class="foot-def">{esc(DEFINITION)}</p>
      <p class="foot-note">{APP_NAME} bir bilgi aracıdır; tıbbi, diyet veya alerji tavsiyesi vermez. Alerjin varsa her zaman ambalajdaki etiketi okuyup kendi doktoruna danış.</p>
    </div>
    <nav class="foot-links" aria-label="Rehberler">{guide_links}<a href="{up}basin/">Basın</a></nav>
    <nav class="foot-links" aria-label="Yasal">{legal_links}<a href="{up}destek/">Destek</a></nav>
    <div class="foot-small">
      <p>Ürün verisinin bir kısmı <a href="https://world.openfoodfacts.org" rel="noopener">Open Food Facts</a> katkıcılarındandır (<a href="https://opendatacommons.org/licenses/odbl/1-0/" rel="noopener">ODbL</a>).</p>
      <p>Apple, App Store ve iPhone, Apple Inc.'in ticari markalarıdır. {APP_NAME}; Sağlık Bakanlığı veya başka bir kurumla bağlantılı değildir, onların onayını taşımaz.</p>
      <p>© 2026 Mehmet Mutlu · <a href="mailto:{CONTACT}">{CONTACT}</a> · Bu site çerez ve analiz aracı kullanmaz.</p>
    </div>
  </div>
</footer>
</body>
</html>
"""


# ------------------------------------------------------------------------------------------------ landing
def landing() -> str:
    label = """<div class="label-card" aria-hidden="true">
  <p class="label-title">İçindekiler</p>
  <p class="label-text">Tam buğday unu (%42), şeker, bitkisel yağ (palm), <span class="hit">buğday glüteni</span>, glikoz şurubu, kabartıcılar (<span class="hit">E500</span>, E503), <span class="hit">süt tozu</span>, tuz, aroma verici, emülgatör (<span class="hit">soya lesitini</span>). <span class="hit soft">Fındık izi içerebilir.</span></p>
  <p class="label-meta">Hayali bir ürün etiketi · 200 g</p>
</div>"""
    rows = [
        ("A", "Ada", "6 yaş · süt alerjisi", "Süt içerir", "personal"),
        ("D", "Deniz", "Çölyak", "Gluten içerir", "personal"),
        ("M", "Mert", "Genel", "Çakışma yok", "ok"),
    ]
    result_rows = "".join(
        f'<li><span class="avatar a-{i}">{a}</span><span class="who"><b>{esc(n)}</b><small>{esc(d)}</small></span>'
        f'<span class="verdict v-{tone}">{esc(v)}</span></li>'
        for i, (a, n, d, v, tone) in enumerate(rows)
    )
    sieve = f"""<div class="sieve" aria-label="Örnek: aynı etiket, aile üyesine göre farklı sonuç">
  {label}
  <div class="mesh" aria-hidden="true"><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
  <div class="result-card">
    <p class="result-head"><span class="score s-c" aria-label="İçgör hesabı C">C</span><span><b>Tam Buğday Bisküvi</b><small>İçgör hesabı · 3 kaynak</small></span></p>
    <ul class="family">{result_rows}</ul>
  </div>
</div>"""

    steps = [
        ("Okut", "Barkodu kameraya tut ya da numarayı yaz. Ürün yoksa etiketin fotoğrafını çek; yazıyı telefonun kendisi okur."),
        ("İncele", "İçindekiler, katkı maddeleri ve besin değerleri; ailedeki her profilin alerjen, diyet ve hassasiyetleriyle tek tek karşılaştırılır."),
        ("Gör", "Her kişi için ayrı bir satır: neyle çakıştığı, neden ve bunu hangi kaynağın söylediği. Korkutmadan, abartmadan."),
    ]
    step_html = "".join(
        f'<li><span class="step-n">{i + 1}</span><h3>{esc(t)}</h3><p>{esc(d)}</p></li>' for i, (t, d) in enumerate(steps)
    )

    kinds = [
        ("Gıda", "Beslenme skoru (Bakanlığın yayımladığı yönteme göre İçgör hesaplar), katkı maddeleri ve AB'nin 14 alerjeni.", "food"),
        ("Kozmetik", "İçerik listesi (INCI) AB Kozmetik Tüzüğü eklerindeki kayıtlarla eşleştirilir; parfüm alerjenleri ayrıca gösterilir.", "beauty"),
        ("Temizlik", "Etiketteki deterjan ve CLP bilgileri sade bir dille özetlenir; puan verilmez.", "home"),
        ("Kıyafet etiketi", "Elyaf yüzdeleri okunur, etiketteki sertifika ibareleri yazıldığı gibi gösterilir.", "cloth"),
    ]
    kind_icons = {
        "food": '<path d="M7 4v7a3 3 0 0 0 6 0V4M10 4v16M17 4c-2 2-2 6 0 8v8" />',
        "beauty": '<path d="M9 3h6v4H9zM8 7h8l1 14H7z" />',
        "home": '<path d="M6 9h12l-1 12H7zM9 9V5h6v4M12 3v2" />',
        "cloth": '<path d="M8 3l-5 4 3 4 2-1v11h8V10l2 1 3-4-5-4a4 4 0 0 1-8 0z" />',
    }
    kind_html = "".join(
        f'<li class="kind"><svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{kind_icons[k]}</svg>'
        f"<h3>{esc(t)}</h3><p>{esc(d)}</p></li>"
        for t, d, k in kinds
    )

    sources = [
        ("Sağlık Bakanlığı", "Beslenme Skoru Rehberi eşikleri"),
        ("AB 1333/2008", "Gıda katkı maddeleri"),
        ("AB 1169/2011", "14 alerjen ve etiket bilgisi"),
        ("AB 1223/2009", "Kozmetik ürünler tüzüğü"),
        ("AB 648/2004 · 1272/2008", "Deterjan ve CLP"),
        ("Open Food Facts", "Açık ürün veritabanı (ODbL)"),
    ]
    source_html = "".join(f"<li><b>{esc(a)}</b><span>{esc(b)}</span></li>" for a, b in sources)

    privacy = [
        ("Hesap yok", "Ad, e-posta, telefon istemeyiz. Giriş ekranı yok."),
        ("Profiller telefonda", "Alerjen, hamilelik ve diyet bilgileri iCloud'a da, bize de gitmez."),
        ("Reklam ve izleme yok", "Reklam kimliği, analiz aracı, üçüncü taraf takipçi kullanmayız."),
        ("Katkı isteğe bağlı", "Bulunamayan ürünü göndermek senin seçimin; gönderilen bilgi kimseyle ilişkilendirilmez."),
    ]
    privacy_html = "".join(f"<li><h3>{esc(a)}</h3><p>{esc(b)}</p></li>" for a, b in privacy)

    faq = [
        ("İçgör bir ürünün sağlıklı olup olmadığını söyler mi?",
         "Hayır. İçgör etikette yazanı okunur hâle getirir, profillerinle çakışan içerikleri işaretler ve her bulgunun kaynağını gösterir. Karar her zaman senindir; alerji ve sağlık konularında etiketin kendisi ve doktorun esastır."),
        ("“İçgör hesabı” resmi bir puan mı?",
         "Hayır. Sağlık Bakanlığı'nın yayımladığı Beslenme Skoru Rehberi'ndeki yönteme göre uygulama içinde hesaplanır. Bakanlığın onayı ya da ürüne verilmiş resmi bir not değildir; bazı ürün grupları (bal, sade süt ürünleri, bebek mamaları gibi) bu yüzden puanlanmaz."),
        ("Ürün bulunamazsa ne olur?",
         "Etiketin fotoğrafını çekersin; yazıyı telefonun kendisi okur, sen kontrol edip kaydedersin. İstersen ürünü, kimliğinle ilişkilendirilmeden ve moderasyondan geçtikten sonra herkesin kullanımına açılmak üzere gönderebilirsin."),
        ("Ücretsiz sürümde neler var?",
         f"Her ay {FREE_MONTHLY_NEW} yeni ürün, bir profil ve geçmişindeki ürünlere sınırsız erişim. İçgör Aile ile tarama sınırı kalkar, {FAMILY_PROFILES} profile kadar aile ekleyebilir, listenin skor dağılımını ve haftalık özeti kullanabilirsin."),
        ("Katkı maddesi (E kodu) nasıl sorgulanır?",
         "Ürünün barkodunu okut ya da içindekiler listesinin fotoğrafını çek. İçgör etiketteki E kodlarını ve adlarını bulur; her maddenin ne işe yaradığını, Türk Gıda Kodeksi'ndeki durumunu ve kaynağını gösterir. Tek tek maddeler için sitedeki katkı maddeleri rehberine de bakabilirsin."),
        ("Besin değerlerini ve içindekileri fotoğraftan okuyabilir mi?",
         "Evet. Ürün kayıtlı değilse ya da bilgisi eksikse etiketin fotoğrafını çekersin; içindekiler ve besin değerleri tablosu telefonun kendisinde okunur, sen kontrol edip onaylarsın. Fotoğraf yalnızca sen göndermeyi seçersen telefondan çıkar."),
        ("İnternet olmadan çalışır mı?",
         "Daha önce baktığın ürünler internetsiz de açılır. Yeni bir barkod için bağlantı gerekir; etiket fotoğrafından okuma ise tamamen telefonda yapılır."),
        ("Verilerimi nasıl silerim?",
         "Profilleri Aile ekranından, geçmişi Ayarlar > Veriler'den silebilirsin. Uygulamayı kaldırdığında telefondaki her şey silinir; sunucumuzda sana ait bir kayıt yoktur."),
    ]
    if TRACKING:
        faq.insert(3, ("Gönderdiğim bilginin durumunu görebilir miyim?",
                       "Evet. Ayarlar > Katkılarım ekranında gönderdiğin ürün bilgilerinin incelemede mi, onaylandı mı yoksa reddedildi mi olduğunu görürsün. Her gönderim için telefonunda rastgele bir takip numarası oluşur; hesap veya cihaz kimliği kullanılmaz."))
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq)

    body = f"""
<section class="hero">
  <div class="wrap hero-grid">
    <div class="hero-copy">
      <p class="eyebrow">Katkı maddesi · alerjen · Beslenme Skoru · etiket okuma</p>
      <h1><em>İçini gör.</em> Bir kez okut, ailendeki herkes için ayrı ayrı anlatsın.</h1>
      <p class="lede">{APP_NAME}, barkodu okuttuğun ürünün içindekiler listesini, katkı maddelerini (E kodları) ve besin değerlerini okur; ailendeki her kişinin alerjen, diyet ve hassasiyetleriyle karşılaştırır. Ne bulduysa sakin bir dille ve kaynağıyla söyler.</p>
      <div class="cta">{store_badge(0)}<a class="link-arrow" href="#nasil">Nasıl çalışır</a></div>
      <ul class="pills" aria-label="Öne çıkanlar"><li>Hesap yok</li><li>Reklam yok</li><li>Profiller telefonda kalır</li></ul>
    </div>
    {sieve}
  </div>
</section>

<section class="band" id="nasil" aria-labelledby="nasil-baslik">
  <div class="wrap">
    <p class="eyebrow">Nasıl çalışır</p>
    <h2 id="nasil-baslik">Üç adım, bir damla gürültü yok.</h2>
    <ol class="steps">{step_html}</ol>
  </div>
</section>

<section class="wrap split-section" aria-labelledby="aile-baslik">
  <div>
    <p class="eyebrow">Aile profilleri</p>
    <h2 id="aile-baslik">Aynı paket, her kişiye ayrı okuma.</h2>
    <p>Çölyaklı bir eş, süt alerjisi olan bir çocuk, hamile bir anne, vegan bir genç. Her biri için profil oluşturursun; {APP_NAME} tek taramada hepsine ayrı cevap verir.</p>
    <ul class="checks">
      <li>AB'nin 14 alerjeni ve iz uyarıları ayrı ayrı</li>
      <li>Hamilelik, vegan, vejetaryen, glutensiz ve helal hassasiyeti</li>
      <li>Belirsiz ifadeler (“aroma verici”, “bitkisel yağ”) açıkça “belirsiz” diye işaretlenir</li>
    </ul>
  </div>
  <figure class="quote-card">
    <blockquote>“Süt içerir” bir yargı değil, bir hatırlatmadır: Etiketteki bir içerik, profilde işaretlediğin bir şeyle eşleşiyor. Neyle eşleştiğini ve bunu nereden bildiğimizi hemen altında görürsün. Etikette bilgi yoksa “Çakışma yok” demeyiz, “bilgi yok” deriz.</blockquote>
    <figcaption>İçgör'ün dili</figcaption>
  </figure>
</section>

<section class="band band-soft" aria-labelledby="tur-baslik">
  <div class="wrap">
    <p class="eyebrow">Sadece gıda değil</p>
    <h2 id="tur-baslik">Mutfaktan banyoya, dolaba kadar.</h2>
    <ul class="kinds">{kind_html}</ul>
  </div>
</section>

<section class="wrap" aria-labelledby="rehber-baslik">
  <p class="eyebrow">Rehberler</p>
  <h2 id="rehber-baslik">Etikette ne yazdığını anlamak için.</h2>
  <ul class="guides">{guides_html()}</ul>
</section>

<section class="wrap split-section" aria-labelledby="kaynak-baslik">
  <div>
    <p class="eyebrow">Kaynak gösterir</p>
    <h2 id="kaynak-baslik">Her bulgunun altında bir dipnot.</h2>
    <p>{APP_NAME} kendi kanaatini değil, yayımlanmış mevzuatı ve açık veriyi kullanır. Bir içeriğe neden not düştüğünü merak edersen kaynağı bir dokunuş uzağındadır.</p>
  </div>
  <ul class="sources">{source_html}</ul>
</section>

<section class="band band-deep" aria-labelledby="gizlilik-baslik">
  <div class="wrap">
    <p class="eyebrow">Gizlilik</p>
    <h2 id="gizlilik-baslik">Ailenin bilgisi sende kalır.</h2>
    <ul class="privacy">{privacy_html}</ul>
    <p class="band-link"><a href="gizlilik/">Gizlilik politikasının tamamı</a></p>
  </div>
</section>

<section class="wrap" aria-labelledby="fiyat-baslik">
  <p class="eyebrow">Fiyat</p>
  <h2 id="fiyat-baslik">Önce dene, gerekirse aileye geç.</h2>
  <div class="plans">
    <article class="plan">
      <h3>Ücretsiz</h3>
      <p class="price">₺0</p>
      <ul><li>Her ay {FREE_MONTHLY_NEW} yeni ürün</li><li>1 profil</li><li>Geçmişteki ürünlere sınırsız bakış</li><li>Etiket fotoğrafından okuma</li></ul>
    </article>
    <article class="plan plan-main">
      <h3>İçgör Aile</h3>
      <p class="price">{PRICE_YEARLY}<small> / yıl</small></p>
      <p class="price-alt">ya da {PRICE_MONTHLY} / ay · 1 hafta ücretsiz deneme</p>
      <ul><li>Sınırsız tarama</li><li>{FAMILY_PROFILES} profile kadar aile</li><li>Liste ve haftalık özet</li><li>Tüm cihazlarında, Aile Paylaşımı ile</li></ul>
    </article>
  </div>
  <p class="fine">Ödeme ve iptal Apple hesabın üzerinden yapılır; abonelik, dönem bitmeden en az 24 saat önce iptal edilmezse yenilenir. Ayrıntılar: <a href="kosullar/">Kullanım koşulları</a>.</p>
</section>

<section class="band band-soft" aria-labelledby="sss-baslik">
  <div class="wrap narrow">
    <p class="eyebrow">Sık sorulanlar</p>
    <h2 id="sss-baslik">Merak edilenler</h2>
    <div class="faq">{faq_html}</div>
  </div>
</section>

<section class="wrap closing">
  <h2>Market rafında bir saniye kazan.</h2>
  <p>{APP_NAME} App Store'da, iPhone için. Soru ve önerilerin için: <a href="mailto:{CONTACT}">{CONTACT}</a></p>
  {store_badge(0)}
</section>
"""
    title = f"{APP_NAME}: Katkı maddesi ve barkod tarayıcı, ailene göre"
    description = (f"{APP_NAME}, barkodu okutulan ürünün katkı maddelerini, alerjenlerini ve besin değerlerini okur; "
                   "Beslenme Skoru'nu hesaplar, ailede herkese ayrı sonuç verir.")
    graph = common_nodes(title, description, "", [], extra={"mainEntity": {"@id": APP_NODE_ID}}) + [app_node()]
    return page(title, description, body, 0, "", active="", graph=graph)


# ------------------------------------------------------------------------------------------------ other pages
def legal_page(slug_: str, source: str, description: str) -> str:
    title, body, toc = markdown((SRC / "legal" / source).read_text(encoding="utf-8"), depth=1)
    toc_html = ""
    if len(toc) >= 4:
        items = "".join(f'<li><a href="#{a}">{inline(t, 1)}</a></li>' for a, t in toc)
        toc_html = f'<nav class="toc" aria-label="Bu sayfada"><p>Bu sayfada</p><ol>{items}</ol></nav>'
    content = f"""<div class="wrap doc-layout">
  {toc_html}
  <article class="doc">
    {breadcrumb_html([("Ana sayfa", ""), (re.sub(r"<[^>]+>", "", inline(title, 1)), f"{slug_}/")], 1)}
    <p class="eyebrow">Yasal</p>
    <h1>{inline(title, 1)}</h1>
    {body}
  </article>
</div>"""
    crumbs = [("Ana sayfa", ""), (re.sub(r"<[^>]+>", "", inline(title, 1)), f"{slug_}/")]
    graph = common_nodes(re.sub(r"<[^>]+>", "", inline(title, 1)), description, f"{slug_}/", crumbs)
    return page(title, description, content, 1, f"{slug_}/", active=f"{slug_}/", graph=graph)


def support_page() -> str:
    body = f"""<div class="wrap narrow doc">
  {breadcrumb_html([("Ana sayfa", ""), ("Destek", "destek/")], 1)}
  <p class="eyebrow">Destek</p>
  <h1>Destek</h1>
  <p>Bir sorun mu yaşadın, bir ürünün bilgisi mi yanlış? Aşağıdaki yollardan birini kullanabilirsin.</p>
  <h2 id="hata">Ürün bilgisi yanlışsa</h2>
  <p>Ürün sayfasında <strong>Hata bildir</strong>'e dokun, neyin yanlış olduğunu seç. Bildirim kimliğinle ilişkilendirilmez. Not alanına ad, telefon veya sağlık bilgisi yazmana gerek yok; barkod ve seçtiğin alan yeterli.</p>
  <h2 id="abonelik">Abonelik ve iade</h2>
  <p>Abonelik Apple üzerinden yönetilir: iPhone'da <strong>Ayarlar &gt; [adın] &gt; Abonelikler</strong>. İade talepleri için <a href="https://reportaproblem.apple.com" rel="noopener">reportaproblem.apple.com</a>. Satın alımı yeni bir cihazda geri yüklemek için uygulamada <strong>Ayarlar &gt; İçgör Aile &gt; Satın alımları geri yükle</strong>.</p>
  <h2 id="veri">Verilerini silmek</h2>
  <p>Profiller ve geçmiş yalnızca telefonundadır: Aile ekranından profili, Ayarlar &gt; Veriler'den geçmişi silebilir ya da uygulamayı kaldırabilirsin. Sunucumuzda sana ait bir hesap veya kayıt bulunmaz.</p>
  <h2 id="iletisim">Bize yaz</h2>
  <p><a href="mailto:{CONTACT}">{CONTACT}</a>. Genellikle iki iş günü içinde dönüyoruz. Yazdığın e-postayı yalnızca sana cevap vermek için kullanırız (<a href="../gizlilik/">Gizlilik</a>).</p>
</div>"""
    description = f"{APP_NAME} destek: hata bildirme, abonelik ve iade, veri silme."
    graph = common_nodes("Destek", description, "destek/", [("Ana sayfa", ""), ("Destek", "destek/")])
    return page("Destek", description, body, 1, "destek/", active="destek/", graph=graph)


def not_found_page() -> str:
    # Served from any depth by GitHub Pages, so links are absolute to the site.
    body = f"""<div class="wrap narrow doc center">
  <p class="eyebrow">404</p>
  <h1>Bu sayfanın içi boş.</h1>
  <p>Aradığın adres burada yok. <a href="{SITE_URL}">Ana sayfaya dön</a>.</p>
</div>"""
    return page("Sayfa bulunamadı", "Sayfa bulunamadı.", body, 0, "404.html", absolute=True, noindex=True)


# ------------------------------------------------------------------------------------------------ guides (SEO/GEO)
# Topic pages for what people search ("E471 nedir", "beslenme skoru nedir", "14 alerjen", "besin değerleri nasıl
# okunur"). Every fact comes from the app's own rule files (data/rules, copied from the app repo with --sync), so the
# site never says more than the app does. Each page has content of its own; no keyword doorway pages.
GUIDES = [
    ("katki-maddeleri/", "Katkı maddeleri (E kodları)", "Her E kodunun ne olduğu, Türkiye'deki durumu ve kaynağı."),
    ("beslenme-skoru/", "Beslenme Skoru nasıl hesaplanır?", "A'dan E'ye harf, hangi değerler sayılır, hangi ürünler kapsam dışı."),
    ("alerjenler/", "14 alerjen", "Etikette bildirilmesi zorunlu 14 alerjen ve etikette nasıl geçtikleri."),
    ("etiket-okuma/", "İçindekiler ve besin değerleri nasıl okunur?", "Etiketi okumanın kısa yolu ve fotoğraftan okuma."),
]
LEVELS = {
    "info": ("Bilgi", "İçgör bu maddeyi bilgi olarak listeler: aşağıdaki “Dikkat” ölçütlerinden hiçbiri bu madde için geçerli değildir."),
    "caution": ("Dikkat", "İçgör bu maddeyi “Dikkat” seviyesinde gösterir. Bu seviye; etikette ek uyarı zorunlu olan maddeler, alerjen grubundaki maddeler, EFSA'nın bazı tüketici gruplarında günlük alım sınırının aşılabileceğini belirttiği ya da ek veri istediği veya geçici sınır koyduğu maddeler için kullanılır. Maddenin Türkiye'de izinli olmadığı anlamına gelmez."),
    "unclear": ("Belirsiz", "İçgör bu maddeyi “Belirsiz” diye işaretler, çünkü etiketteki bilgi tek başına yeterli değildir."),
}
ORIGIN = {
    "always": "Hayvansal kaynaklıdır; vegan ve vejetaryen profillerde İçgör bunu ayrıca belirtir.",
    "maybe": "Bitkisel ya da hayvansal kaynaklı olabilir. Etikette kaynağı yazmıyorsa İçgör “Kaynağı belirsiz” der.",
    "nonVegan": "Hayvansal kaynaklı olabilir; vegan profillerde İçgör bunu ayrıca belirtir.",
}


DESCRIPTION_MAX = 155  # Bing flags descriptions outside ~25-160 characters; Google cuts around 155
TITLE_MAX = 70


def fit(*sentences: str, limit: int = DESCRIPTION_MAX) -> str:
    """Whole sentences while they fit (callers end with a short neutral sentence so the result is never too short)."""
    text = ""
    for sentence in sentences:
        candidate = f"{text} {sentence}".strip()
        if len(candidate) <= limit:
            text = candidate
            continue
        break  # never cut a sentence: a half claim about an additive can say the opposite of the source
    return text


def load_rules() -> dict:
    data = {name: json.loads((RULES / name).read_text(encoding="utf-8")) for name in RULE_FILES}
    sources = {item["id"]: item for item in data["sources.json"]["sources"]}
    additives = data["additives_tr.json"]["additives"]
    return {"additives": additives, "sources": sources, "allergens": data["allergens_eu14.json"]["allergens"],
            "score": data["beslenme_skoru_tr.json"], "additive_source": data["additives_tr.json"]["source"]}


def code_slug(code: str) -> str:
    return code.lower()


def tr_lower(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").lower()


def guides_html(depth: int = 0) -> str:
    up = "../" * depth
    return "".join(f'<li><a class="guide" href="{up}{path}"><b>{esc(name)}</b><span>{esc(desc)}</span></a></li>'
                   for path, name, desc in GUIDES)


def app_node() -> dict:
    """MobileApplication; @id shared by every page's WebPage.about. No ratings or awards (none exist)."""
    return {
        "@type": "MobileApplication", "@id": APP_NODE_ID, "name": APP_NAME, "alternateName": STORE_NAME,
        "description": DEFINITION, "url": SITE_URL, "image": f"{SITE_URL}assets/apple-touch-icon.png",
        "applicationCategory": "HealthApplication", "applicationSubCategory": "Gıda etiketi ve katkı maddesi okuyucu",
        "operatingSystem": "iOS", "inLanguage": "tr", "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "TRY"},
        "installUrl": APP_STORE_URL, "sameAs": [APP_STORE_URL],
        "author": {"@id": ORG_ID}, "publisher": {"@id": ORG_ID},
    }


def cta_box(depth: int) -> str:
    return f"""<aside class="cta-box">
  <p><b>{APP_NAME}</b> bu bilgileri ürünün barkodunu okuttuğun anda, ailedeki her kişi için ayrı gösterir.</p>
  {store_badge(depth, compact=True)}
</aside>"""


def disclaimer() -> str:
    return ('<p class="fine">Bilgi amaçlıdır, tıbbi tavsiye değildir. Alerji veya sağlık durumun varsa ambalajdaki '
            'etiketi kontrol et ve doktoruna danış.</p>')


def source_list(ids: list[str], sources: dict) -> str:
    items = "".join(
        f'<li><a href="{esc(sources[i]["url"])}" rel="noopener">{esc(sources[i]["label"])}</a>'
        f'{" · " + esc(sources[i]["detail"]) if sources[i].get("detail") else ""}</li>' for i in ids)
    return f'<ol class="refs">{items}</ol>'


def additive_page(item: dict, rules: dict) -> tuple[str, str]:
    code, name, cls = item["code"], item["name"], item["class"]
    level_name, level_text = LEVELS[item["level"]]
    slug_ = f"katki-maddeleri/{code_slug(code)}/"
    title = f"{code} {name} nedir? {cls}"
    description = fit(f"{code} ({name}): {tr_lower(cls)}.", item["summary"], item["trStatus"])
    if len(description) < 90:
        description = fit(f"{code} ({name}): {tr_lower(cls)}.",
                          "Türkiye'deki durumu, EFSA değerlendirmesi, etikette diğer adları ve kaynakları.")
    crumbs = [("Ana sayfa", ""), ("Katkı maddeleri", "katki-maddeleri/"), (f"{code} {name}", slug_)]
    facts = [
        ("Türü", cls),
        ("Türkiye'deki durumu", item["trStatus"]),
        ("EFSA değerlendirmesi", item["efsa"]),
        ("İçgör'de", level_name),
    ]
    if item.get("animalOrigin"):
        facts.append(("Kaynağı", ORIGIN[item["animalOrigin"]]))
    others = [x for x in item["synonyms"] if tr_lower(x) != tr_lower(name)]
    if others:
        facts.append(("Etikette diğer adı", ", ".join(others)))
    facts_html = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in facts)
    notes = []
    if item.get("whyUnclear"):
        notes.append(item["whyUnclear"])
    if item.get("southampton"):
        notes.append("Bu renklendiriciyi içeren gıdalarda çocuklara yönelik uyarı ifadesi zorunludur; çocuk profili "
                     "varsa İçgör bunu o kişinin satırında ayrıca gösterir.")
    if item.get("sweetener"):
        notes.append("Tatlandırıcıdır; çocuk profili varsa İçgör “çocuklarda sık tüketimi önerilmez” notunu gösterir.")
    if code in rules["score"]["colorantDowngradeCodes"]:
        notes.append("Beslenme Skoru Rehberi'ne göre bu renklendiriciyi içeren üründe skor sınıfı bir harf düşer.")
    notes_html = "".join(f"<li>{esc(n)}</li>" for n in notes)
    same = [x for x in rules["additives"] if x["class"] == cls and x["code"] != code][:8]
    related = "".join(f'<li><a href="../{code_slug(x["code"])}/">{esc(x["code"])} {esc(x["name"])}</a></li>' for x in same)
    body = f"""<div class="wrap narrow doc">
  {breadcrumb_html(crumbs, 2)}
  <p class="eyebrow">Katkı maddesi · {esc(cls)}</p>
  <h1>{esc(code)} {esc(name)}</h1>
  <p class="lede">{esc(code)} ({esc(name)}), gıdalarda {esc(tr_lower(cls))} olarak kullanılan bir katkı maddesidir. {esc(item["summary"])}</p>
  <span class="level level-{item["level"]}">{esc(level_name)}</span>
  <dl class="facts">{facts_html}</dl>
  {f'<ul class="checks">{notes_html}</ul>' if notes else ""}
  <h2 id="zararli-mi">{esc(code)} zararlı mı?</h2>
  <p>İçgör bir katkı maddesini “zararlı” ya da “zararsız” diye nitelemez; resmî kaynakların ne dediğini aktarır. {esc(item["trStatus"])} {esc(item["efsa"])}</p>
  <p>{esc(level_text)}</p>
  <h2 id="icgor">İçgör bu maddeyi nasıl gösterir?</h2>
  <p>Etikette “{esc(code)}” ya da “{esc(tr_lower(name))}” yazıyorsa {APP_NAME} maddeyi bulur ve ürünün içerik bulgularında kaynağıyla listeler. Aile profillerinde diyet veya yaş grubuyla ilgili bir not varsa o kişinin satırında ayrıca görünür.</p>
  <h2 id="kaynaklar">Kaynaklar</h2>
  {source_list(item["sources"], rules["sources"])}
  {f'<h2 id="benzer">Aynı türden diğer maddeler</h2><ul class="chips">{related}</ul>' if related else ""}
  {cta_box(2)}
  {disclaimer()}
</div>"""
    graph = common_nodes(title, description, slug_, crumbs)
    return slug_, page(title, description, body, 2, slug_, graph=graph)


def additives_index(rules: dict) -> str:
    by_class: dict[str, list[dict]] = {}
    for item in rules["additives"]:
        by_class.setdefault(item["class"], []).append(item)
    count = len(rules["additives"])
    title = "Gıda katkı maddeleri ve E kodları rehberi"
    description = (f"{count} gıda katkı maddesinin (E kodu) ne olduğu, Türk Gıda Kodeksi'ndeki durumu, EFSA "
                   "değerlendirmesi ve kaynağı.")
    crumbs = [("Ana sayfa", ""), ("Katkı maddeleri", "katki-maddeleri/")]
    def row(x: dict) -> str:
        badge = "" if x["level"] == "info" else f'<span class="level level-{x["level"]}">{LEVELS[x["level"]][0]}</span>'
        return f'<li><a href="{code_slug(x["code"])}/"><b>{esc(x["code"])}</b> {esc(x["name"])}</a>{badge}</li>'

    groups = []
    for cls in sorted(by_class, key=tr_lower):
        rows = "".join(row(x) for x in by_class[cls])
        groups.append(f'<h2 id="{slug(cls, set())}">{esc(cls)}</h2><ul class="code-list">{rows}</ul>')
    levels = "".join(f'<li><span class="level level-{k}">{esc(v[0])}</span> {esc(v[1])}</li>'
                     for k, v in LEVELS.items())
    body = f"""<div class="wrap narrow doc">
  {breadcrumb_html(crumbs, 1)}
  <p class="eyebrow">Rehber</p>
  <h1>Gıda katkı maddeleri ve E kodları</h1>
  <p class="lede">E kodu, Avrupa Birliği'nde ve Türkiye'de izin verilen gıda katkı maddelerine verilen numaradır. Bu rehberde {APP_NAME}'ün etikette tanıdığı {count} maddenin ne işe yaradığı, Türk Gıda Kodeksi'ndeki durumu ve kaynağı var.</p>
  <h2 id="seviyeler">İçgör'deki seviyeler ne anlama gelir?</h2>
  <ul class="level-legend">{levels}</ul>
  <p>Türkiye'de izinli bir madde için “yasaklı” denmez. Kaynaklar: {esc(rules["additive_source"])}, AB mevzuatı ve EFSA değerlendirmeleri.</p>
  {"".join(groups)}
  {cta_box(1)}
  {disclaimer()}
</div>"""
    items = [{"@type": "ListItem", "position": i, "name": f'{x["code"]} {x["name"]}',
              "url": f'{SITE_URL}katki-maddeleri/{code_slug(x["code"])}/'}
             for i, x in enumerate(rules["additives"], start=1)]
    graph = common_nodes(title, description, "katki-maddeleri/", crumbs, ["WebPage", "CollectionPage"],
                         {"mainEntity": {"@type": "ItemList", "numberOfItems": count, "itemListElement": items}})
    return page(title, description, body, 1, "katki-maddeleri/", active="katki-maddeleri/", graph=graph)


def score_page(rules: dict) -> str:
    score = rules["score"]
    grades = score["general"]["grades"]
    title = "Beslenme Skoru nedir, nasıl hesaplanır?"
    description = ("Beslenme Skoru, 100 g'daki enerji, şeker, doymuş yağ, tuz, lif ve proteinden A'dan E'ye bir harf "
                   "verir. Nasıl hesaplanır, hangi ürünler kapsam dışı?")
    crumbs = [("Ana sayfa", ""), ("Beslenme Skoru", "beslenme-skoru/")]
    bounds = [("A", None, grades["A"]), ("B", grades["A"] + 1, grades["B"]), ("C", grades["B"] + 1, grades["C"]),
              ("D", grades["C"] + 1, grades["D"])]
    grade_rows = "".join(
        f"<tr><th>{g}</th><td>{f'{lo}–{hi}' if lo is not None else f'{hi} ve altı'}</td></tr>" for g, lo, hi in bounds)
    colorants = ", ".join(f'<a href="../katki-maddeleri/{code_slug(c)}/">{c}</a>'
                          for c in score["colorantDowngradeCodes"])
    body = f"""<div class="wrap narrow doc">
  {breadcrumb_html(crumbs, 1)}
  <p class="eyebrow">Rehber</p>
  <h1>Beslenme Skoru nedir, nasıl hesaplanır?</h1>
  <p class="lede">Beslenme Skoru, T.C. Sağlık Bakanlığı'nın yayımladığı ve aynı kategorideki gıdaları karşılaştırmaya yarayan, A'dan E'ye harfli bir ön yüz etiketidir. {APP_NAME} skoru Bakanlığın Beslenme Skoru Rehberi'ndeki eşiklerle, ürün kaydındaki besin değerlerinden kendisi hesaplar ve bunu “İçgör hesabı” diye belirtir.</p>
  <h2 id="nasil">Puan nasıl oluşur?</h2>
  <p>100 g veya 100 ml başına enerji, şeker, doymuş yağ ve tuz olumsuz puan; lif, protein ve meyve-sebze-baklagil oranı olumlu puan getirir. Olumsuz puanlardan olumlu puanlar düşülür ve toplam bir harfe çevrilir. İçecekler, yağlar ve genel gıdalar için ayrı eşik tabloları kullanılır.</p>
  <h2 id="harfler">Genel gıdalarda harf sınırları</h2>
  <table class="grid"><thead><tr><th>Harf</th><th>Toplam puan</th></tr></thead><tbody>{grade_rows}<tr><th>E</th><td>{grades["D"] + 1} ve üstü</td></tr></tbody></table>
  <h2 id="nbs">Nişasta bazlı şeker ve renklendiriciler</h2>
  <p>İçindekilerde nişasta bazlı şeker (NBŞ; glikoz-fruktoz şurubu gibi) varsa toplam puana {score["nbs"]["penalty"]} puan eklenir. Şu renklendiricilerden birini içeren üründe sınıf bir harf düşer: {colorants}.</p>
  <h2 id="kapsam-disi">Hangi ürünlerde skor yoktur?</h2>
  <p>Bal, doğal ve katkısız süt ürünleri (süt, sade yoğurt, peynir, tereyağı, kefir, ayran), 0–3 yaş bebek gıdaları, takviye edici gıdalar, sporcu gıdaları, öğün yerine geçen ürünler, tuz, baharat ve tek başına satılan katkı maddeleri Bakanlığın kapsam dışı saydığı ürünlerdir. {APP_NAME} bu ürünlerde skor göstermez.</p>
  <h2 id="eksik">Besin değeri eksikse?</h2>
  <p>Skor tahmin edilmez; ürün sayfasında “Besin değeri eksik” yazar. Etiketteki besin değerleri tablosunun fotoğrafını çekip değerleri ekleyebilirsin; tablo telefonda okunur, sen kontrol edip onaylarsın.</p>
  <h2 id="resmi-mi">Ambalajdaki skorla neden farklı olabilir?</h2>
  <p>Ambalajda bir Beslenme Skoru varsa o esas alınır. İçgör'ün hesabı ürün kaydındaki değerlere dayanır; değerler eksik, eski veya hatalıysa iki sonuç farklı olabilir. İçgör hesabı Bakanlık onayı veya üretici beyanı değildir ve bir ürünü tek başına “sağlıklı” ya da “sağlıksız” diye nitelemez.</p>
  <h2 id="kaynaklar">Kaynaklar</h2>
  {source_list(score["sources"], rules["sources"])}
  {cta_box(1)}
  {disclaimer()}
</div>"""
    graph = common_nodes(title, description, "beslenme-skoru/", crumbs, ["WebPage", "Article"],
                         {"headline": title, "author": {"@id": ORG_ID}})
    return page(title, description, body, 1, "beslenme-skoru/", active="beslenme-skoru/", graph=graph)


def label_terms(allergen: dict, limit: int = 6) -> list[str]:
    """The first Turkish label words of an allergen (the list starts with Turkish terms; '=' marks whole-word)."""
    words = []
    for term in allergen["terms"]:
        if term.startswith("="):
            continue
        if words and term.isascii() and term in {"wheat", "milk", "egg", "eggs", "fish", "soy", "soya", "peanut", "peanuts",
                                                  "celery", "mustard", "sesame", "lupin", "crustaceans", "molluscs",
                                                  "nuts", "sulphites", "sulfites", "sulphite", "sulfite", "almond", "shrimp", "mussel", "soja", "soia"}:
            break
        words.append(term)
        if len(words) == limit:
            break
    return words


def allergens_page(rules: dict) -> str:
    title = "14 alerjen: etikette nasıl yazar?"
    description = ("Etikette bildirilmesi zorunlu 14 alerjen, içindekilerde hangi adlarla geçtikleri ve “iz miktarda "
                   "içerebilir” ifadesinin anlamı.")
    crumbs = [("Ana sayfa", ""), ("14 alerjen", "alerjenler/")]
    rows = "".join(
        f'<tr><th>{esc(a["name_tr"])}</th><td>{esc(", ".join(label_terms(a)))}</td></tr>' for a in rules["allergens"])
    body = f"""<div class="wrap narrow doc">
  {breadcrumb_html(crumbs, 1)}
  <p class="eyebrow">Rehber</p>
  <h1>14 alerjen: etikette nasıl yazar?</h1>
  <p class="lede">Avrupa Birliği'nin 1169/2011 sayılı tüzüğü ve Türk Gıda Kodeksi, alerjiye en sık yol açan 14 madde grubunun içindekiler listesinde vurgulanarak yazılmasını zorunlu tutar. {APP_NAME} bu 14 grubu etikette ve ürün kaydında arar, profilinde işaretlediğin alerjenle eşleşirse o kişinin satırında söyler.</p>
  <table class="grid"><thead><tr><th>Alerjen</th><th>Etikette geçebileceği bazı adlar</th></tr></thead><tbody>{rows}</tbody></table>
  <h2 id="iz">“İz miktarda içerebilir” ne demek?</h2>
  <p>Ürünün aynı tesiste ya da hatta o alerjeni içeren başka ürünlerle üretildiğini ve bulaşma olabileceğini belirten bir uyarıdır. {APP_NAME} bunu “içerir”den ayrı, “iz” olarak gösterir.</p>
  <h2 id="bilgi-yok">Etikette bilgi yoksa?</h2>
  <p>İçindekiler listesi yoksa ya da okunamıyorsa {APP_NAME} “Çakışma yok” demez, “bilgi yok” der. Yabancı dilde etikette tanımadığı bir ifade varsa da aynı kural geçerlidir. “Çakışma yok”, ürün kaydında profilinle çakışan bir bilgi bulunamadığı anlamına gelir; ürünün senin için güvenli olduğu anlamına gelmez.</p>
  <h2 id="kaynaklar">Kaynaklar</h2>
  {source_list(["ab-1169-ek2"], rules["sources"])}
  {cta_box(1)}
  {disclaimer()}
</div>"""
    graph = common_nodes(title, description, "alerjenler/", crumbs, ["WebPage", "Article"],
                         {"headline": title, "author": {"@id": ORG_ID}})
    return page(title, description, body, 1, "alerjenler/", graph=graph)


def label_reading_page(rules: dict) -> str:
    title = "İçindekiler ve besin değerleri nasıl okunur?"
    description = ("İçindekiler listesi ve besin değerleri tablosu nasıl okunur: sıralama, E kodları, alerjenler, 100 g "
                   "değerleri ve fotoğraftan okuma.")
    crumbs = [("Ana sayfa", ""), ("Etiket okuma", "etiket-okuma/")]
    body = f"""<div class="wrap narrow doc">
  {breadcrumb_html(crumbs, 1)}
  <p class="eyebrow">Rehber</p>
  <h1>İçindekiler ve besin değerleri nasıl okunur?</h1>
  <p class="lede">Bir gıda etiketinde iki bölüm işin çoğunu anlatır: içindekiler listesi ve besin değerleri tablosu. Aşağıda ikisini okumanın kısa yolunu ve {APP_NAME}'ün etiketi fotoğraftan nasıl okuduğunu bulabilirsin.</p>
  <h2 id="icindekiler">İçindekiler listesi</h2>
  <ul class="checks">
    <li>Bileşenler, ürüne katılan miktara göre çoktan aza sıralanır; ilk sıradaki en çok olandır.</li>
    <li>Katkı maddeleri işlevleriyle birlikte yazılır: “renklendirici (E102)” ya da “emülgatör (soya lesitini)” gibi. Her E kodu için <a href="../katki-maddeleri/">katkı maddeleri rehberine</a> bakabilirsin.</li>
    <li><a href="../alerjenler/">14 alerjen</a> içindekiler listesinde vurgulanarak (kalın ya da büyük harfle) yazılır; “iz miktarda içerebilir” ayrı bir uyarıdır.</li>
    <li>“Aroma verici” veya “bitkisel yağ” gibi genel ifadeler kaynağı söylemez; {APP_NAME} bunları “belirsiz” diye işaretler.</li>
  </ul>
  <h2 id="besin-degerleri">Besin değerleri tablosu</h2>
  <ul class="checks">
    <li>Tablo enerji (kJ ve kcal), yağ, doymuş yağ, karbonhidrat, şeker, protein ve tuz değerlerini verir; lif isteğe bağlıdır.</li>
    <li>Karşılaştırma için 100 g veya 100 ml sütununu kullan. Porsiyon sütunu üreticinin porsiyonuna göredir ve ürünler arasında farklıdır.</li>
    <li><a href="../beslenme-skoru/">Beslenme Skoru</a> da bu 100 g değerlerinden hesaplanır.</li>
  </ul>
  <h2 id="fotograftan">Etiketi fotoğraftan okuma</h2>
  <p>Ürün kayıtlı değilse ya da içindekiler veya besin değerleri eksikse {APP_NAME}'de etiketin fotoğrafını çekersin. Belge tarayıcı etiketi bulup düzeltir; yazı ve tablo telefonun kendisinde okunur. Okunan değerleri ambalajla karşılaştırıp onaylarsın. Fotoğraf, yalnızca sen göndermeyi seçersen telefondan çıkar.</p>
  {cta_box(1)}
  {disclaimer()}
</div>"""
    graph = common_nodes(title, description, "etiket-okuma/", crumbs, ["WebPage", "Article"],
                         {"headline": title, "author": {"@id": ORG_ID}})
    return page(title, description, body, 1, "etiket-okuma/", graph=graph)


def press_page(rules: dict) -> str:
    title = "Basın ve tanıtım bilgileri"
    description = f"{APP_NAME} hakkında kısa bilgiler: tanım, platform, fiyat, veri kaynakları ve iletişim."
    crumbs = [("Ana sayfa", ""), ("Basın", "basin/")]
    facts = [
        ("Ad", APP_NAME), ("App Store adı", STORE_NAME), ("Geliştirici", f"{DEVELOPER}, Türkiye'de bağımsız geliştirici"),
        ("Platform", "iPhone (iOS)"), ("Dil", "Türkçe"),
        ("Fiyat", f"Ücretsiz; İçgör Aile aboneliği {PRICE_MONTHLY} / ay veya {PRICE_YEARLY} / yıl"),
        ("Ücretsiz sürüm", f"Her ay {FREE_MONTHLY_NEW} yeni ürün, 1 profil"),
        ("İçgör Aile", f"Sınırsız tarama, {FAMILY_PROFILES} profile kadar aile"),
        ("Tanıdığı katkı maddesi", f"{len(rules['additives'])} E kodu"),
        ("Alerjenler", "AB 1169/2011'deki 14 alerjen"),
        ("Veri", "Open Food Facts (ODbL) ve onaylanan kullanıcı katkıları"),
        ("Hesap ve reklam", "Hesap yok, reklam yok; profiller telefonda kalır"),
        ("App Store", APP_STORE_URL), ("İletişim", CONTACT),
    ]
    rows = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in facts)
    body = f"""<div class="wrap narrow doc">
  {breadcrumb_html(crumbs, 1)}
  <p class="eyebrow">Basın</p>
  <h1>Basın ve tanıtım bilgileri</h1>
  <h2 id="kisa">Kısa tanım</h2>
  <p>{esc(DEFINITION)}</p>
  <h2 id="bilgiler">Bilgiler</h2>
  <table class="grid"><tbody>{rows}</tbody></table>
  <h2 id="kullanim">Kullanım</h2>
  <p>Logo ve ekran görüntüleri için <a href="mailto:{CONTACT}">{CONTACT}</a> adresine yaz. {APP_NAME}'ü anlatırken skoru “resmî” ya da “Bakanlık onaylı” diye anlatmamanı rica ederiz: skor, Bakanlığın yöntemiyle uygulama içinde hesaplanan bir İçgör hesabıdır. {APP_NAME} tıbbi tavsiye vermez.</p>
</div>"""
    graph = common_nodes(title, description, "basin/", crumbs, ["WebPage", "AboutPage"])
    return page(title, description, body, 1, "basin/", graph=graph)


# ------------------------------------------------------------------------------------------------ build + check
def write(rel: str, text: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def check() -> list[str]:
    """Every relative href/src resolves to a file, every #anchor to an id on its page."""
    problems = []
    for file in ROOT.rglob("*.html"):
        if any(part in {"src", "node_modules", ".git"} for part in file.relative_to(ROOT).parts):
            continue
        text = file.read_text(encoding="utf-8")
        ids = set(re.findall(r'id="([^"]+)"', text))
        for ref in re.findall(r'(?:href|src)="([^"]+)"', text):
            if ref.startswith(("http", "mailto:", "data:")) or file.name == "404.html":
                continue
            target, _, anchor = ref.partition("#")
            target = target.partition("?")[0]
            if not target:
                if anchor and anchor not in ids:
                    problems.append(f"{file.relative_to(ROOT)}: #{anchor} yok")
                continue
            resolved = (file.parent / target).resolve()
            if resolved.is_dir():
                resolved = resolved / "index.html"
            if not resolved.exists():
                problems.append(f"{file.relative_to(ROOT)}: {ref} bulunamadı")
            elif anchor and f'id="{anchor}"' not in resolved.read_text(encoding="utf-8"):
                problems.append(f"{file.relative_to(ROOT)}: {ref} çapası yok")
    return problems


def sync_legal() -> None:
    """The app repo's legal texts follow the next release; copy them only once that release is on the App Store."""
    if APP_RELEASE != "1.1":
        raise SystemExit("HATA: yasal metinler 1.1 içindir; önce APP_RELEASE = \"1.1\" yap (1.1.0 yayına girince).")
    target = SRC / "legal"
    target.mkdir(parents=True, exist_ok=True)
    for _, source, _, _ in LEGAL_PAGES:
        shutil.copyfile(LEGAL_SRC / source, target / source)
    print(f"Yasal metinler kopyalandı: {LEGAL_SRC}")


def sync_rules() -> None:
    RULES.mkdir(parents=True, exist_ok=True)
    for name in RULE_FILES:
        shutil.copyfile(RULES_SRC / name, RULES / name)
    print(f"Kural dosyaları kopyalandı: {RULES_SRC}")


def check_rules_fresh() -> list[str]:
    """The site must not drift from the app: data/rules equals the app repo's files when that repo is next to us."""
    if not RULES_SRC.exists():
        return []
    return [f"data/rules/{name} uygulamadakinden farklı; `python3 build.py --sync-rules` çalıştır"
            for name in RULE_FILES if (RULES / name).read_bytes() != (RULES_SRC / name).read_bytes()]


# Claims we never make (overclaims, health claims, legal labels the app avoids). Title/H1/URL: error; body: listed.
BANNED = [r"\ben iyi\b", r"#1\b", r"\bbir numara", r"\bzararsız", r"\bsağlıklı ürün", r"\bkanserojen", r"\bzehir",
          r"\byasaklı katkı", r"\btehlikeli", r"\bgaranti", r"\bresmî skor", r"\bresmi skor", r"tıbbi tavsiye ver(ir|ir\.)"]
BANNED_OK = {"zararsız"}  # quoted on purpose: "zararlı" ya da "zararsız" diye nitelemez


def visible_text(html_text: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html_text, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)))


def check_content() -> list[str]:
    problems = []
    for file in ROOT.rglob("index.html"):
        if any(part in {"src", "node_modules", ".git", "data"} for part in file.relative_to(ROOT).parts):
            continue
        rel = file.relative_to(ROOT)
        text = file.read_text(encoding="utf-8")
        title = re.search(r"<title>(.*?)</title>", text).group(1)
        meta = html.unescape(re.search(r'<meta name="description" content="([^"]*)"', text).group(1))
        if not 50 <= len(meta) <= DESCRIPTION_MAX:
            problems.append(f"{rel}: açıklama {len(meta)} karakter (50–{DESCRIPTION_MAX} olmalı)")
        if len(html.unescape(title)) > TITLE_MAX:
            problems.append(f"{rel}: başlık {len(html.unescape(title))} karakter (en çok {TITLE_MAX})")
        h1 = re.search(r"<h1>(.*?)</h1>", text, re.S)
        head_text = tr_lower(html.unescape(title + " " + (h1.group(1) if h1 else "") + " " + str(rel)))
        for pattern in BANNED:
            if re.search(pattern, head_text):
                problems.append(f"{rel}: başlıkta yasak ifade /{pattern}/")
        if "legal" in str(rel) or rel.parts[0] in {s for s, *_ in LEGAL_PAGES}:
            continue
        body = tr_lower(visible_text(text))
        for pattern in BANNED:
            for match in re.finditer(pattern, body):
                if match.group(0).strip() not in BANNED_OK:
                    problems.append(f"{rel}: metinde yasak ifade “{match.group(0)}”")
        # JSON-LD must say only what the page shows.
        ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
        if not ld:
            problems.append(f"{rel}: JSON-LD yok")
            continue
        graph = json.loads(ld.group(1).replace("<\\/", "</"))["@graph"]
        shown = visible_text(text)
        for node in graph:
            if "WebPage" in (node["@type"] if isinstance(node["@type"], list) else [node["@type"]]):
                if html.unescape(node["description"]) not in html.unescape(re.search(r'<meta name="description" content="([^"]*)"', text).group(1)):
                    problems.append(f"{rel}: JSON-LD description meta ile aynı değil")
                if not html.unescape(title).startswith(node["name"]):
                    problems.append(f"{rel}: JSON-LD name başlıkla uyuşmuyor")
            if node["@type"] == "BreadcrumbList":
                for item in node["itemListElement"]:
                    if item["name"] not in shown:
                        problems.append(f"{rel}: sayfa yolu “{item['name']}” sayfada görünmüyor")
            if node["@type"] == "MobileApplication" and node["description"] not in shown:
                problems.append(f"{rel}: uygulama tanımı sayfada görünmüyor")
    return problems


def page_paths() -> list[str]:
    paths = []
    for file in sorted(ROOT.rglob("index.html")):
        rel = file.relative_to(ROOT)
        if any(part in {"src", "node_modules", ".git", "data"} for part in rel.parts):
            continue
        paths.append("" if rel.parent == pathlib.Path(".") else f"{rel.parent.as_posix()}/")
    return paths


def lastmods(paths: list[str]) -> dict[str, str]:
    """Date of the last real content change per page (hash of the page minus the CSS cache key)."""
    store = ROOT / "data" / "lastmod.json"
    known = json.loads(store.read_text(encoding="utf-8")) if store.exists() else {}
    today = datetime.date.today().isoformat()
    result = {}
    for path in paths:
        text = (ROOT / path / "index.html").read_text(encoding="utf-8")
        digest = hashlib.sha256(re.sub(r"\?v=[0-9a-f]+", "", text).encode()).hexdigest()
        old = known.get(path)
        result[path] = {"hash": digest, "date": old["date"] if old and old["hash"] == digest else today}
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {path: value["date"] for path, value in result.items()}


def write_sitemap(dates: dict[str, str]) -> None:
    urls = "".join(f"<url><loc>{SITE_URL}{path}</loc><lastmod>{date}</lastmod></url>\n" for path, date in dates.items())
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')


def write_robots() -> None:
    bots = ["Googlebot", "Bingbot", "Applebot", "Applebot-Extended", "Google-Extended", "OAI-SearchBot", "ChatGPT-User",
            "GPTBot", "Claude-SearchBot", "Claude-User", "ClaudeBot", "PerplexityBot", "Perplexity-User", "CCBot",
            "YandexBot"]
    agents = "".join(f"User-agent: {b}\n" for b in bots)
    write("robots.txt", f"# {APP_NAME}: all crawlers welcome (search, user-initiated fetches and AI answers)\n"
                        f"User-agent: *\nAllow: /\n\n{agents}Allow: /\n\nSitemap: {SITE_URL}sitemap.xml\n")


def write_llms(rules: dict) -> None:
    """llms.txt (speculative; Google says it does not use it). Same facts as the pages, in Turkish."""
    pages = [("", f"{APP_NAME} ana sayfa")] + [(path, name) for path, name, _ in GUIDES] + [
        ("basin/", "Basın ve tanıtım bilgileri"), ("destek/", "Destek"), ("gizlilik/", "Gizlilik politikası")]
    page_lines = "".join(f"- [{name}]({SITE_URL}{path})\n" for path, name in pages)
    codes = ", ".join(f'{x["code"]} {x["name"]}' for x in rules["additives"][:12])
    write("llms.txt", f"""# {APP_NAME}

> {DEFINITION}

{APP_NAME} ({STORE_NAME}), {DEVELOPER} tarafından Türkiye'de geliştirilen bir iPhone uygulamasıdır.

## Bilgiler
- Platform: iPhone (iOS); dil: Türkçe
- Fiyat: ücretsiz indirme; İçgör Aile aboneliği {PRICE_MONTHLY} / ay veya {PRICE_YEARLY} / yıl (Türkiye App Store)
- Ücretsiz sürüm: her ay {FREE_MONTHLY_NEW} yeni ürün, 1 profil; İçgör Aile: sınırsız tarama, {FAMILY_PROFILES} profile kadar aile
- Hesap yok, reklam yok; aile profilleri telefonda kalır
- Ürün türleri: gıda, kozmetik, temizlik ürünü, kıyafet etiketi
- Katkı maddeleri: {len(rules["additives"])} E kodu (ör. {codes}); kaynaklar Türk Gıda Kodeksi, AB mevzuatı, EFSA
- Alerjenler: AB 1169/2011'deki 14 alerjen
- Beslenme Skoru: Sağlık Bakanlığı Beslenme Skoru Rehberi eşikleriyle İçgör hesaplar; resmî bir not değildir
- Tıbbi tavsiye vermez
- App Store: {APP_STORE_URL}

## Sayfalar
{page_lines}
## İsteğe bağlı
- [Geliştirici]({DEVELOPER_URL})
""")


INDEXNOW_KEY = "f31eb28ebc81c1b9118317945af166ae"


def write_indexnow_key() -> None:
    write(f"{INDEXNOW_KEY}.txt", INDEXNOW_KEY)


def main() -> int:
    if "--sync" in sys.argv:
        sync_legal()
    if "--sync" in sys.argv or "--sync-rules" in sys.argv:
        sync_rules()
    rules = load_rules()
    write("index.html", landing())
    write("katki-maddeleri/index.html", additives_index(rules))
    for item in rules["additives"]:
        slug_, text = additive_page(item, rules)
        write(f"{slug_}index.html", text)
    write("beslenme-skoru/index.html", score_page(rules))
    write("alerjenler/index.html", allergens_page(rules))
    write("etiket-okuma/index.html", label_reading_page(rules))
    write("basin/index.html", press_page(rules))
    for slug_, source, _, description in LEGAL_PAGES:
        write(f"{slug_}/index.html", legal_page(slug_, source, description))
    write("destek/index.html", support_page())
    write("404.html", not_found_page())
    write(".nojekyll", "")
    write_robots()
    write_llms(rules)
    write_indexnow_key()
    write_sitemap(lastmods(page_paths()))
    problems = check() + check_content() + check_rules_fresh()
    for file in sorted(ROOT.glob("*/index.html")):
        todo = re.findall(r'<mark class="todo">\[([^\]]+)\]</mark>', file.read_text(encoding="utf-8"))
        if todo:
            print(f"UYARI: {file.parent.name}/ yer tutucu içeriyor: {', '.join(sorted(set(todo)))}")
    for problem in problems:
        print("HATA:", problem)
    print("Derlendi." if not problems else f"{len(problems)} sorun.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
