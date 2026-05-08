import sqlite3
import os

db_path = r"e:\projects\python\movie-tv-series-file-renamer\data\renda.db"

if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit()

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("--- media_files status counts ---")
rows = cursor.execute("SELECT status, COUNT(*) as count FROM media_files GROUP BY status").fetchall()
for row in rows:
    print(f"{row['status']}: {row['count']}")

print("\n--- media_items type counts ---")
rows = cursor.execute("SELECT media_type, COUNT(*) as count FROM media_items GROUP BY media_type").fetchall()
for row in rows:
    print(f"{row['media_type']}: {row['count']}")

print("\n--- file_media_links count ---")
row = cursor.execute("SELECT COUNT(*) as count FROM file_media_links").fetchone()
print(f"Total links: {row['count']}")

print("\n--- library counts (query from FileRepository) ---")
movies = cursor.execute("""
    SELECT COUNT(DISTINCT m.id) FROM media_items m
    JOIN file_media_links l ON m.id = l.media_item_id
    JOIN media_files f ON l.file_id = f.id
    WHERE m.media_type = 'movie' AND f.status IN ('renamed', 'organized')
""").fetchone()[0]

series = cursor.execute("""
    SELECT COUNT(DISTINCT m.id) FROM media_items m
    JOIN file_media_links l ON m.id = l.media_item_id
    JOIN media_files f ON l.file_id = f.id
    WHERE m.media_type = 'tv' AND f.status IN ('renamed', 'organized')
""").fetchone()[0]
print(f"Movies in library: {movies}")
print(f"Series in library: {series}")

conn.close()
