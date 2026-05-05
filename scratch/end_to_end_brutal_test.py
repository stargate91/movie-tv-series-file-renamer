import os
import sys
import shutil
import time

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from core.engine.manager import RenamerEngineV3
from core.db.database import LibraryDB

def run_e2e_test():
    print("=== MOVIE RENAMER V3 END-TO-END BRUTAL TEST (V2) ===")
    
    source_dir = os.path.join(project_root, "test_e2e_source")
    target_dir = os.path.join(project_root, "test_e2e_target")
    # We will use the default DB path for now, but wipe it first
    
    if os.path.exists(target_dir): shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)

    engine = RenamerEngineV3()
    engine.db.wipe_discovery_data()
    
    s = engine.config.settings
    s.default_scan_path = source_dir
    s.base_target_path = target_dir
    s.move_files = True
    s.auto_organize_by_type = True
    
    print(f"\n[1] SCANNING...")
    engine.scanner.scan_directory(source_dir)
    
    print(f"[2] COLLECTING...")
    engine.collector.collect_all()
    
    print(f"[3] MOCKING MATCHES (to avoid API wait)...")
    vids = engine.db.files.get_files_by_category('video')
    for v in vids:
        mid = engine.db.media.upsert_media_item(tmdb_id=500+v['id'], title="E2E Movie", year=2024, media_type="movie")
        engine.db.media.link_file_to_media(v['id'], mid)
        engine.db.files.update_file(v['id'], match_status='MATCHED', resolution="1080p")
    
    print(f"[4] PLANNING...")
    plan = engine.get_rename_plan()
    for p in plan:
        print(f"  Plan: {os.path.basename(p['original_path'])} -> {os.path.basename(p['proposed_path'] or '')}")

    print(f"[5] EXECUTING...")
    results = engine.apply_plan(plan)
    print(f"  Results: {results['success']} success, {results['failed']} failed.")

    print(f"\n[6] DISK VERIFICATION...")
    for root, dirs, files in os.walk(target_dir):
        for f in files:
            print(f"  [TARGET] {os.path.relpath(os.path.join(root, f), target_dir)}")

    print("\n=== E2E TEST V2 COMPLETE ===")

if __name__ == "__main__":
    run_e2e_test()
