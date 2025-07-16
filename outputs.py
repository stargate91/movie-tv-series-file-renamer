import os

def processing_file_message(file_path):
    print(f"Processing file: {file_path}")

def getting_resolution_error_message(file_path, e):
    print(f"[ERROR] Error getting resolution for {file_path}: {e}")

def rename_success_message(file_path, new_filename):
    rel_path = os.path.relpath(file_path)
    print(f"Old name: {rel_path} → New name: {new_filename}")

def dry_rename_success_message(file_path, new_filename):
    rel_path = os.path.relpath(file_path)
    print(f"[DRY RUN] Old name: {rel_path} → New name: {new_filename}")

def unknown_file_type_message(item, file_type):
    print(f"[ERROR] Unknown file type for {item}: {file_type}")

def episode_files_success_message(file):
    rel_path = os.path.relpath(file)
    print(f"{rel_path} added to episode files")

def movie_files_success_message(file):
    rel_path = os.path.relpath(file)
    print(f"{rel_path} added to movie files")

def unknown_files_success_message(file):
    rel_path = os.path.relpath(file)
    print(f"{rel_path} added to unknown type files")

def incorrect_api_arguments_message():
    print("[ERROR] Incorrect arguments for API source")

def no_result_message(file_path):
    rel_path = os.path.relpath(file_path)
    print(f"No results found for {rel_path}")

def one_result_message(file_path, data):
    rel_path = os.path.relpath(file_path)
    print(f"One result found for {rel_path}: {data}")

def multiple_results_tmdb_message(file_path, data):
    rel_path = os.path.relpath(file_path)
    print(f"Multiple results found for {rel_path}: {data}")

def no_data_found_message(file_path):
    rel_path = os.path.relpath(file_path)
    print(f"No data found for {rel_path}")