"""Simulate manual resolve for a movie and check enrichment."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.engine.manager import RenamerEngineV3

engine = RenamerEngineV3()
resolver = engine.resolver

# 1. Simulate search result (lean object)
search_result = {
    'tmdb_id': 27205, # Inception
    'title': 'Inception',
    'year': 2010,
    'media_type': 'movie',
    'poster_path': '/xQH69n9pY96039vN4D5U14N91V.jpg'
}

# 2. Call the NEW logic from ManualResolveDialog
print("=== Simulating Manual Resolve Enrichment ===")
media_item_id = resolver._store_result(search_result)
print(f"Enriched Media Item ID: {media_item_id}")

# 3. Check DB
conn = engine.db._get_connection()
row = conn.execute('SELECT director, "cast", overview FROM media_items WHERE id = ?', (media_item_id,)).fetchone()
print(f"Director: {row['director']}")
print(f"Cast: {row['cast'][:50]}...")
print(f"Overview: {row['overview'][:50]}...")
conn.close()
