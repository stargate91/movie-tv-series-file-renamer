import os
import json
from datetime import datetime

LABELS = {
    "start":           ("🚀 ", ""),
    "live_mode":       ("⚠️ ", ""),
    "dry_run":         ("📝 ", ""),
    "name":            ("🎥 ", ""),
    "version":         ("📦 ", ""),
    "config":          ("⚙️ ", ""),
    "dir":             ("📁 ", ""),
    "up":              ("⚡ ", ""),
    "summary":         ("📋 ", ""),
    "skipped":         ("⏭️ ", ""),
    "unprocessed":     ("⏳ ", ""),
    "no_se_ep":        ("⚠️ ", ""),
    "unexpected_ep":   ("❓ ", ""),
    "renamed":         ("✅ ", ""),
    "done":            ("🎉 ", "")
}

def get_label(name, use_emojis):
    pair = LABELS.get(name, ("", ""))
    return pair[0] if use_emojis else pair[1]

def group_by_folders(episodes):
    folders = {}
    main_folders = {}

    for file_data in episodes:
        file_path = file_data['file_path']
        directory = os.path.dirname(file_path)
        main_directory = os.path.dirname(directory)

        if directory not in folders:
            folders[directory] = []
        folders[directory].append(file_data)

        if main_directory not in main_folders:
            main_folders[main_directory] = []
            
        if file_data not in main_folders[main_directory]:
            main_folders[main_directory].append(file_data)

    return folders, main_folders

def build_entry(item, selected):
    entry = {
        'file_path': item['file_path'],
        'file_type': item['file_type'],
        'extras': item['extras'],
        'details': selected
    }

    for key in ('season_file', 'episode_file', 'season_folder', 'episode_folder'):
        if key in item:
            entry[key] = item[key]

    return entry

def get_api_func(api_client, source):
    return {
        'tmdb': api_client.get_from_tmdb_movie,
        'tmdb_tv': api_client.get_from_tmdb_tv
    }.get(source)

def has_results(result):
    return result.get("total_results", 0) > 0 if result else False

def extract_results(result):
    return result.get('results', []) if result else []

def search_api(api_client, source, title, year):
    api_func = get_api_func(api_client, source)
    result = api_func(title, year)
    results = extract_results(result)
    return result, results

def save_skipped_to_file(skipped, data_dir="data", filename="skipped_latest.json"):
    os.makedirs(data_dir, exist_ok=True)

    file_path = os.path.join(data_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(skipped, f, ensure_ascii=False, indent=2)

    print(f"\n[SAVED] Skipped list saved to: {file_path}")

def load_skipped_menu(path="data/skipped_latest.json", max_examples=2):
    if not os.path.exists(path):
        print("[INFO] No skipped file found.")
        return None

    with open(path, "r", encoding="utf-8") as f:
        skipped_files = json.load(f)

    print(f"Found skipped file: {os.path.basename(path)} ({len(skipped_files)} entries)")

    print("Examples:")
    for entry in skipped_files[:max_examples]:
        print(f"- {entry.get('file_path', 'Unknown file')}")

    print("""
[1] Resume from this
[2] Ignore and start fresh
[0] Exit
    """)

    while True:
        choice = input("Select an option: ").strip()
        if choice == "1":
            return skipped_files
        elif choice == "2":
            print("[INFO] Ignoring the saved skipped files.")
            return
        elif choice == "0":
            print("Exiting.")
            exit(0)
        else:
            print("Invalid choice. Please enter 1, 2, or 0.")

def save_rename_history_to_file(rename_history, data_dir="rename_history"):
    os.makedirs(data_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    history_filename = f"rename_history_{timestamp}.json"
    file_path = os.path.join(data_dir, history_filename)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(rename_history, f, ensure_ascii=False, indent=2)

    print(f"\n[SAVED] Rename history saved to: {file_path}")
