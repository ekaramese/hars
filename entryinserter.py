import sqlite3
import os
import re

DB = "db.sqlite"
SUBS_DIR = "/Users/erkankaramese/Downloads/ytyoutubedlp/subs"

time_re = re.compile(r"(\d{2}:\d{2}:\d{2})\s+(.*)")

conn = sqlite3.connect(DB)
cur = conn.cursor()

for fname in os.listdir(SUBS_DIR):
    if not fname.endswith(".timecodes.txt"):
        continue

    video_id = fname.replace(".timecodes.txt", "")
    path = os.path.join(SUBS_DIR, fname)

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            m = time_re.match(line)
            if not m:
                continue

            timecode, text = m.groups()
            h, m_, s = map(int, timecode.split(":"))
            seconds = h * 3600 + m_ * 60 + s

            cur.execute("""
                INSERT INTO entries (video_id, timecode, seconds, text)
                VALUES (?, ?, ?, ?)
            """, (video_id, timecode, seconds, text))

conn.commit()
conn.close()

print("✅ entries tablosu dolduruldu")
