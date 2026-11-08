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

import html
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
UPDATED = "5 Kasım 2026"

# Launch-day switch: True turns the App Store badges into real links (fill APP_ID from App Store Connect first).
APP_STORE_LIVE = False
APP_ID = "6830374026"
APP_STORE_URL = f"https://apps.apple.com/tr/app/id{APP_ID}"

PRICE_MONTHLY = "₺84,99"
PRICE_YEARLY = "₺499,99"
FREE_MONTHLY_NEW = 3

LEGAL_PAGES = [
    # (slug, source file, nav label, description)
    ("gizlilik", "gizlilik-politikasi.md", "Gizlilik", "İçgör gizlilik politikası: hangi bilgi nerede kalır, ne kadar tutulur."),
    ("kosullar", "kullanim-kosullari.md", "Kullanım koşulları", "İçgör kullanım koşulları ve abonelik bilgileri."),
    ("katki", "katki-kosullari.md", "Katkı koşulları", "İçgör'e ürün bilgisi ve fotoğrafı gönderme koşulları."),
    ("kvkk", "kvkk-aydinlatma.md", "KVKK", "6698 sayılı KVKK kapsamında bilgilendirme."),
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


def page(title: str, description: str, body: str, depth: int, canonical: str, active: str = "",
         absolute: bool = False) -> str:
    """`absolute` is for 404.html, which GitHub Pages serves at whatever path was requested."""
    up = SITE_URL if absolute else "../" * depth
    home = up or "./"
    nav = [("", "Ürün"), ("gizlilik/", "Gizlilik"), ("kosullar/", "Koşullar"), ("destek/", "Destek")]
    links = "".join(
        f'<a href="{up}{path}"{" aria-current=\"page\"" if active == path else ""}>{label}</a>' for path, label in nav
    )
    legal_links = "".join(f'<a href="{up}{s}/">{label}</a>' for s, _, label, _ in LEGAL_PAGES)
    full_title = title if title.startswith(APP_NAME) else f"{title} · {APP_NAME}"
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
<link rel="canonical" href="{SITE_URL}{canonical}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_URL}{canonical}">
<meta property="og:image" content="{SITE_URL}assets/og.png">
<link rel="icon" href="{up}assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{up}assets/apple-touch-icon.png">
<link rel="stylesheet" href="{up}assets/site.css">
</head>
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
      <p class="foot-note">{APP_NAME} bir bilgi aracıdır; tıbbi, diyet veya alerji tavsiyesi vermez. Alerjin varsa her zaman ambalajdaki etiketi okuyup kendi doktoruna danış.</p>
    </div>
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
         f"Her ay {FREE_MONTHLY_NEW} yeni ürün, bir profil ve geçmişindeki ürünlere sınırsız erişim. İçgör Aile ile tarama sınırı kalkar, 6 profile kadar aile ekleyebilir, sepet ve haftalık özeti kullanabilirsin."),
        ("İnternet olmadan çalışır mı?",
         "Daha önce baktığın ürünler internetsiz de açılır. Yeni bir barkod için bağlantı gerekir; etiket fotoğrafından okuma ise tamamen telefonda yapılır."),
        ("Verilerimi nasıl silerim?",
         "Profilleri Aile ekranından, geçmişi Ayarlar > Veriler'den silebilirsin. Uygulamayı kaldırdığında telefondaki her şey silinir; sunucumuzda sana ait bir kayıt yoktur."),
    ]
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq)

    body = f"""
<section class="hero">
  <div class="wrap hero-grid">
    <div class="hero-copy">
      <p class="eyebrow">Gıda · kozmetik · temizlik · kıyafet etiketi</p>
      <h1><em>İçini gör.</em> Bir kez okut, ailendeki herkes için ayrı ayrı anlatsın.</h1>
      <p class="lede">{APP_NAME}, barkodu okuttuğun ürünün içeriğini ailendeki her kişinin alerjen, diyet ve hassasiyetleriyle karşılaştırır. Ne bulduysa sakin bir dille ve kaynağıyla söyler.</p>
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
    <h2 id="aile-baslik">Aynı paket, altı farklı okuma.</h2>
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
      <ul><li>Sınırsız tarama</li><li>6 profile kadar aile</li><li>Sepet ve haftalık özet</li><li>Tüm cihazlarında, Aile Paylaşımı ile</li></ul>
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
  <p>{APP_NAME} iPhone için hazırlanıyor. Çıktığında haber almak istersen bize yazabilirsin: <a href="mailto:{CONTACT}">{CONTACT}</a></p>
  {store_badge(0)}
</section>
"""
    return page(
        f"{APP_NAME}: Ailene göre etiket okuyucu",
        f"{APP_NAME}, barkodu okutulan gıda, kozmetik, temizlik ürünü ve kıyafet etiketini ailendeki her kişinin alerjen ve tercihlerine göre kaynaklı olarak değerlendirir. Hesap yok, reklam yok.",
        body, 0, "",
    )


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
    <p class="eyebrow"><a href="../">{APP_NAME}</a> · Yasal</p>
    <h1>{inline(title, 1)}</h1>
    {body}
  </article>
</div>"""
    return page(title, description, content, 1, f"{slug_}/", active=f"{slug_}/")


def support_page() -> str:
    body = f"""<div class="wrap narrow doc">
  <p class="eyebrow"><a href="../">{APP_NAME}</a> · Destek</p>
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
    return page("Destek", f"{APP_NAME} destek: hata bildirme, abonelik ve iade, veri silme.", body, 1, "destek/", active="destek/")


def not_found_page() -> str:
    # Served from any depth by GitHub Pages, so links are absolute to the site.
    body = f"""<div class="wrap narrow doc center">
  <p class="eyebrow">404</p>
  <h1>Bu sayfanın içi boş.</h1>
  <p>Aradığın adres burada yok. <a href="{SITE_URL}">Ana sayfaya dön</a>.</p>
</div>"""
    return page("Sayfa bulunamadı", "Sayfa bulunamadı.", body, 0, "404.html", absolute=True)


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
    target = SRC / "legal"
    target.mkdir(parents=True, exist_ok=True)
    for _, source, _, _ in LEGAL_PAGES:
        shutil.copyfile(LEGAL_SRC / source, target / source)
    print(f"Yasal metinler kopyalandı: {LEGAL_SRC}")


def main() -> int:
    if "--sync" in sys.argv:
        sync_legal()
    write("index.html", landing())
    for slug_, source, _, description in LEGAL_PAGES:
        write(f"{slug_}/index.html", legal_page(slug_, source, description))
    write("destek/index.html", support_page())
    write("404.html", not_found_page())
    write(".nojekyll", "")
    problems = check()
    for problem in problems:
        print("HATA:", problem)
    print("Derlendi." if not problems else f"{len(problems)} sorun.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
