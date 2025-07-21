import os

# ----- File operations outputs -----

def proc_file_msg(file_path, root_folder):
    rel_path = os.path.relpath(file_path, os.path.dirname(root_folder))
    print(f"[INFO] Processing file: {rel_path}")

def rename_success_msg(file_path, new_filename):
    rel_path = os.path.relpath(file_path)
    print(f"[RENAME] Old name: {rel_path} → New name: {new_filename}")

def dry_rename_msg(file_path, new_filename):
    rel_path = os.path.relpath(file_path)
    print(f"[DRY RUN] Old name: {rel_path} → New name: {new_filename}")

# ----- Handling outputs -----

def print_cancellation_summary(
    handled=None,
    skipped=None,
    source=None,
    mode=None,
    idx_or_processed=None,
    content=None,
    action=None
):
    print(f"\n[INFO] Manual {action} cancelled by user.") # {action}: [search, selection]

    if handled:
        print(f"\nMetadata stored for the following {content}:\n") # {content}: [movies, episodes]
        for file in handled:
            print(f"[SAVED] {file['file_path']}")
    else:
        print("\n[INFO] No metadata was stored.")

    if skipped:
        print(f"\nThe following {content} were deferred for later:\n")
        for skip in skipped:
            print(f"[SKIPPED] {skip['file_path']}")
    else:
        print("\n[INFO] No video file was skipped.")

    remaining = []

    if mode == 1:
        remaining = source[idx_or_processed:]
    elif mode == 2:
        for dir_key, eps in source.items():
            if dir_key not in idx_or_processed:
                remaining.extend(eps)

    if remaining:
        print(f"\nThe following {content} were not processed:\n")
        for leftover in remaining:
            print(f"[PENDING] {leftover['file_path']}")

    return handled, skipped, remaining

# ----- Handling inputs -----

def user_menu(files, folders, main_folders):
    menu_text = (
        "\nChoose how you want to apply the selected metadata for the files above:\n"
        f"  1. Apply to a single file only (e.g: {files[0]['file_path']})\n"
        f"  2. Apply to the entire folder (e.g: {folders})\n"
        f"  3. Apply to the main (parent) folder and all sub‑folders (e.g: {main_folders})\n"
        "  4. Cancel\n"
        "Enter your choice (1–4): "
    )
    while True:
        try:
            raw = input(menu_text).strip()
            if not raw:
                print("Please enter a number between 1 and 4.")
                continue

            choice = int(raw)
            if 1 <= choice <= 4:
                return choice
            else:
                print("Invalid choice. Only 1, 2, 3, or 4 are allowed.")
        except ValueError:
            print("Invalid input. Please type a number (1–4).")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled. Exiting menu.")
            return None

# ----- Main messages -----

def done_msg(unknown):
    print("\n Done.")
    print("\n Unexpected files:")
    for file_data in unknown:
        print(f"\n [INFO] {file_data['file_path']}")



