#!/usr/bin/env python3
"""Build the static site (standard library only).

    python3 tools/build.py

Reads everything in content/ and writes finished HTML into the repository root,
then checks that every internal link and image in the output resolves.
"""
import datetime
import hashlib
import html
import json
import re
import shutil
import struct
import sys
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"


def load_json(name):
    return json.loads((CONTENT / name).read_text(encoding="utf-8"))


def split_front_matter(text, source="page"):
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        sys.exit(f"{source}: missing front matter (--- ... ---) at the top of the file")
    meta = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, m.group(2)


def make_excerpt(body):
    paras = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<br\s*/?>", " ", x)))).strip()
             for x in re.findall(r"<p>(.*?)</p>", body, re.S)]
    text = next((t for t in paras if len(t) >= 80), paras[0] if paras else "")
    if len(text) > 230:
        cut = text[:230]
        sentences = list(re.finditer(r"[.!?](?=\s)", cut))
        if sentences and sentences[-1].end() >= 100:
            return cut[:sentences[-1].end()]
        return cut.rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return text


def load_posts():
    posts = []
    for f in sorted((CONTENT / "posts").glob("*.html")):
        meta, body = split_front_matter(f.read_text(encoding="utf-8"), f.name)
        for key in ("title", "slug", "date"):
            if not meta.get(key):
                sys.exit(f"{f.name}: front matter is missing '{key}'")
        posts.append({
            "title": meta["title"], "slug": meta["slug"], "date": meta["date"],
            "image": meta.get("image") or None, "imageAlt": meta.get("imageAlt", ""),
            "excerpt": meta.get("excerpt") or make_excerpt(body), "html": body.strip(),
        })
    return sorted(posts, key=lambda p: p["date"], reverse=True)


SITE = load_json("site.json")
POSTS = load_posts()
PUBS = load_json("publications.json")
STUDIES = load_json("studies.json")
TEAM = load_json("team.json")
YEAR = datetime.date.today().year
esc = html.escape


# ---------------------------------------------------------------- helpers
def fmt_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d:%B} {d.day}, {d.year}"


def root_for(path):
    """Relative prefix that points from a page at `path` back to the site root."""
    if path == "404.html":
        return (SITE["basePath"] + "/") if SITE["basePath"] else "/"
    return "../" * path.count("/")


def post_dir(post):
    return f"f/{post['slug']}/"


def post_href(post, root):
    return f"{root}f/{quote(post['slug'])}/"


def asset_version(*rel_paths):
    h = hashlib.md5()
    for rel in rel_paths:
        h.update((ROOT / rel).read_bytes())
    return h.hexdigest()[:8]


CSS_V = asset_version("assets/css/site.css")
JS_V = asset_version("assets/js/site.js")


def image_size(path):
    """Read (width, height) from a PNG or JPEG header without third-party libraries."""
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


def add_dimensions(markup):
    def repl(m):
        tag = m.group(0)
        if " width=" in tag:
            return tag
        src = re.search(r'src="([^"]+)"', tag)
        if not src or "assets/img/" not in src.group(1):
            return tag
        f = ROOT / "assets" / "img" / src.group(1).split("assets/img/", 1)[1]
        size = image_size(f) if f.exists() else None
        if not size:
            return tag
        return tag[:-1].rstrip("/").rstrip() + f' width="{size[0]}" height="{size[1]}">'

    return re.sub(r"<img\b[^>]*>", repl, markup)


def load_fragment(name):
    return split_front_matter((CONTENT / "pages" / f"{name}.html").read_text(encoding="utf-8"), f"{name}.html")


# ---------------------------------------------------------------- components
X_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M18.244 2.25h3.308l-7.227 8.26 '
          '8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 '
          '17.52h1.833L7.084 4.126H5.117z"/></svg>')


def header(path, root):
    links = []
    for item in SITE["nav"]:
        current = ' aria-current="page"' if item["path"] == path else ""
        links.append(f'<li><a href="{(root + item["path"]) or "./"}"{current}>{esc(item["label"])}</a></li>')
    return f"""<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="{root or './'}"><img src="{root}assets/img/logo.jpg" alt=""><span>{esc(SITE['name'])}</span></a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">
      <span class="sr-only">Menu</span>
      <svg class="icon-open" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
      <svg class="icon-close" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
    </button>
    <nav class="site-nav" id="site-nav" aria-label="Primary"><ul>{''.join(links)}</ul></nav>
  </div>
</header>"""


def footer(root):
    links = "".join(f'<li><a href="{(root + i["path"]) or "./"}">{esc(i["label"])}</a></li>' for i in SITE["nav"])
    return f"""<footer class="site-footer">
  <div class="wrap">
    <div class="footer-inner">
      <div class="footer-brand">
        <img src="{root}assets/img/logo.jpg" alt="">
        <div><strong>{esc(SITE['name'])}</strong><span>Birmingham, Alabama</span></div>
      </div>
      <nav class="footer-nav" aria-label="Footer"><ul>{links}</ul></nav>
    </div>
    <div class="footer-meta">
      <p>&copy; {YEAR} {esc(SITE['name'])}. All rights reserved.</p>
      <p class="social"><a href="{esc(SITE['xUrl'])}" target="_blank" rel="noopener">{X_ICON} Follow on X</a> <a href="{root}feed.xml">RSS</a></p>
    </div>
  </div>
</footer>"""


def head(meta, path, root, extra_head=""):
    title = meta["title"] if meta.get("fullTitle") else f"{meta['title']} | {SITE['name']}"
    desc = meta["description"]
    canonical = "" if path == "404.html" else SITE["url"] + "/" + (quote(path, safe="/") if path else "")
    image = SITE["url"] + "/" + meta.get("image", "assets/img/og-default.jpg")
    og_type = meta.get("ogType", "website")
    card = "summary_large_image"
    robots = '<meta name="robots" content="noindex">\n' if meta.get("noindex") else ""
    canon_tag = f'<link rel="canonical" href="{canonical}">\n' if canonical else ""
    og_url = f'<meta property="og:url" content="{canonical}">\n' if canonical else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc, quote=True)}">
{robots}{canon_tag}<meta name="theme-color" content="#34454c">
<link rel="icon" href="{root}assets/img/favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="{root}assets/img/favicon-192.png" sizes="192x192" type="image/png">
<link rel="apple-touch-icon" href="{root}assets/img/apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="{esc(SITE['name'], quote=True)}" href="{root}feed.xml">
<link rel="preload" href="{root}assets/fonts/mulish-normal-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{root}assets/css/site.css?v={CSS_V}">
<meta property="og:site_name" content="{esc(SITE['name'], quote=True)}">
<meta property="og:title" content="{esc(title, quote=True)}">
<meta property="og:description" content="{esc(desc, quote=True)}">
<meta property="og:type" content="{og_type}">
{og_url}<meta property="og:image" content="{image}">
<meta name="twitter:card" content="{card}">
<meta name="twitter:site" content="@{SITE['twitterHandle']}">
<meta name="twitter:title" content="{esc(title, quote=True)}">
<meta name="twitter:description" content="{esc(desc, quote=True)}">
<meta name="twitter:image" content="{image}">
{extra_head}</head>"""


def json_ld(data):
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"


def page(meta, body, path):
    root = root_for(path)
    body = body.replace("{{root}}", root)
    cls = "page-" + meta["class"] if meta.get("class") else ""
    document = (
        head(meta, path, root, meta.get("_extra_head", ""))
        + f'\n<body class="{cls}">\n<a class="skip-link" href="#main">Skip to content</a>\n'
        + header(path, root)
        + f'\n<main id="main">\n{body}\n</main>\n'
        + footer(root)
        + f'\n<script src="{root}assets/js/site.js?v={JS_V}" defer></script>\n</body>\n</html>\n'
    )
    return add_dimensions(document)


def write(rel, text):
    out = ROOT / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


# ---- news / posts
def news_section(root):
    items = []
    for i, p in enumerate(POSTS):
        href = post_href(p, root)
        extra = " is-extra" if i >= 10 else ""
        media = ""
        if p.get("image"):
            media = (f'<a class="news-item__media" href="{href}" tabindex="-1" aria-hidden="true">'
                     f'<img src="{root}{p["image"]}" alt="" loading="lazy"></a>')
        items.append(
            f'<li class="news-item{extra}">{media}<div class="news-item__body">'
            f'<p class="meta"><time datetime="{p["date"]}">{fmt_date(p["date"])}</time></p>'
            f'<h3><a href="{href}">{esc(p["title"])}</a></h3>'
            f'<p>{esc(p["excerpt"])}</p>'
            f'<a class="more-link" href="{href}">Continue reading<span class="sr-only">: {esc(p["title"])}</span></a>'
            f'</div></li>'
        )
    return (f'<section class="section section--tint" id="news"><div class="wrap">'
            f'<h2 class="section-title">Recent News</h2>'
            f'<ul class="news-list" data-news-list>{"".join(items)}</ul></div></section>')


def build_post(index):
    p = POSTS[index]
    path = post_dir(p)
    root = root_for(path)
    canonical = SITE["url"] + "/" + quote(path, safe="/")
    body = p["html"].replace("{{root}}", root)
    older = POSTS[index + 1] if index + 1 < len(POSTS) else None
    newer = POSTS[index - 1] if index > 0 else None
    nav = ""
    if older:
        nav += f'<a class="prev" href="{post_href(older, root)}"><small>Older post</small>{esc(older["title"])}</a>'
    if newer:
        nav += f'<a class="next" href="{post_href(newer, root)}"><small>Newer post</small>{esc(newer["title"])}</a>'
    share_text = quote(p["title"])
    share_url = quote(canonical, safe="")
    article = f"""<article class="post">
  <div class="wrap">
    <header class="post-header">
      <p class="crumb"><a href="{root}#news">&larr; All posts</a></p>
      <p class="meta"><time datetime="{p['date']}">{fmt_date(p['date'])}</time></p>
      <h1>{esc(p['title'])}</h1>
    </header>
    <div class="prose">
{body}
    </div>
    <footer class="post-footer">
      <div class="share"><span>Share this post</span>
        <a href="https://x.com/intent/post?text={share_text}&amp;url={share_url}&amp;via={SITE['twitterHandle']}" target="_blank" rel="noopener">X</a>
        <a href="https://www.facebook.com/sharer/sharer.php?u={share_url}" target="_blank" rel="noopener">Facebook</a>
        <button type="button" data-copy-link="{esc(canonical, quote=True)}" hidden>Copy link</button>
      </div>
      <nav class="post-nav" aria-label="More posts">{nav}</nav>
    </footer>
  </div>
</article>"""
    image = p.get("image")
    ld = {
        "@context": "https://schema.org", "@type": "BlogPosting", "headline": p["title"],
        "datePublished": p["date"], "dateModified": p["date"], "mainEntityOfPage": canonical,
        "author": {"@type": "Organization", "name": SITE["name"]},
        "publisher": {"@type": "Organization", "name": SITE["name"],
                      "logo": {"@type": "ImageObject", "url": SITE["url"] + "/assets/img/logo.jpg"}},
        "description": p["excerpt"],
    }
    if image:
        ld["image"] = SITE["url"] + "/" + image
    desc = p["excerpt"] if len(p["excerpt"]) <= 160 else p["excerpt"][:157].rsplit(" ", 1)[0] + "…"
    meta = {"title": p["title"], "description": desc, "class": "post", "ogType": "article",
            "image": image or "assets/img/og-default.jpg", "_extra_head": json_ld(ld)}
    write(path + "index.html", page(meta, article, path))


# ---- studies / team / publications
def studies_active():
    out = []
    for s in STUDIES["active"]:
        out.append(
            f'<article class="study card"><div class="study__head"><h2 class="study__title">{esc(s["title"])}</h2>'
            f'<span class="status"><span class="sr-only">Status: </span>{esc(s["status"])}</span></div>'
            f'<p class="study__eligible"><strong>Eligible infants:</strong> {esc(s["eligible"])}</p>'
            f'<p>{s["description"]}</p>'
            f'<a class="more-link" href="{esc(s["url"], quote=True)}" target="_blank" rel="noopener">{esc(s["linkLabel"])}</a></article>'
        )
    return f'<div class="study-list">{"".join(out)}</div>'


def studies_completed():
    out = []
    for s in STUDIES["completed"]:
        out.append(
            f'<article><h3>{esc(s["title"])}</h3><p>{esc(s["description"])}</p>'
            f'<p class="cite"><a href="{esc(s["url"], quote=True)}" target="_blank" rel="noopener">{esc(s["linkLabel"])}</a></p></article>'
        )
    return f'<div class="completed-list">{"".join(out)}</div>'


def team_grid():
    out = []
    for m in TEAM:
        initials = "".join(w[0] for w in m["name"].split(",")[0].split()[:2]).upper()
        if m.get("photo"):
            photo = f'<div class="person__photo"><img src="{{{{root}}}}{m["photo"]}" alt="Portrait of {esc(m["name"].split(",")[0])}" loading="lazy"></div>'
        else:
            photo = f'<div class="person__photo person__photo--initials" aria-hidden="true">{initials}</div>'
        link = ""
        if m.get("url"):
            link = f'<a class="more-link" href="{esc(m["url"], quote=True)}" target="_blank" rel="noopener">{esc(m["linkLabel"])}<span class="sr-only"> about {esc(m["name"].split(",")[0])}</span></a>'
        out.append(f'<li class="person">{photo}<h3>{esc(m["name"])}</h3><p class="role">{esc(m["role"])}</p><p>{esc(m["bio"])}</p>{link}</li>')
    return f'<ul class="team-grid">{"".join(out)}</ul>'


def publications_section():
    all_items = [it for g in PUBS for it in g["items"]]
    counts = {}
    for it in all_items:
        for t in it["tags"]:
            counts[t] = counts.get(t, 0) + 1
    ordered = sorted(counts, key=lambda t: (-counts[t], t))
    chips = [f'<button type="button" class="chip" data-tag="" aria-pressed="true">All<span>{len(all_items)}</span></button>']
    chips += [f'<button type="button" class="chip" data-tag="{esc(t, quote=True)}" aria-pressed="false">{esc(t)}<span>{counts[t]}</span></button>'
              for t in ordered]
    tools = f"""<div class="pub-tools" data-pub-tools hidden>
  <div class="wrap">
    <label class="sr-only" for="pub-search">Search publications</label>
    <input class="pub-search" id="pub-search" type="search" placeholder="Search titles, authors, or journals" autocomplete="off">
    <div class="chips" role="group" aria-label="Filter by topic">{''.join(chips)}</div>
    <p class="pub-count" aria-live="polite"></p>
  </div>
</div>"""
    groups = []
    for g in PUBS:
        items = []
        for it in g["items"]:
            badges = ""
            if it["freeArticle"]:
                badges += '<span class="badge">Free article</span>'
            if it.get("videoAbstract"):
                badges += f'<a class="badge badge--video" href="{esc(it["videoAbstract"], quote=True)}" target="_blank" rel="noopener">Video abstract</a>'
            tags = "".join(f"<li>{esc(t)}</li>" for t in it["tags"])
            tag_list = f'<ul class="pub__tags" aria-label="Topics">{tags}</ul>' if tags else ""
            haystack = " ".join([it["authors"], it["title"], it["source"], " ".join(it["tags"])]).lower()
            items.append(
                f'<li class="pub" data-tags="{esc("|".join(it["tags"]), quote=True)}" data-text="{esc(haystack, quote=True)}">'
                f'<p class="pub__authors">{esc(it["authors"])}</p>'
                f'<h3 class="pub__title"><a href="{esc(it["url"], quote=True)}" target="_blank" rel="noopener">{esc(it["title"])}</a></h3>'
                f'<p class="pub__source">{esc(it["source"])}{badges}</p>{tag_list}</li>'
            )
        groups.append(f'<section class="pub-group" id="{g["id"]}"><h2>{esc(g["title"])}</h2><ol class="pub-list">{"".join(items)}</ol></section>')
    return (tools + '<section class="section" style="padding-top:0"><div class="wrap">' + "".join(groups) +
            '<p class="pub-empty" hidden>No publications match your search. Try a different word or topic.</p></div></section>')


# ---- contact / forms
def contact_card():
    c = SITE["contact"]
    coordinators = "".join(f"<li>{esc(n)}</li>" for n in c["coordinators"])
    address = "<br>".join(esc(l) for l in c["address"])
    return f"""<div class="card contact-card">
  <div>
    <h3>{esc(c['site'])}</h3>
    <address>{address}</address>
    <a class="btn btn--outline" href="{esc(c['mapsUrl'], quote=True)}" target="_blank" rel="noopener">Get directions</a>
  </div>
  <dl>
    <dt>Study coordinators</dt><dd><ul style="list-style:none;margin:0;padding:0">{coordinators}</ul></dd>
    <dt>Phone</dt><dd><a class="phone" href="{c['phoneHref']}">{esc(c['phone'])}</a></dd>
    <dt>Hours</dt><dd>{esc(c['hours'])}</dd>
  </dl>
</div>"""


def contact_form():
    endpoint = SITE.get("formEndpoint")
    if not endpoint:
        return ""
    return f"""<section class="section">
  <div class="wrap wrap--narrow">
    <h2 class="section-title">Drop us a line!</h2>
    <form class="form" method="post" action="{esc(endpoint, quote=True)}" data-endpoint="{esc(endpoint, quote=True)}">
      <label>Name<input type="text" name="name" autocomplete="name"></label>
      <label>Email*<input type="email" name="email" required autocomplete="email"></label>
      <label>Phone<input type="tel" name="phone" autocomplete="tel"></label>
      <label>Message<textarea name="message" required></textarea></label>
      <input class="hp" type="text" name="_gotcha" tabindex="-1" autocomplete="off" aria-hidden="true">
      <div><button class="btn" type="submit">Send</button></div>
      <p class="form-status" role="status"></p>
    </form>
  </div>
</section>"""


def subscribe_section():
    endpoint = SITE.get("formEndpoint")
    if not endpoint:
        return ""
    return f"""<section class="section subscribe" id="subscribe">
  <div class="wrap wrap--narrow">
    <h2 class="section-title">Subscribe</h2>
    <form class="inline-form" method="post" action="{esc(endpoint, quote=True)}" data-endpoint="{esc(endpoint, quote=True)}" data-success="Thanks for subscribing!">
      <input type="hidden" name="form" value="subscribe">
      <label class="form" style="gap:.35rem">Email Address<input type="email" name="email" required autocomplete="email"></label>
      <input class="hp" type="text" name="_gotcha" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px">
      <button class="btn" type="submit">Sign up</button>
      <p class="form-status" role="status" style="flex-basis:100%"></p>
    </form>
  </div>
</section>"""


# ---------------------------------------------------------------- build
PAGES = ["home", "about-us", "studies", "resources", "publications", "contact-us", "milk", "body-composition", "gallery", "404"]
GENERATED = ["index.html", "404.html", "feed.xml", "sitemap.xml", "robots.txt", "f"] + \
    ["about-us", "studies", "resources", "publications", "contact-us", "milk", "body-composition", "gallery"]


def clean():
    for name in GENERATED:
        target = ROOT / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def build_pages():
    for name in PAGES:
        meta, body = load_fragment(name)
        path = meta["path"]
        root = root_for(path)
        replacements = {
            "{{news}}": news_section(root),
            "{{subscribe}}": subscribe_section(),
            "{{team}}": team_grid(),
            "{{studies_active}}": studies_active(),
            "{{studies_completed}}": studies_completed(),
            "{{publications}}": publications_section(),
            "{{contact_card}}": contact_card(),
            "{{contact_form}}": contact_form(),
        }
        for token, value in replacements.items():
            body = body.replace(token, value)
        if name == "home":
            ld = {"@context": "https://schema.org", "@type": "Organization", "name": SITE["name"], "url": SITE["url"],
                  "logo": SITE["url"] + "/assets/img/logo.jpg", "sameAs": [SITE["xUrl"]], "description": SITE["description"]}
            meta["_extra_head"] = json_ld(ld)
        target = "404.html" if name == "404" else (path + "index.html" if path else "index.html")
        write(target, page(meta, body, path))


def build_feed():
    site_url = SITE["url"]
    items = []
    for p in POSTS:
        link = f"{site_url}/f/{quote(p['slug'])}/"
        d = datetime.datetime.fromisoformat(p["date"] + "T12:00:00+00:00")
        items.append(
            f"<item><title>{esc(p['title'])}</title><link>{link}</link><guid isPermaLink=\"true\">{link}</guid>"
            f"<pubDate>{format_datetime(d)}</pubDate><description>{esc(p['excerpt'])}</description></item>"
        )
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
        f"<title>{esc(SITE['name'])}</title><link>{site_url}/</link><description>{esc(SITE['description'])}</description>"
        f"<language>en-us</language>{''.join(items)}</channel></rss>\n"
    )
    write("feed.xml", feed)


def build_sitemap_and_robots():
    urls = [(SITE["url"] + "/", None)]
    for item in SITE["nav"]:
        if item["path"]:
            urls.append((SITE["url"] + "/" + item["path"], None))
    for extra in ("milk/", "body-composition/", "gallery/"):
        urls.append((SITE["url"] + "/" + extra, None))
    for p in POSTS:
        urls.append((f"{SITE['url']}/f/{quote(p['slug'])}/", p["date"]))
    body = "".join(f"<url><loc>{u}</loc>{f'<lastmod>{d}</lastmod>' if d else ''}</url>" for u, d in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE['url']}/sitemap.xml\n")


# ---------------------------------------------------------------- self-check
def check_output():
    problems = []
    pages = [p for p in ROOT.rglob("*.html") if not any(part in ("content", "tools", ".git") for part in p.relative_to(ROOT).parts)]
    for f in pages:
        text = f.read_text(encoding="utf-8")
        ids = set(re.findall(r'\bid="([^"]+)"', text))
        for attr, ref in re.findall(r'\b(href|src)="([^"]*)"', text):
            if not ref or re.match(r"(https?:|mailto:|tel:|data:|#|javascript:)", ref):
                if ref.startswith("#") and len(ref) > 1 and unquote(ref[1:]) not in ids:
                    problems.append(f"{f.relative_to(ROOT)}: missing anchor {ref}")
                continue
            if f.name == "404.html" and ref.startswith("/"):
                target = ROOT / unquote(urlsplit(ref).path.lstrip("/"))
            else:
                target = (f.parent / unquote(urlsplit(ref).path)).resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                problems.append(f"{f.relative_to(ROOT)}: broken {attr} {ref}")
            elif urlsplit(ref).fragment and target.suffix == ".html":
                tid = set(re.findall(r'\bid="([^"]+)"', target.read_text(encoding="utf-8")))
                if unquote(urlsplit(ref).fragment) not in tid:
                    problems.append(f"{f.relative_to(ROOT)}: missing anchor #{urlsplit(ref).fragment} in {ref}")
    return problems, len(pages)


def main():
    clean()
    build_pages()
    for i in range(len(POSTS)):
        build_post(i)
    build_feed()
    build_sitemap_and_robots()
    problems, count = check_output()
    print(f"Built {count} pages ({len(POSTS)} news posts).")
    if problems:
        print("\nProblems found:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("Link check passed: all internal links, images and anchors resolve.")


if __name__ == "__main__":
    main()
