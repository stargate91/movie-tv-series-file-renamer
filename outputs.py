import os

# ----- File operations messages -----

def proc_file_msg(file_path):
    print(f"Processing file: {file_path}")

def res_error_msg(file_path, e):
    print(f"[ERROR] Error getting resolution for {file_path}: {e}")

def rename_success_msg(file_path, new_filename):
    rel_path = os.path.relpath(file_path)
    print(f"Old name: {rel_path} → New name: {new_filename}")

def dry_rename_msg(file_path, new_filename):
    rel_path = os.path.relpath(file_path)
    print(f"[DRY RUN] Old name: {rel_path} → New name: {new_filename}")

# ----- Metadata handling messages -----

def unknown_type_msg(item, file_type):
    print(f"[ERROR] Unknown file type for {item}: {file_type}")

def sorted_success_msg(file, file_type):
    rel_path = os.path.relpath(file)
    print(f"{rel_path} added to {file_type} files")

def api_arg_error_msg():
    print("[ERROR] Unsupported API source for manual search")

def result_message(file_path, Response=None, total_results=None, data=None):
    rel_path = os.path.relpath(file_path)

    if Response == "False" or total_results == 0:
        print(f"No results found for {rel_path}")
    elif Response == "True" or total_results == 1:
        print(f"One result found for {rel_path}: {data}")
    elif total_results > 1:
        print(f"Multiple results found for {rel_path}: {data}")
    else:
        print(f"No data found for {rel_path}")

# ----- Movie metadata handling messages -----

def found_omdb_msg(data):
    print(f"Found result: {data['Title']} ({data['Year']})")

def no_manual_results_msg():
    print(f"No manual results found.")

def invalid_choice_msg():
    print("Invalid choice. No movie selected.")

def found_results_msg(file_data=None, file_type=None):
    if file_data and file_type:
        if file_type == "episode":
            file_type = "series"
        print(f"\nMultiple {file_type} results found for: {file_data['file_path']}")
    else:
        print("Found results:")

def display_res(results, file_type):
    for idx, result in enumerate(results, start=1):
        if file_type == "movie":
            print(f"{idx}. {result['title']} ({result['release_date']})")
        elif file_type == "episode":
            print(f"{idx}. {result['name']} ({result['first_air_date']})")

def manual_search_msg(file_data):
    print(f"\nAttempting manual search for: {file_data['file_path']}")

def skip_manual_search_msg(file_data):
    print(f"Skipping manual search for {file_data['file_path']}.")

def selected_res_msg(selected_result):
    print(f"User selected: {selected_result['title']} ({selected_result['release_date']})")

# ----- Series metadata handling messages -----

def pick_res(results, choice):
    selected_result = results[choice - 1]
    print(f"User selected: {selected_result['name']} ({selected_result['first_air_date']})")
    return selected_result

def manual_series_search_msg(file_data):
    print(f"Manual series search required for {file_data['file_path']}")

def manual_search_dir_msg(season_dir):
    print(f"\nAttempting manual search for: {season_dir}")

def manual_search_main_dir_msg(series_dir):
    print(f"\nAttempting manual search for: {series_dir}")

# ----- Episode metadata handling messages -----

def no_episode_msg(file_path):
    print(f"No episode found for {file_path}")

# ----- Main messages -----

def done_msg(unknown):
    print("\n Done.")
    print("\n Unexpected files:")
    for file_data in unknown:
        print(f"\n [MANUAL RENAMING REQ] {file_data['file_path']}")
