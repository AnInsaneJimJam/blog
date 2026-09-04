#!/usr/bin/env python3
"""Build the blog: posts/<YYYY-MM-DD-slug>/index.md -> docs/<slug>/index.html"""
import re, shutil, sys
from email.utils import format_datetime
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote

import markdown

ROOT = Path(__file__).parent
AUTHOR = "JimJam"
SITE_TITLE = "JimJam's blogs"
SITE_URL = "https://anandbansal.me"
DOMAIN = "anandbansal.me"   # GitHub Pages reads this from docs/CNAME
FOLDER_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def load_icons(root):
    """Vendored Feather icons (MIT). stroke=currentColor, so they take the link colour."""
    return {p.stem: p.read_text().strip()
            for p in sorted((root / "icons").glob("*.svg"))}


def expand_icons(text, icons):
    return re.sub(r"\{\{icon:(\w+)\}\}", lambda m: icons.get(m.group(1), ""), text)


def share_row(title, url, icons):
    """Plain links -- no third-party scripts, nothing loaded from the networks."""
    targets = [
        ("twitter", f"https://twitter.com/intent/tweet?url={quote(url, safe='')}&text={quote(title, safe='')}"),
        ("facebook", f"https://www.facebook.com/sharer/sharer.php?u={quote(url, safe='')}"),
        ("linkedin", f"https://www.linkedin.com/sharing/share-offsite/?url={quote(url, safe='')}"),
        ("mail", f"mailto:?subject={quote(title, safe='')}&body={quote(url, safe='')}"),
    ]
    links = "".join(
        f'<a href="{href}" title="Share on {name}" aria-label="Share on {name}"'
        f' rel="noopener" target="_blank">{icons.get(name, name)}</a>'
        for name, href in targets)
    return f'<p class="share"><span>Share on:</span>{links}</p>'


def pretty_date(iso):
    y, m, d = iso.split("-")
    return f"{MONTHS[int(m) - 1]} {int(d)}, {y}"


def render(template, title, head="", content="", nav=""):
    """Fill the template. str.replace, not str.format -- CSS braces break format."""
    return (template
            .replace("{{title}}", title)
            .replace("{{head}}", head)
            .replace("{{content}}", content)
            .replace("{{nav}}", nav))


def post_nav(older):
    """Older post on the left, archive on the right, chevrons on the outside."""
    left = (f'<a class="prev" href="../{older[1]}/">'
            f'<span class="arrow">&lsaquo;</span>'
            f'<span><span class="lbl">Previous Post</span>'
            f'<span class="t">{escape(older[2])}</span></span></a>') if older else "<span></span>"
    return (f'<nav class="postnav">{left}'
            f'<a class="next" href="/">'
            f'<span><span class="lbl">Blog Archive</span>'
            f'<span class="t">All previous posts</span></span>'
            f'<span class="arrow">&rsaquo;</span></a></nav>')


def write_feed(docs, entries):
    """Minimal RSS 2.0. Readers want absolute URLs, hence SITE_URL."""
    items = "".join(
        f"<item><title>{escape(t)}</title>"
        f"<link>{SITE_URL}/{s}/</link><guid>{SITE_URL}/{s}/</guid>"
        f"<pubDate>{format_datetime(datetime.fromisoformat(d).replace(tzinfo=timezone.utc))}</pubDate>"
        f"<description>{escape(html)}</description></item>"
        for d, s, t, html in entries)
    (docs / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel>'
        f"<title>{escape(SITE_TITLE)}</title><link>{SITE_URL}/</link>"
        f"<description>{escape(SITE_TITLE)}</description>{items}"
        "</channel></rss>")


def build(root=ROOT, out=None):
    posts_dir = root / "posts"
    docs = out or root.parent / "docs"      # <repo>/docs is what Pages serves
    icons = load_icons(root)
    template = expand_icons((root / "template.html").read_text(), icons)
    md = markdown.Markdown(extensions=["fenced_code", "tables", "smarty"])

    if docs.exists():
        if not (docs / "index.html").exists() and any(docs.iterdir()):
            raise SystemExit(f"refusing to wipe {docs}: does not look like build output")
        shutil.rmtree(docs)          # rebuild clean so deleted posts really vanish
    docs.mkdir(parents=True)
    shutil.copy(root / "style.css", docs / "style.css")

    entries = []
    for folder in sorted(posts_dir.iterdir()) if posts_dir.exists() else []:
        m = FOLDER_RE.match(folder.name)
        if not folder.is_dir() or folder.name.startswith("_") or not m:
            continue                 # drafts and stray files
        date, slug = m.groups()
        text = (folder / "index.md").read_text()

        # copy the whole post folder so images land beside the html
        shutil.copytree(folder, docs / slug, ignore=shutil.ignore_patterns("index.md"))

        heading = re.search(r"^#\s+(.+)$", text, re.M)
        title = heading.group(1).strip() if heading else slug
        if heading:
            text = text[:heading.start()] + text[heading.end():]   # template renders it
        md.reset()
        entries.append((date, slug, title, md.convert(text)))

    entries.sort(key=lambda e: (e[0], e[1]), reverse=True)   # newest first
    for i, (date, slug, title, html) in enumerate(entries):
        older = entries[i + 1] if i + 1 < len(entries) else None
        head = (f'<h1>{escape(title)}</h1>'
                f'<p class="meta">{pretty_date(date)} &middot; {AUTHOR}</p>'
                + share_row(title, f"{SITE_URL}/{slug}/", icons))
        (docs / slug / "index.html").write_text(
            render(template, title, head, html, post_nav(older)))

    links = "\n".join(
        f'<li><span class="meta">{pretty_date(d)}</span>'
        f'<a href="{s}/">{t}</a></li>' for d, s, t, _ in entries)
    (docs / "index.html").write_text(
        render(template, SITE_TITLE, "", f'<ul class="posts">\n{links}\n</ul>'))
    write_feed(docs, entries)
    (docs / "CNAME").write_text(DOMAIN + "\n")     # custom domain for GitHub Pages
    (docs / ".nojekyll").write_text("")             # serve the files as-is, no Jekyll
    return [(d, s, t) for d, s, t, _ in entries]


def selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "template.html").write_text("{{title}}|{{head}}|{{content}}|{{nav}}")
        (root / "style.css").write_text("body{color:red}")
        for name, body in [("2026-01-02-older", "# Older\n\ntext"),
                           ("2026-03-04-newer", "# Newer\n\ntext"),
                           ("_2026-05-06-draft", "# Draft\n"),
                           ("not-a-post", "# Nope\n")]:
            (root / "posts" / name).mkdir(parents=True)
            (root / "posts" / name / "index.md").write_text(body)
        (root / "posts" / "2026-03-04-newer" / "plot.png").write_bytes(b"PNG")

        posts = build(root, out=root / 'docs')
        assert posts == [("2026-03-04", "newer", "Newer"),
                         ("2026-01-02", "older", "Older")], posts
        assert (root / "docs/newer/plot.png").read_bytes() == b"PNG"   # images copied
        assert not (root / "docs/newer/index.md").exists()             # source not shipped
        assert not (root / "docs/draft").exists()                      # drafts skipped
        newer = (root / "docs/newer/index.html").read_text()
        assert "<h1>Newer</h1>" in newer
        assert newer.count("<h1>") == 1           # title not duplicated in the body
        assert "Mar 4, 2026 &middot; JimJam" in newer
        assert "twitter.com/intent" in newer and "%2Fnewer%2F" in newer   # share links
        assert '../older/' in newer                                    # links to older post
        assert '../' not in (root / "docs/older/index.html").read_text()  # oldest: no prev
        index = (root / "docs/index.html").read_text()
        assert index.index("newer/") < index.index("older/")           # newest first
        feed = (root / "docs/feed.xml").read_text()
        assert feed.count("<item>") == 2 and "/newer/" in feed          # drafts stay out
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        print(f"built {len(build())} posts -> docs/")
