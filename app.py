import sqlite3
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
import re
import unicodedata
from urllib.parse import urlparse, parse_qs

def extract_video_id(input_str: str) -> str | None:
    """
    URL veya direkt video_id kabul eder
    """
    input_str = input_str.strip()

    # Direkt video_id (11 karakter)
    if len(input_str) == 11 and "/" not in input_str:
        return input_str

    # YouTube URL
    try:
        parsed = urlparse(input_str)
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]
    except Exception:
        pass

    return None



def normalize_text(text: str) -> str:
    """
    Unicode NFKD normalize + lowercase + diacritics temizleme
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()
def normalize_fts_query(q: str) -> str:
    q = normalize_text(q)
    q = re.sub(r'[^\w\s]', ' ', q)
    q = re.sub(r'\s+', ' ', q)
    return " ".join(f"{w}*" for w in q.split())

def highlight_ci(text, word):
    norm_word = normalize_text(word)

    def repl(match):
        return f"<mark>{match.group(0)}</mark>"

    pattern = re.compile(
        re.escape(norm_word),
        re.IGNORECASE
    )

    return pattern.sub(
        repl,
        normalize_text(text)
    )
app = FastAPI()
DB_PATH = "db.sqlite"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------------------
# ANA SAYFA
# --------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html", encoding="utf-8") as f:
        return f.read()


# --------------------------------------------------
# TIMECODE ARAMASI (FTS)
# --------------------------------------------------
@app.get("/search/timecodes")
def search_timecodes(q: str = Query(..., min_length=1)):
    db = get_db()

    fts_query = normalize_fts_query(q)

    sql = """
    SELECT
      e.video_id,
      e.timecode,
      e.seconds,
      highlight(entries, 3, '<mark>', '</mark>') AS text,
      v.title,
      v.url
    FROM entries e
    JOIN videos v ON v.video_id = e.video_id
    WHERE entries MATCH ?
    ORDER BY v.title, e.seconds
    """

    rows = db.execute(sql, (fts_query,)).fetchall()

    results = {}
    for r in rows:
        vid = r["video_id"]

        # highlight case-insensitive güvenli
        text = highlight_ci(r["text"], q)

        results.setdefault(vid, {
            "title": r["title"],
            "url": r["url"],
            "items": []
        })

        results[vid]["items"].append({
            "timecode": r["timecode"],
            "seconds": r["seconds"],
            "text": text
        })

    return results

@app.get("/search/title")
def search_title(q: str = Query(..., min_length=2)):
    db = get_db()

    q_norm = normalize_text(q)

    rows = db.execute("""
        SELECT
          video_id,
          title,
          url,
          transcript
        FROM videos
    """).fetchall()

    results = []
    for r in rows:
        title_norm = normalize_text(r["title"])
        if q_norm in title_norm:
            results.append({
                "video_id": r["video_id"],
                "title": r["title"],      # orijinal
                "url": r["url"],
                "transcript": r["transcript"] or ""
            })

    return results
# --------------------------------------------------
# METİN (TRANSCRIPT) ARAMASI
# --------------------------------------------------
@app.get("/search/text")
def search_text(q: str = Query(..., min_length=1)):
    db = get_db()
    q = q.strip()
    q_norm = normalize_text(q)
    q_len = len(q_norm)
   

    sql = """
    WITH RECURSIVE matches AS (
      SELECT
        video_id,
        title,
        url,
        transcript,
        lower(transcript) AS t_lower,
        instr(lower(transcript), lower(?)) AS pos
      FROM videos
      WHERE instr(lower(transcript), lower(?)) > 0

      UNION ALL

      SELECT
        video_id,
        title,
        url,
        transcript,
        t_lower,
        pos + ? +
          instr(
            substr(t_lower, pos + ?),
            lower(?)
          ) AS pos
      FROM matches
      WHERE instr(
        substr(t_lower, pos + ?),
        lower(?)
      ) > 0
    )
    SELECT
      video_id,
      title,
      url,
      substr(
        transcript,
        max(1, pos - 100),
        200
      ) AS snippet
    FROM matches
    """

    rows = db.execute(
        sql,
        (q_norm, q_norm, q_len, q_len, q_norm, q_len, q_norm)
    ).fetchall()

    results = {}
    for r in rows:
        vid = r["video_id"]
        snippet = highlight_ci(r["snippet"], q)

        results.setdefault(vid, {
            "title": r["title"],
            "url": r["url"],
            "snippets": []
        })

        results[vid]["snippets"].append(snippet)

    return results

@app.get("/video/timecodes")
def get_video_timecodes(q: str = Query(..., min_length=1)):
    db = get_db()

    video_id = extract_video_id(q)
    if not video_id:
        return {"error": "Geçersiz video URL veya ID"}

    video = db.execute(
        "SELECT title, url FROM videos WHERE video_id = ?",
        (video_id,)
    ).fetchone()

    if not video:
        return {"error": "Video bulunamadı"}

    rows = db.execute("""
        SELECT
          timecode,
          seconds,
          text
        FROM entries
        WHERE video_id = ?
        ORDER BY seconds
    """, (video_id,)).fetchall()

    return {
        "video_id": video_id,
        "title": video["title"],
        "url": video["url"],
        "items": [
            {
                "timecode": r["timecode"],
                "seconds": r["seconds"],
                "text": r["text"]   # 🔥 AYNEN, SNIPPET YOK
            }
            for r in rows
        ]
    }




