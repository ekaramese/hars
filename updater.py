import sqlite3
import os

DB = "db.sqlite"
SUBS_DIR = "/Users/erkankaramese/Downloads/ytyoutubedlp/subs"

conn = sqlite3.connect(DB)
cur = conn.cursor()

for fname in os.listdir(SUBS_DIR):
    path = os.path.join(SUBS_DIR, fname)

    if fname.endswith(".tr.txt"):
        video_id = fname.replace(".tr.txt", "")
        with open(path, encoding="utf-8") as f:
            transcript = f.read().strip()

        cur.execute("""
            UPDATE videos
            SET transcript = ?
            WHERE video_id = ? AND transcript IS NULL
        """, (transcript, video_id))

    elif fname.endswith(".tr.vtt"):
        video_id = fname.replace(".tr.vtt", "")
        with open(path, encoding="utf-8", errors="ignore") as f:
            captions = f.read().strip()

        cur.execute("""
            UPDATE videos
            SET captions = ?
            WHERE video_id = ? AND captions IS NULL
        """, (captions, video_id))

conn.commit()
conn.close()

print("✅ transcript ve captions dolduruldu")
