import os
import sys
import logging
import json

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from core.engine.manager import RenamerEngineV3

def run_brutal_test():
    print("=== MOVIE RENAMER V3 BRUTAL STRESS TEST ===")
    
    engine = RenamerEngineV3()
    test_path = os.path.join(project_root, "test_wormy_library")
    engine.db.wipe_discovery_data()
    
    print(f"\n[1/3] Scanning & Collecting...")
    engine.scanner.scan_directory(test_path)
    engine.collector.collect_all()
    
    files = engine.db.files.get_all_files()
    
    print("\n--- A. The Nested Nightmare ---")
    matrix = [f for f in files if "Matrix.1999.mkv" in f['file_name']]
    if matrix:
        print(f"File found at: {matrix[0]['current_path']}")
        print(f"Depth: {matrix[0]['current_path'].count(os.sep) - test_path.count(os.sep)} levels deep")
    
    print("\n--- B. The Multi-Episode Soup ---")
    soup = [f for f in files if "Soup" in f['current_path']][0]
    print(f"File: {soup['file_name']}")
    print(f"Parsed S: {soup['fn_season']} E: {soup['fn_episode']}")
    
    print("\n--- C. The Junk Path ---")
    junk = [f for f in files if "Junk" in f['current_path']][0]
    print(f"Original Path: {junk['current_path']}")
    
    # 2. Mock some matches for renaming tests
    print("\n[2/3] Mocking matches for Collision Resolution...")
    
    # Gladiator collision
    glad1 = [f for f in files if "Gladiator.2000.4K" in f['file_name']][0]
    glad2 = [f for f in files if "Gladiator.2000.Director" in f['file_name']][0]
    
    m_id = engine.db.media.upsert_media_item(tmdb_id=99, title="Gladiator", year=2000, media_type="movie")
    for f in [glad1, glad2]:
        engine.db.media.link_file_to_media(f['id'], m_id)
        engine.db.files.update_file(f['id'], match_status='MATCHED', resolution="4K")

    # 3. Rename Plan
    print("\n[3/3] Generating Rename Plan...")
    plan = engine.get_rename_plan()
    
    for p in plan:
        status = p['status']
        orig = os.path.basename(p['original_path'])
        new = os.path.basename(p['proposed_path'] or 'N/A')
        
        # Highlight collisions
        prefix = "!! " if status == 'collision' else "   "
        print(f"{prefix}{status:15} | {orig:45} -> {new}")

    print("\n=== BRUTAL TEST COMPLETE ===")

if __name__ == "__main__":
    run_brutal_test()
