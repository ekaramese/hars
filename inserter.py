import sqlite3
import csv

DB = "db.sqlite"
CSV_PATH = "/Users/erkankaramese/Downloads/ytyoutubedlp/videos.csv"

conn = sqlite3.connect(DB)
cur = conn.cursor()

with open(CSV_PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter=";")
    for row in reader:
        cur.execute("""
            INSERT OR IGNORE INTO videos (video_id, url, title)
            VALUES (?, ?, ?)
        """, (row["video_id"], row["url"], row["title"]))

conn.commit()
conn.close()

print("✅ videos.csv içe aktarıldı")
