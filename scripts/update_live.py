#!/usr/bin/env python3
"""Top 30 Berita Saham: ambil berita terbaru dari lima media, kelompokkan per peristiwa,
tulis data/live.json untuk aplikasi. Hanya pustaka standar Python.

Dijalankan GitHub Actions kira-kira tiap 10 menit. Jendela bergulir 24 jam, tanpa edisi final.
"""
import hashlib
import html
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

WIB = timezone(timedelta(hours=7))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "data", "live.json")
STORE = os.path.join(ROOT, "data", "articles.json")
WINDOW_H = 24          # topik dihitung dari artikel 24 jam terakhir
KEEP_H = 36            # artikel disimpan sedikit lebih lama agar tidak hilang saat RSS bergulir
PREV_EVERY_MIN = 60    # panah naik/turun dibanding peringkat sekitar 1 jam lalu
REFRESH_MIN = 30       # tulis ulang file walau isi sama, supaya jam "dicek" tidak basi
TARGET = 30
UA = "Mozilla/5.0 (compatible; Top30BeritaSaham/1.0; +https://github.com/rhezadestra/top30-saham)"


def gnews(q):
    return "https://news.google.com/rss/search?q=" + quote(q + " when:1d") + "&hl=id&gl=ID&ceid=ID:id"


# Sumber per media: RSS langsung dulu; jika gagal atau kosong, Google News RSS per situs.
MEDIA = [
    {"name": "Kontan", "abbr": "KON", "domains": ["kontan.co.id"],
     "direct": [],  # rss.kontan.co.id menolak akses server (403)
     "google": [gnews("site:investasi.kontan.co.id"), gnews("site:insight.kontan.co.id"),
                gnews("site:keuangan.kontan.co.id"), gnews("site:nasional.kontan.co.id saham OR emiten OR investasi")]},
    {"name": "CNBC Indonesia", "abbr": "CNBC", "domains": ["cnbcindonesia.com"],
     "direct": ["https://www.cnbcindonesia.com/market/rss"],
     "google": [gnews("site:cnbcindonesia.com/market"), gnews("site:cnbcindonesia.com/research")]},
    {"name": "IDX Channel", "abbr": "IDXC", "domains": ["idxchannel.com"],
     "direct": ["https://www.idxchannel.com/rss"],
     "google": [gnews("site:idxchannel.com/market-news"), gnews("site:idxchannel.com/economics")]},
    {"name": "Bisnis", "abbr": "BIS", "domains": ["bisnis.com"],
     "direct": [],  # bisnis.com memasang tantangan Cloudflare untuk server
     "google": [gnews("site:market.bisnis.com"), gnews("site:finansial.bisnis.com"),
                gnews("site:ekonomi.bisnis.com saham OR emiten OR investasi")]},
    {"name": "Investor.id", "abbr": "INV", "domains": ["investor.id"],
     "direct": [],  # investor.id/rss mengembalikan 404
     "google": [gnews("site:investor.id/market"), gnews("site:investor.id/finance"), gnews("site:investor.id saham OR emiten")]},
]

CATS = ["Aksi korporasi", "Regulasi", "Kinerja", "Makro"]

# Berita pergerakan harga dan yang dibuang sesuai keputusan: selalu dibuang.
HARD_EXCLUDE = re.compile(r"""
  \bihsg\b | indeks\ harga\ saham\ gabungan | \blq45\b.*\b(menguat|melemah)\b |
  \b(dibuka|ditutup)\ (menguat|melemah|naik|turun|hijau|merah|stagnan) | \bsesi\ (i|ii|1|2)\b |
  top\ (gainer|loser)s? | net\ (buy|sell) | asing\ (borong|lepas|jual|beli|obral) | jual\ bersih\ asing | beli\ bersih\ asing |
  harga\ emas | emas\ antam | buyback\ emas | \bkurs\b | \brupiah\b | dolar\ as\ (menguat|melemah) | \bbitcoin\b | \bkripto\b | \bcrypto\b |
  rekomendasi\ saham | saham\ pilihan | analisis\ teknikal | rekomendasi\ teknikal | \bteknikal\b | trading\ (hari|pekan) |
  saham\ (paling\ )?(cuan|boncos) | saham\ (yang\ )?(ara|arb)\b | \b(ara|arb)\b | proyeksi\ ihsg | gerak\ ihsg |
  \bvideo:? | \bfoto:? | \bpodcast\b | \blive\b: | harga\ (bbm|cabai|beras) |
  kumpulan\ berita | terbaru\ dan\ terkini | berita\ terkini | ^berita\ \w+\ hari\ ini
""", re.I | re.X)

# Pergerakan harga yang masih boleh jika ada peristiwa korporasi di judul.
SOFT_PRICE = re.compile(r"(harga\s+)?saham\s+\S+(\s+\S+)?\s+(melesat|meroket|melonjak|anjlok|ambles|ambruk|terbang|terjun|longsor|menguat|melemah|naik|turun)|"
                        r"(melesat|meroket|anjlok|ambles|terbang)\s+\d", re.I)

CORP = re.compile(r"dividen|rights?\s*issue|hmetd|buyback|\bipo\b|penawaran umum|akuisisi|caplok|merger|divestasi|\brups|stock split|"
                  r"tender offer|private placement|obligasi|sukuk|laba|rugi|pendapatan|penjualan|kontrak|ekspansi", re.I)

RELEVANT = re.compile(r"saham|emiten|\btbk\b|bursa|\bbei\b|\bojk\b|\bipo\b|dividen|rights?\s*issue|buyback|akuisisi|merger|laba|rugi|"
                      r"pendapatan|penjualan|kinerja|obligasi|sukuk|investor|pasar modal|reksa dana|the fed|suku bunga|bi rate|"
                      r"inflasi|tarif|danantara|msci|ekspor|neraca|apbn|\bpdb\b|kuartal|produksi|tender offer|\brups|delisting|"
                      r"suspensi|free float|private placement|stock split|bumn|\bbank\b|batu bara|nikel|cpo|migas|\([A-Z]{4}\)", re.I)

CAT_RULES = [
    ("Aksi korporasi", re.compile(r"dividen|rights?\s*issue|hmetd|pmhmetd|buyback|\bipo\b|penawaran umum|akuisisi|caplok|merger|"
                                  r"divestasi|\brupslb?\b|stock split|tender offer|private placement|obligasi|sukuk|\bmtn\b|"
                                  r"pinjaman|sindikasi|ekspansi|pabrik|kontrak|direksi|komisaris|\bdirut\b|pengendali|"
                                  r"anak usaha|spin.?off|pencatatan|listing", re.I)),
    ("Regulasi", re.compile(r"\bojk\b|\bbei\b|bursa efek|suspensi|suspend|\buma\b|delisting|aturan|regulasi|sanksi|free float|"
                            r"\bhsc\b|msci|pengawasan|\bpojk\b|papan pemantauan|full call auction|denda|manipulasi|"
                            r"kebijakan|undang|\bkppu\b|izin", re.I)),
    ("Kinerja", re.compile(r"laba|rugi|pendapatan|penjualan|kinerja|kuartal|semester|produksi|target|proyeksi|margin|ebitda|"
                           r"volume|kapasitas|okupansi|kredit|pembiayaan|aset", re.I)),
    ("Makro", re.compile(r"the fed|\bfed\b|suku bunga|bi rate|inflasi|\bpdb\b|ekonomi|tarif|neraca|apbn|pajak|cukai|ekspor|"
                         r"impor|harga minyak|global|china|amerika|perang dagang|danantara|\bina\b|bumn|pemerintah", re.I)),
]

EVENT_KEYS = [
    ("dividen", r"dividen"), ("rights", r"rights?\s*issue|hmetd"), ("buyback", r"buyback"), ("ipo", r"\bipo\b|penawaran umum perdana"),
    ("akuisisi", r"akuisisi|caplok|merger|divestasi|tender offer"), ("rups", r"\brups"), ("kinerja", r"laba|rugi|pendapatan|penjualan|kinerja"),
    ("produksi", r"produksi|volume"), ("direksi", r"direksi|komisaris|\bdirut\b"), ("obligasi", r"obligasi|sukuk|\bmtn\b"),
    ("sanksi", r"sanksi|denda|manipulasi"), ("suspensi", r"suspensi|suspend|\buma\b|delisting"), ("placement", r"private placement"),
]

TICKER_STOP = {
    "IHSG", "BUMN", "BUMD", "MSCI", "KSEI", "BPJS", "PLTU", "PLTS", "PLTA", "PLTP", "APBN", "APBD", "OPEC", "ESDM", "KPPU",
    "BPKP", "LPEI", "BRIN", "UMKM", "RUPS", "TKDN", "FOMC", "NYSE", "PSAK", "SPBU", "IDXC", "CNBC", "ASEAN", "OECD", "BRICS",
    "BPOM", "KPK", "PDB", "HMETD", "ODOL", "COVID", "NATO", "EBITDA", "WTI", "LNG", "JISDOR", "LPS", "IKN", "DPR", "MPR",
    "SAAT", "AKAN", "BARU", "LAGI", "JUGA", "BISA", "PADA", "YANG", "INI", "ITU", "USD", "IDR", "TBK", "CEO", "CFO", "GDP",
}

STOPWORDS = set("""yang dan di ke dari untuk pada dengan ini itu dalam akan jadi atau juga karena oleh sebagai bisa lebih
masih telah sudah hingga sampai capai tahun hari bulan pekan per rp us juta miliar triliun persen saham emiten tbk pt
siap siapkan bakal naik turun ada tak tidak cek ini simak berapa begini apa kata soal usai jelang terbaru baru lagi""".split())


def log(*a):
    print(*a, file=sys.stderr)


def fetch(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    with urlopen(req, timeout=25) as r:
        return r.read()


def text_of(el, *names):
    for n in names:
        x = el.find(n)
        if x is not None and (x.text or "").strip():
            return x.text.strip()
    return ""


def parse_time(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=WIB)
    return d.astimezone(WIB)


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def short(s, n=240):
    s = clean(s)
    if len(s) <= n:
        return s
    cut = s[:n]
    dot = cut.rfind(". ")
    if dot > n * 0.5:
        return cut[:dot + 1]
    return cut[:cut.rfind(" ")].rstrip(",;:") + "…"


def parse_feed(raw):
    root = ET.fromstring(raw)
    ns = {"atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/"}
    out = []
    for it in root.iter("item"):
        src = it.find("source")
        out.append({
            "title": clean(text_of(it, "title")),
            "link": text_of(it, "link") or text_of(it, "guid"),
            "time": parse_time(text_of(it, "pubDate", "{http://purl.org/dc/elements/1.1/}date")),
            "desc": text_of(it, "description"),
            "source_url": (src.get("url") if src is not None else "") or "",
            "source_name": (src.text or "").strip() if src is not None else "",
        })
    for it in root.iter("{http://www.w3.org/2005/Atom}entry"):
        link = it.find("atom:link", ns)
        out.append({
            "title": clean(text_of(it, "{http://www.w3.org/2005/Atom}title")),
            "link": link.get("href") if link is not None else "",
            "time": parse_time(text_of(it, "{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated")),
            "desc": text_of(it, "{http://www.w3.org/2005/Atom}summary"),
            "source_url": "", "source_name": "",
        })
    return out


def host_ok(url, domains):
    h = urlparse(url or "").netloc.lower()
    return any(h == d or h.endswith("." + d) for d in domains)


MEDIA_SUFFIX = re.compile(r"\s+[-–|]\s+(bisnis|kontan|investor|investortrust|idx\s?channel|idxchannel|cnbc)[\w.]*\.{0,3}\s*$", re.I)


def strip_source_suffix(title, m):
    # Judul Google News diakhiri " - Nama Media", kadang dua kali atau terpotong ("- Bisnis.").
    title = re.sub(r"\s+[-–|]\s+[^-–|]{2,40}$", "", title).strip()
    for _ in range(3):
        new = MEDIA_SUFFIX.sub("", title).strip()
        if new == title:
            break
        title = new
    return title


def collect(m, now):
    """Kembalikan (artikel, status) untuk satu media."""
    status = {"via": None, "items": 0, "errors": []}
    items = []
    for url in m["direct"]:
        try:
            got = [x for x in parse_feed(fetch(url)) if host_ok(x["link"], m["domains"])]
            if got:
                items += got
                status["via"] = "rss"
        except Exception as e:  # noqa: BLE001
            status["errors"].append("rss: " + type(e).__name__ + " " + str(e)[:80])
    if not items:
        for url in m["google"]:
            try:
                got = parse_feed(fetch(url))
                for x in got:
                    if x["source_url"] and not host_ok(x["source_url"], m["domains"]):
                        continue
                    x["title"] = strip_source_suffix(x["title"], m)
                    x["desc"] = ""  # deskripsi Google News hanya tautan, bukan ringkasan
                    items.append(x)
                status["via"] = "google"
            except Exception as e:  # noqa: BLE001
                status["errors"].append("google: " + type(e).__name__ + " " + str(e)[:80])
            time.sleep(1.5)
    arts = []
    for x in items:
        if not x["title"] or not x["link"] or not x["time"]:
            continue
        if x["time"] > now + timedelta(minutes=10) or x["time"] < now - timedelta(hours=KEEP_H):
            continue
        arts.append({"media": m["name"], "title": x["title"], "url": x["link"],
                     "time": x["time"].isoformat(timespec="seconds"), "desc": short(x["desc"]) if x["desc"] else ""})
    status["items"] = len(arts)
    if not status["errors"]:
        del status["errors"]
    return arts, status


def keep_article(a):
    t = a["title"]
    if HARD_EXCLUDE.search(t):
        return False
    if SOFT_PRICE.search(t) and not CORP.search(t):
        return False
    return bool(RELEVANT.search(t + " " + a.get("desc", "")))


# Kode saham besar yang sering ditulis tanpa kurung. Kode lain dikenali setelah pernah muncul dalam kurung, mis. "Bumi Resources (BUMI)".
COMMON_TICKERS = set("""AADI ADRO AMMN AMRT ANTM ASII BBCA BBNI BBRI BBTN BMRI BRIS BREN BRPT BUMI BYAN CPIN CUAN DSSA EXCL GOTO ICBP
INCO INDF INKP INTP ISAT ITMG JPFA JSMR KLBF MAPI MDKA MEDC PGAS PGEO PTBA SMGR TLKM TOWR UNTR UNVR TPIA PANI DEWA RAJA""".split())
KNOWN_TICKERS = set(COMMON_TICKERS)


def tickers_of(title):
    found = re.findall(r"\(([A-Z]{4})\)", title)
    letters = [c for c in title if c.isalpha()]
    mostly_caps = letters and sum(c.isupper() for c in letters) / len(letters) > 0.6
    if not mostly_caps:
        found += [w for w in re.findall(r"\b[A-Z]{4}\b", title) if w in KNOWN_TICKERS and w not in TICKER_STOP]
        # Kata pertama berhuruf kapital empat huruf hampir selalu kode saham ("BWPT Tawarkan Obligasi").
        m0 = re.match(r"([A-Z]{4})\b", title)
        if m0 and m0.group(1) not in TICKER_STOP:
            found.insert(0, m0.group(1))
    out = []
    for t in found:
        if t not in out and t not in TICKER_STOP:
            out.append(t)
    return out


def tokens(title):
    words = re.findall(r"[a-z0-9]+", title.lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS and not w.isdigit()}


def event_keys(title):
    return {k for k, rx in EVENT_KEYS if re.search(rx, title, re.I)}


def category_of(text, has_ticker):
    rules = CAT_RULES if has_ticker else [r for r in CAT_RULES if r[0] != "Kinerja"] + [r for r in CAT_RULES if r[0] == "Kinerja"]
    for name, rx in rules:
        if rx.search(text):
            return name
    return "Kinerja" if has_ticker else "Makro"


def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def same_event(a, b):
    ta, tb = set(a["tickers"]), set(b["tickers"])
    sim = jaccard(a["tok"], b["tok"])
    if ta and tb:
        if not (ta & tb):
            return False
        ea, eb = a["ev"], b["ev"]
        if ea and eb:
            return bool(ea & eb)
        return sim >= 0.2
    shared = len(a["tok"] & b["tok"])
    # Jenis aksi sama (mis. delisting, dividen) dan beberapa kata kunci sama: kemungkinan besar peristiwa yang sama.
    if a["ev"] & b["ev"] and shared >= 3 and sim >= 0.2:
        return True
    if ta or tb:
        return sim >= 0.45
    return sim >= 0.4 and shared >= 3


def cluster(arts):
    arts = sorted(arts, key=lambda a: a["time"])
    groups = []
    for a in arts:
        a["tickers"] = tickers_of(a["title"])
        a["tok"] = tokens(a["title"])
        a["ev"] = event_keys(a["title"])
        best = None
        for g in groups:
            if any(same_event(a, b) for b in g):
                best = g
                break
        if best is None:
            groups.append([a])
        else:
            best.append(a)
    topics = []
    for g in groups:
        first = g[0]
        tick = []
        for a in g:
            for t in a["tickers"]:
                if t not in tick:
                    tick.append(t)
        desc_src = next((a for a in g if a["desc"]), None)
        text = " ".join(a["title"] for a in g)
        topics.append({
            "id": hashlib.sha1(first["url"].encode()).hexdigest()[:12],
            "title": first["title"],
            "category": category_of(text, bool(tick)),
            "tickers": tick[:6],
            "summary": desc_src["desc"] if desc_src else "",
            "summaryFrom": desc_src["media"] if desc_src else None,
            "sources": [{"media": a["media"], "time": a["time"], "url": a["url"], "title": a["title"]} for a in g],
        })
    return topics


def rank(topics, start, end):
    order = {c: i for i, c in enumerate(CATS)}
    rows = []
    for t in topics:
        src = [s for s in t["sources"] if start <= datetime.fromisoformat(s["time"]) <= end]
        if not src:
            continue
        rows.append((len({s["media"] for s in src}), len(src), order.get(t["category"], 9), max(s["time"] for s in src), t["id"]))
    # Jumlah media, jumlah artikel, kategori, lalu jam terbaru dulu.
    rows.sort(key=lambda r: (-r[0], -r[1], r[2], -datetime.fromisoformat(r[3]).timestamp()))
    return {r[4]: i + 1 for i, r in enumerate(rows[:TARGET])}


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def main():
    now = datetime.now(WIB).replace(microsecond=0)
    start, end = now - timedelta(hours=WINDOW_H), now

    store = {a["url"]: a for a in load(STORE, {"articles": []}).get("articles", [])}
    feeds = {}
    for m in MEDIA:
        arts, st = collect(m, now)
        feeds[m["name"]] = st
        for a in arts:
            if a["url"] in store:
                # Pertahankan jam pertama kali terlihat; perbarui judul/ringkasan jika berubah.
                store[a["url"]].update({k: a[k] for k in ("title", "desc") if a[k]})
            else:
                store[a["url"]] = a
        log(m["name"], st)

    cutoff = now - timedelta(hours=KEEP_H)
    articles = sorted((a for a in store.values() if datetime.fromisoformat(a["time"]) >= cutoff), key=lambda a: a["time"])
    for a in articles:
        KNOWN_TICKERS.update(re.findall(r"\(([A-Z]{4})\)", a["title"]))
    for a in articles:
        if a["media"] in ("Bisnis", "Kontan", "Investor.id", "IDX Channel", "CNBC Indonesia"):
            a["title"] = MEDIA_SUFFIX.sub("", a["title"]).strip()
    kept = [a for a in articles if keep_article(a) and datetime.fromisoformat(a["time"]) >= start]
    topics = cluster([dict(a) for a in kept])
    ranks = rank(topics, start, end)
    topics = [t for t in topics if t["id"] in ranks]
    topics.sort(key=lambda t: ranks[t["id"]])

    old = load(LIVE, {})
    prev_ranks, prev_at = old.get("prevRanks", {}), old.get("prevAt")
    if not prev_at or now - datetime.fromisoformat(prev_at) >= timedelta(minutes=PREV_EVERY_MIN):
        old_topics = old.get("topics", [])
        prev_ranks = {t["id"]: i + 1 for i, t in enumerate(old_topics)} if old_topics else {}
        prev_at = now.isoformat()

    payload = {
        "live": True,
        "mode": "rolling",
        "updated": now.isoformat(),
        "window": {"start": start.isoformat(), "end": end.isoformat(), "hours": WINDOW_H},
        "target": TARGET,
        "media": [{"name": m["name"], "abbr": m["abbr"]} for m in MEDIA],
        "feeds": feeds,
        "prevAt": prev_at,
        "prevRanks": prev_ranks,
        "topics": topics,
    }

    # Lewati tulis jika isi topik sama dan file belum lama diperbarui (hemat build GitHub Pages).
    same = json.dumps(old.get("topics"), sort_keys=True) == json.dumps(topics, sort_keys=True)
    fresh = old.get("updated") and now - datetime.fromisoformat(old["updated"]) < timedelta(minutes=REFRESH_MIN)
    if same and fresh:
        log("tidak ada perubahan; lewati")
        return

    os.makedirs(os.path.dirname(LIVE), exist_ok=True)
    with open(LIVE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump({"updated": now.isoformat(), "articles": articles}, f, ensure_ascii=False, indent=0)
    log("topik:", len(topics), "artikel 24 jam:", len(kept), "tersimpan:", len(articles))


if __name__ == "__main__":
    main()
