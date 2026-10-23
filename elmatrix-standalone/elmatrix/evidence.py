"""Source-linked evidence collection and storage. Network access is opt-in per feed."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import hashlib, ipaddress, json, os, re, socket, sqlite3
from pathlib import Path
from xml.etree import ElementTree as ET
from urllib.request import HTTPRedirectHandler, build_opener

USER_AGENT = "ElmatrixResearch/0.3 (+public RSS reader; bounded requests)"
MAX_FEED_BYTES = 2_000_000
MAX_ITEMS = 100

@dataclass
class Evidence:
    source_name: str
    source_url: str
    canonical_url: str
    retrieved_at: str
    published_at: str
    query: str
    region: str
    title: str
    observation: str
    metric: str
    value: str
    content_hash: str
    source_type: str = "public_rss"

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def canonicalize_url(url: str) -> str:
    if not isinstance(url, str) or len(url) > 4096 or any(ord(c) < 33 for c in url):
        raise ValueError("URL contains whitespace/control characters or exceeds limits.")
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("Only absolute HTTP(S) URLs are supported.")
    if p.username or p.password:
        raise ValueError("URLs containing credentials are not allowed.")
    host = p.hostname.lower()
    if "%" in host:
        raise ValueError("Scoped IP addresses are not supported.")
    if ":" in host:
        host = "[" + host + "]"
    port = p.port
    netloc = host if not port or (p.scheme == "http" and port == 80) or (p.scheme == "https" and port == 443) else f"{host}:{port}"
    # Tracking query parameters are removed; meaningful query parameters remain.
    query = "&".join(x for x in p.query.split("&") if x and not x.lower().startswith(("utm_", "fbclid=", "gclid=")))
    return urlunparse((p.scheme.lower(), netloc, p.path or "/", "", query, ""))

def validate_public_url(url: str) -> str:
    """Validate an HTTP(S) destination and reject local/private address targets."""
    canonical = canonicalize_url(url)
    parsed = urlparse(canonical)
    host = (parsed.hostname or "").rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local and internal hostnames are not allowed for feed collection.")
    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        try:
            answers = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except OSError as exc:
            raise ValueError("Feed hostname could not be resolved.") from exc
        addresses = []
        for answer in answers:
            try:
                addresses.append(ipaddress.ip_address(answer[4][0].split("%", 1)[0]))
            except ValueError:
                continue
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("Feed host must resolve only to globally routable IP addresses.")
    return canonical

class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def _text(node, names):
    for name in names:
        found = node.find(name)
        if found is not None and found.text:
            return " ".join(unescape(found.text).split())
    return ""

def _parse_date(value):
    if not value:
        return ""
    value = value.strip()
    if not value:
        return ""
    try:
        # Atom uses ISO 8601/RFC 3339; RSS commonly uses email-style dates.
        try:
            d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError, OverflowError):
            d = parsedate_to_datetime(value)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError, OverflowError):
        return ""

def parse_rss(xml_bytes: bytes, feed_url: str, *, source_name=None, query="", region="global", retrieved_at=None, limit=MAX_ITEMS):
    if len(xml_bytes) > MAX_FEED_BYTES:
        raise ValueError("Feed exceeds 2 MB limit.")
    if b"\x00" in xml_bytes or re.search(br"<!\s*(DOCTYPE|ENTITY)\b", xml_bytes, re.I):
        raise ValueError("DTD/entity declarations and NUL-encoded XML are not accepted.")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"Feed is not valid XML: {exc}") from exc
    # RSS 2.0 and Atom, without resolving external entities or fetching linked pages.
    is_atom = root.tag.rsplit("}", 1)[-1].lower() == "feed"
    nodes = root.findall(".//{*}entry") if is_atom else root.findall(".//item")
    now = retrieved_at or utc_now()
    results = []
    for node in nodes[:max(1, min(int(limit), MAX_ITEMS))]:
        if is_atom:
            title = _text(node, ["{*}title"])
            summary = _text(node, ["{*}summary", "{*}content"])
            link_node = next((n for n in node.findall("{*}link") if n.get("rel", "alternate") == "alternate"), None)
            link = link_node.attrib.get("href", "") if link_node is not None else ""
            published = _text(node, ["{*}published", "{*}updated"])
        else:
            title = _text(node, ["title"])
            summary = _text(node, ["description", "encoded"])
            link = _text(node, ["link"])
            published = _text(node, ["pubDate", "date"])
        if not title or not link:
            continue
        try:
            canonical = canonicalize_url(link)
        except ValueError:
            continue
        # Remove markup conservatively; summary remains a short observation, not verified truth.
        summary = re.sub(r"<[^>]*>", " ", summary)
        summary = " ".join(unescape(summary).split())[:1200]
        observation = summary or title
        digest = hashlib.sha256((canonical + "\n" + title).encode("utf-8")).hexdigest()
        results.append(Evidence(
            source_name=source_name or urlparse(feed_url).hostname or "public feed",
            source_url=canonicalize_url(feed_url), canonical_url=canonical,
            retrieved_at=now, published_at=_parse_date(published),
            query=query, region=region, title=title[:500], observation=observation,
            metric="published_item", value="observed; not a demand or revenue metric",
            content_hash=digest))
    return results

def open_db(path=None):
    if path is None:
        home = Path(os.environ.get("ELMATRIX_HOME", Path.home()/".elmatrix-standalone"))
        if home.is_symlink() or any(x.is_symlink() for x in home.absolute().parents):
            raise ValueError("Storage directory must not contain symlinks.")
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
        try: home.chmod(0o700)
        except OSError: pass
        path = home / "elmatrix.sqlite3"
    path = Path(path)
    if any(parent.is_symlink() for parent in path.absolute().parents):
        raise ValueError("Database parents must not be symlinks.")
    import stat
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
            raise ValueError("Database must be an owned regular file with one link.")
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)
    for suffix in ('-journal', '-wal', '-shm'):
        sidecar = Path(str(path) + suffix)
        if sidecar.is_symlink() or (sidecar.exists() and (not sidecar.is_file() or sidecar.stat().st_nlink != 1)):
            raise ValueError("Unsafe database sidecar.")
    db = sqlite3.connect(str(path))
    try:
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='schema_meta'").fetchone():
            versions = db.execute("SELECT version FROM schema_meta").fetchall()
            if versions != [(1,)]:
                raise ValueError("Unsupported database schema; preserve data and use a compatible version.")
    except BaseException:
        db.close()
        raise
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER NOT NULL);
    INSERT INTO schema_meta(version) SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM schema_meta);
    CREATE TABLE IF NOT EXISTS evidence (
      id INTEGER PRIMARY KEY, source_name TEXT NOT NULL, source_url TEXT NOT NULL,
      canonical_url TEXT NOT NULL, retrieved_at TEXT NOT NULL, published_at TEXT NOT NULL DEFAULT '',
      query TEXT NOT NULL DEFAULT '', region TEXT NOT NULL DEFAULT 'global',
      title TEXT NOT NULL, observation TEXT NOT NULL, metric TEXT NOT NULL,
      value TEXT NOT NULL, content_hash TEXT NOT NULL UNIQUE, source_type TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE INDEX IF NOT EXISTS evidence_canonical_idx ON evidence(canonical_url);
    CREATE INDEX IF NOT EXISTS evidence_retrieved_idx ON evidence(retrieved_at);
    CREATE TABLE IF NOT EXISTS experiments (
      id INTEGER PRIMARY KEY, opportunity_id TEXT NOT NULL, hypothesis TEXT NOT NULL,
      metric TEXT NOT NULL, target TEXT NOT NULL, result TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    """)
    db.commit()
    return db

def fetch_rss(url, *, timeout=8, max_bytes=MAX_FEED_BYTES):
    from .transport import fetch
    if type(timeout) is not int or not 1 <= timeout <= 15:
        raise ValueError("Timeout must be 1–15 seconds.")
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_FEED_BYTES:
        raise ValueError("Invalid response byte limit.")
    return fetch(url, canonicalize_url, timeout=timeout, max_bytes=max_bytes, user_agent=USER_AGENT)

def collect_feed(url, *, source_name=None, query="", region="global", timeout=8, limit=MAX_ITEMS):
    data, feed_url = fetch_rss(url, timeout=timeout)
    return parse_rss(data, feed_url, source_name=source_name, query=query, region=region, limit=limit)

def save_evidence(items, db=None):
    owns = db is None
    db = db or open_db()
    inserted = 0
    try:
        with db:
            for item in items:
                d = asdict(item)
                cur = db.execute("""INSERT OR IGNORE INTO evidence
                (source_name,source_url,canonical_url,retrieved_at,published_at,query,region,title,observation,metric,value,content_hash,source_type)
                VALUES(:source_name,:source_url,:canonical_url,:retrieved_at,:published_at,:query,:region,:title,:observation,:metric,:value,:content_hash,:source_type)""", d)
                inserted += cur.rowcount
    finally:
        if owns: db.close()
    return inserted

def list_evidence(db=None, limit=100):
    owns = db is None
    db = db or open_db()
    try:
        return [dict(r) for r in db.execute("SELECT * FROM evidence ORDER BY retrieved_at DESC,id DESC LIMIT ?", (max(1,min(int(limit),500)),))]
    finally:
        if owns: db.close()
