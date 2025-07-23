from helper import group_by_folders, build_entry, get_label
import os

# ----- File operations outputs -----

def rename_starts_msg(live_run, use_emojis):
    print(f"\n{get_label('start', use_emojis)}Starting file renaming process...")
    if live_run:
        print(f"{get_label('live_mode', use_emojis)}Live mode enabled - files **will be renamed**.\n")
    else:
        print(f"{get_label('dry_run', use_emojis)}Dry run mode - no changes will be made, just simulating.\n")
    print("=" * 35 + "\n")
 
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
        print(f"\n[INFO] Metadata stored for the following {content}:\n") # {content}: [movies, episodes]
        for file in handled:
            print(f"[SAVED] {file['file_path']}")
    else:
        print("\n[INFO] No metadata was stored.")

    if skipped:
        print(f"\n[INFO] The following {content} were deferred for later:\n")
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
        print(f"\n[INFO] The following {content} were not processed:\n")
        for leftover in remaining:
            print(f"[PENDING] {leftover['file_path']}")

    return handled, skipped, remaining

def display_res(
    options,
    file=None,
    folder=None,
    content=None
):

    if file:
        print(f"\n Choose a result or an action for this {content}: {file['file_path']}") # {content}: [movie, episode]
    elif folder:
        print(f"\n Choose a result or an action for this folder: {folder}")
    else:
        print("\nFound results:")

    for i, opt in enumerate(options, 1):
        print(f"{i}. {opt.get('title') or opt.get('Title') or opt.get('name')} ({opt.get('Year') or opt.get('release_date') or opt.get('first_air_date')})")

# ----- Handling inputs -----

def user_menu(files, folders, main_folders):
    menu_text = (
        "Choose how you want to apply the selected metadata for the files above:\n"
        f"  [1] Apply to a single file only (e.g: {files[0]['file_path']})\n"
        f"  [2] Apply to the entire folder (e.g: {folders})\n"
        f"  [3] Apply to the main (parent) folder and all sub‑folders (e.g: {main_folders})\n"
        "  [4] Cancel\n"
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

def show_list_and_get_user_choice(
    vid_files,
    current_api=None,
    content=None,
    action=None,
    res_quantity=None
):

    if not vid_files:
        print(f"\n[INFO] There are no {content} with {res_quantity}. Continue with the next task.") # {res_quantity}: [no match, multiple matches]
        return [], [], [], []

    print(f"\n===== {content.upper()} WITH {res_quantity.upper()} =====\n") # {content}: [movies, episodes]

    if current_api:
        print(f"[INFO] Current API: {current_api.upper()}\n")

    for idx, vid in enumerate(vid_files, 1):
        print(f"{idx}. {vid['file_path']}")

    print(f"\nManual {action} required for these {content}.\n") # {action}: [search, selection]
    
    if content == "movies":
        print(f"Options:\n1: Manual {action} for all\n2: Cancel")
        choice = int(input("Choose an option (1/2): "))
        while choice not in {1, 2}:
            print("Invalid input. Please enter 1 or 2")
            choice = int(input("Choose an option (1/2): "))

        if choice == 2:
            handled, skipped, remaining = print_cancellation_summary(source=vid_files, mode=1, idx_or_processed=0, content="movies", action=action)
            return handled, skipped, remaining, choice
        else:
            return [], [], [], []

    if content == "episodes":
        folders, main_folders = group_by_folders(vid_files) 
        
        first_folder_key = next(iter(folders))
        first_main_folder_key = next(iter(main_folders))

        action_choice = user_menu(vid_files, first_folder_key, first_main_folder_key)
        return folders, main_folders, action_choice, []

def prompt_search_decision(file, idx, handled, skipped, source, content, action):
    valid_choices = {'y', 'n', 's', 'c'}
    while True:
        print(f"\n{file['file_path']}")
        choice = input(f"Do you want to search manually? (y/n/c): ").strip().lower()
        if choice in valid_choices:
            if choice == 'c':
                handled, skipped, remaining = print_cancellation_summary(
                    handled=handled,
                    skipped=skipped,
                    source=source,
                    mode=1,
                    idx_or_processed=idx,
                    content=content,
                    action=action
                )
                return 'c', handled, skipped, remaining
            elif choice == 'n' or choice == 's':
                skipped.append(file)
            return choice, handled, skipped, []
        print("Invalid input. Please enter y, n, or c.")

def get_title_and_year_input(re=None, mo=None, ep=None, file=None, folder=None, current_api=None):
    if file:
        print(f"\n Search for: {file['file_path']}")

    if folder:
        print(f"\n Search for: {folder}")

    if current_api:
        print(f"[API: {current_api.upper()}]")

    if mo:
        prompt_title = "Retry title" if re else "Title"
        title = input(f"{prompt_title}: ").strip()
        year = input("Year (optional): ").strip() or 'unknown'

    elif ep:
        prompt_title = "Retry title" if re else "Series title"
        title = input(f"{prompt_title}: ").strip()
        year = input("Series first air year (optional): ").strip() or 'unknown'

    return title, year

def switch_api(current):
    available = ['omdb', 'tmdb']
    others = [a for a in available if a != current]
    
    while True:
        print(f"\nAvailable APIs: {', '.join(others)} (current: {current})")
        new_api = input("Switch to: ").strip().lower()

        if new_api == current:
            print(f"You are already using '{current}'. Choose a different API.")
            continue

        if new_api in others:
            print(f"[INFO] Switched to API: {new_api.upper()}")
            return new_api

        print("Invalid API. Please choose from the available options or press Enter to cancel.")
        cancel = input("Try again? (y/n): ").strip().lower()
        if cancel != 'y':
            print("Staying on current API.")
            return current

def action_menu(no=None, mult_api=None):
    if no:
        print("No results found.")
        print("Options:")
    print("Select result by number, or:")
    print("[r] Retry search")
    if mult_api:
        print("[a] Try another API")
    print("[s] Skip")
    print("[c] Cancel")

def process_number_choice(sel, options, file, handled):
    if sel.isdigit():
        num = int(sel)
        if 1 <= num <= len(options):
            selected = options[num - 1]
            handled.append(build_entry(file, selected))
            return True
        else:
            print("Invalid number.")
    return False

# ----- Main messages -----
def start_msg(source, folder_path, use_emojis):
    print("===================================")
    print(f"{get_label('name', use_emojis)}MovieRenamer")
    print(f"{get_label('version', use_emojis)}Version: 1.1.0")
    print(f"{get_label('config', use_emojis)}Using configuration: {source}")
    print(f"{get_label('dir', use_emojis)}Working directory: {folder_path}")
    print("===================================\n")
    print("This tool helps you rename your video files using metadata from TMDb or OMDb.")
    print("Make sure your files are organized properly!\n")

    print(f"{get_label('up', use_emojis)}Starting up...\n")

def done_msg(unknown_files, skipped, remaining, no_episode_detail, u_episodes, renamed_files, use_emojis, interactive):
    print("\n" + "="*30)
    print(f"{get_label('summary', use_emojis)}CLEANUP SUMMARY")
    print("="*30)

    if interactive:
        if skipped:
            print(f"\n{get_label('skipped', use_emojis)}Skipped Files:")
            for file_data in skipped:
                print(f"   • {file_data['file_path']}")
        else:
            print(f"\n{get_label('skipped', use_emojis)}No files were skipped.")

    if unknown_files:
        print(f"\n{get_label('unexpected_ep', use_emojis)}Unexpected Files:")
        for file_data in unknown_files:
            print(f"   • {file_data['file_path']}")
    else:
        print(f"\n{get_label('unexpected_ep', use_emojis)}No unexpected files were detected.")

    if remaining:
        print(f"\n{get_label('unprocessed', use_emojis)}Unprocessed Files:")
        for file_data in remaining:
            print(f"   • {file_data['file_path']}")
    else:
        print(f"\n{get_label('unprocessed', use_emojis)}All files were processed.")

    if no_episode_detail:
        print(f"\n{get_label('no_se_ep', use_emojis)}Episodes Missing Season/Episode Info:")
        for file_data in no_episode_detail:
            print(f"   • {file_data['file_path']}")
    else:
        print(f"\n{get_label('no_se_ep', use_emojis)}All episodes have season and episode numbers.")

    if u_episodes:
        print(f"\n{get_label('unexpected_ep', use_emojis)}Episodes With Unexpected Format (e.g. S01E0102, S01E01-02, 1x0102):")
        for file_data in u_episodes:
            print(f"   • {file_data['file_path']}")
    else:
        print(f"\n{get_label('unexpected_ep', use_emojis)}No unexpected episode formats detected.")

    if renamed_files:
        print(f"\n{get_label('renamed', use_emojis)}Files renamed:")
        for file_data in renamed_files:
            print(f"   • {file_data['file_path']}")
        print(f"\n {len(renamed_files)} file(s) renamed successfully.")
    else:
        print(f"\n{get_label('renamed', use_emojis)}No files were renamed - either a dry run or nothing matched.")

    print(f"\n{get_label('done', use_emojis)}Done!")
    print("Your video library is now cleaner and better organized.")
    print("If you spot any issues or have feature ideas, feel free to open an issue on GitHub!")
    print("="*30 + "\n")

def skipped_msg(skipped, remaining, no_episode_detail, u_episodes, renamed_files, use_emojis):
    print("\n" + "="*30)
    print(f"{get_label('summary', use_emojis)}SKIPPED FILES SUMMARY")
    print("="*30)

    if skipped:
        print(f"\n{get_label('skipped', use_emojis)}Skipped Files:")
        for file_data in skipped:
            print(f"   • {file_data['file_path']}")
    else:
        print(f"\n{get_label('skipped', use_emojis)}No files were skipped.")

    if unknown_files:
        print(f"\n{get_label('unexpected_ep', use_emojis)}Unexpected Files:")
        for file_data in unknown_files:
            print(f"   • {file_data['file_path']}")
    else:
        print(f"\n{get_label('unexpected_ep', use_emojis)}No unexpected files were detected.")

    if remaining:
        print(f"\n{get_label('unprocessed', use_emojis)}Unprocessed Files:")
        for file_data in remaining:
            print(f"   • {file_data['file_path']}")
    else:
        print(f"\n{get_label('unprocessed', use_emojis)}All files were processed.")

    if no_episode_detail:
        print(f"\n{get_label('no_se_ep', use_emojis)}Episodes Missing Season/Episode Info:")
        for file_data in no_episode_detail:
            print(f"   • {file_data['file_path']}")
    else:
        print(f"\n{get_label('no_se_ep', use_emojis)}All episodes have season and episode numbers.")

    if u_episodes:
        print(f"\n{get_label('unexpected_ep', use_emojis)}Episodes With Unexpected Format (e.g. S01E0102, S01E01-02, 1x0102):")
        for file_data in u_episodes:
            print(f"   • {file_data['file_path']}")
    else:
        print(f"\n{get_label('unexpected_ep', use_emojis)}No unexpected episode formats detected.")

    if renamed_files:
        print(f"\n{get_label('renamed', use_emojis)}Files renamed:")
        for file_data in renamed_files:
            print(f"   • {file_data['file_path']}")
        print(f"\n {len(renamed_files)} file(s) renamed successfully.")
    else:
        print(f"\n{get_label('renamed', use_emojis)}No files were renamed (dry run or no matches).")

    print("\n" + "="*30)
    print(f"{get_label('done', use_emojis)} Done!")
    print("Skipped files processing completed.")
    print("="*30 + "\n")
