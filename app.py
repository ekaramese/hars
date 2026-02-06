from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import re
import unicodedata
from urllib.parse import urlparse, parse_qs

from db import fetch_all


# --------------------------------------------------
# YARDIMCI FONKSİYONLAR
# --------------------------------------------------

def extract_video_id(input_str: str) -> str | None:
    input_str = input_str.strip()

    if len(input_str) == 11 and "/" not in input_str:
        return input_str

    try:
        parsed = urlparse(input_str)
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]
    except Exception:
        pass

    return None


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def normalize_fts_query(q: str) -> str:
    q = normalize_text(q)
    q = re.sub(r"[^\w\s]", " ", q)
    q = re.sub(r"\s+", " ", q)
    return " ".join(f"{w}*" for w in q.split())


def highlight_ci(text: str, word: str) -> str:
    norm_word = normalize_text(word)

    def repl(match):
        return f"<mark>{match.group(0)}</mark>"

    pattern = re.compile(re.escape(norm_word), re.IGNORECASE)
    return pattern.sub(repl, normalize_text(text))


# --------------------------------------------------
# FASTAPI
# --------------------------------------------------

app = FastAPI()


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
    fts_query = normalize_fts_query(q)

    sql = """
    SELECT
      e.video_id,
      e.timecode,
      e.seconds,
      e.text,
      v.title,
      v.url
    FROM entries e
    JOIN videos v ON v.video_id = e.video_id
    WHERE entries MATCH ?
    ORDER BY v.title, e.seconds
    """

    rows = fetch_all(sql, (fts_query,))

    results = {}
    for r in rows:
        vid = r["video_id"]
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


# --------------------------------------------------
# BAŞLIKTA ARAMA
# --------------------------------------------------

@app.get("/search/title")
def search_title(q: str = Query(..., min_length=2)):
    q_norm = normalize_text(q)

    sql = """
    SELECT video_id, title, url, transcript
    FROM videos
    """

    rows = fetch_all(sql)

    results = []
    for r in rows:
        if q_norm in normalize_text(r["title"]):
            results.append({
                "video_id": r["video_id"],
                "title": r["title"],
                "url": r["url"],
                "transcript": r["transcript"] or ""
            })

    return results


# --------------------------------------------------
# METİN (TRANSCRIPT) ARAMASI
# --------------------------------------------------

@app.get("/search/text")
def search_text(q: str = Query(..., min_length=1)):
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

    rows = fetch_all(
        sql,
        (q_norm, q_norm, q_len, q_len, q_norm, q_len, q_norm)
    )

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


# --------------------------------------------------
# TEK VİDEO – TÜM TIMECODE'LAR
# --------------------------------------------------

@app.get("/video/timecodes")
def get_video_timecodes(q: str = Query(..., min_length=1)):
    video_id = extract_video_id(q)
    if not video_id:
        return {"error": "Geçersiz video URL veya ID"}

    video = fetch_all(
        "SELECT title, url FROM videos WHERE video_id = ?",
        (video_id,)
    )

    if not video:
        return {"error": "Video bulunamadı"}

    rows = fetch_all(
        """
        SELECT timecode, seconds, text
        FROM entries
        WHERE video_id = ?
        ORDER BY seconds
        """,
        (video_id,)
    )

    return {
        "video_id": video_id,
        "title": video[0]["title"],
        "url": video[0]["url"],
        "items": [
            {
                "timecode": r["timecode"],
                "seconds": r["seconds"],
                "text": r["text"]
            }
            for r in rows
        ]
    }
