import sqlite3

DB = "db.sqlite"

conn = sqlite3.connect(DB)
cur = conn.cursor()

# temizle (tekrar çalıştırılabilir)
cur.execute("DELETE FROM transcript_entries")

rows = cur.execute("""
    SELECT video_id, transcript
    FROM videos
    WHERE transcript IS NOT NULL
""").fetchall()

for video_id, transcript in rows:
    lines = [l.strip() for l in transcript.splitlines() if l.strip()]

    for i, line in enumerate(lines):
        cur.execute("""
            INSERT INTO transcript_entries (video_id, line_no, text)
            VALUES (?, ?, ?)
        """, (video_id, i, line))

conn.commit()
conn.close()

print("✅ transcript_entries dolduruldu")
