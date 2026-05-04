from core.db.database import LibraryDB
import os

db = LibraryDB()
raw_videos = db.get_files_by_category('video', 'extra', 'subtitle', 'audio', 'image', 'metadata', 'unknown')
print(f"Total files found by category: {len(raw_videos)}")

if raw_videos:
    print(f"Sample file: {raw_videos[0]['file_name']} | Status: {raw_videos[0].get('status')} | Match Status: {raw_videos[0].get('match_status')}")
    
    statuses = set(v.get('status') for v in raw_videos)
    print(f"Unique 'status' values: {statuses}")
    
    match_statuses = set(v.get('match_status') for v in raw_videos)
    print(f"Unique 'match_status' values: {match_statuses}")

    filtered = [v for v in raw_videos if v.get('status') not in ('renamed', 'deleted')]
    print(f"Files after filtering: {len(filtered)}")
else:
    # Check all files to see if anything is in there
    all_files = db.get_all_files()
    print(f"Total files in DB (all categories): {len(all_files)}")
    if all_files:
        print(f"Categories found: {set(v.get('category') for v in all_files)}")
