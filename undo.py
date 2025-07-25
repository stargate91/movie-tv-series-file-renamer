import os
import json
from helper import get_label


def find_latest_history_file(history_dir):
    try:
        files = [
            f for f in os.listdir(history_dir)
            if f.startswith("rename_history_") and f.endswith(".json")
        ]
        if not files:
            return None

        files.sort(reverse=True)
        latest_file = files[0]
        return os.path.join(history_dir, latest_file)
    except Exception as e:
        print(f"[ERROR] Could not search for history files: {e}")
        return None


def undo_rename(history_file=None, history_dir="rename_history", use_emojis=False):

    if not history_file:
        history_file = find_latest_history_file(history_dir)

    if not history_file or not os.path.exists(history_file):
        print(f"\n[ERROR] No valid rename history file found at: {history_file}")
        return

    print(f"\n{get_label('paper', use_emojis)}Undoing renames using history file:\n{history_file}\n")

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history_data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to load history file: {e}")
        return

    if not isinstance(history_data, list):
        print("[ERROR] Invalid history format. Expected a list of rename records.")
        return

    success_count = 0
    fail_count = 0

    for record in history_data:
        old_path = record.get("old_path")
        new_path = record.get("new_path")

        if not old_path or not new_path:
            print(f"[WARN] Skipping invalid entry: {record}")
            continue

        if not os.path.exists(new_path):
            print(f"[WARN] File not found, skipping: {new_path}")
            fail_count += 1
            continue

        try:
            os.renames(new_path, old_path)
            print(f"[UNDO] {new_path} -> {old_path}")
            success_count += 1
        except Exception as e:
            print(f"[ERROR] Failed to undo rename for {new_path}: {e}")
            fail_count += 1

    print(f"\n{get_label('renamed', use_emojis)}Undo complete!")
    print(f"Renames restored: {success_count}")
    if fail_count:
        print(f"Failures: {fail_count}")
