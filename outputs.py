import os

# ----- File operations messages -----

def proc_file_msg(file_path, root_folder):
    rel_path = os.path.relpath(file_path, os.path.dirname(root_folder))
    print(f"Processing file: {rel_path}")

def rename_success_msg(file_path, new_filename):
    rel_path = os.path.relpath(file_path)
    print(f"[RENAME] Old name: {rel_path} → New name: {new_filename}")

def dry_rename_msg(file_path, new_filename):
    rel_path = os.path.relpath(file_path)
    print(f"[DRY RUN] Old name: {rel_path} → New name: {new_filename}")

# ----- Main messages -----

def done_msg(unknown):
    print("\n Done.")
    print("\n Unexpected files:")
    for file_data in unknown:
        print(f"\n [MANUAL RENAMING REQ] {file_data['file_path']}")
