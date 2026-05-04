"""Fix: delete stale API cache entries that don't have credits/external_ids."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.db.database import LibraryDB
import json

db = LibraryDB()
conn = db._get_connection()

# Find all tv-detail cache entries and check if they have credits
rows = conn.execute("SELECT cache_key, response_json FROM api_cache WHERE cache_key LIKE 'tv-detail-%'").fetchall()
stale = []
for r in rows:
    try:
        data = json.loads(r['response_json'])
        if 'credits' not in data:
            stale.append(r['cache_key'])
    except:
        stale.append(r['cache_key'])

print(f"Found {len(stale)} stale TV detail cache entries (missing credits)")
for key in stale[:10]:
    print(f"  Deleting: {key}")

if stale:
    for key in stale:
        conn.execute("DELETE FROM api_cache WHERE cache_key = ?", (key,))
    conn.commit()
    print(f"Deleted {len(stale)} stale entries.")

# Also check movie-detail entries
rows = conn.execute("SELECT cache_key, response_json FROM api_cache WHERE cache_key LIKE 'movie-detail-%'").fetchall()
stale_movies = []
for r in rows:
    try:
        data = json.loads(r['response_json'])
        if 'credits' not in data:
            stale_movies.append(r['cache_key'])
    except:
        stale_movies.append(r['cache_key'])

if stale_movies:
    for key in stale_movies:
        conn.execute("DELETE FROM api_cache WHERE cache_key = ?", (key,))
    conn.commit()
    print(f"Also deleted {len(stale_movies)} stale movie-detail entries.")

conn.close()
print("Done! Re-scan to repopulate with full credits data.")
