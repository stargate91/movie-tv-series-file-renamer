from ui.ui_interface import UIInterface
from utils.helper import build_entry, extract_results, search_api, group_by_folders
import os

def handle_episodes_with_no_match(episode_no, api_client, ui: UIInterface):
    if not episode_no:
        return [], [], []

    ui.show_message("EPISODES WITH NO MATCH", level="info")
    for idx, vid in enumerate(episode_no, 1):
        ui.show_message(f"{idx}. {vid['file_path']}")

    folders, main_folders = group_by_folders(episode_no) 
    first_folder_key = next(iter(folders))
    first_main_folder_key = next(iter(main_folders))

    ui.show_message(f"Manual search required for these episodes.", level="info")
    menu_text = (
        "Choose how to apply metadata:\n"
        f"  [1] Apply to a single file only\n"
        f"  [2] Apply to the entire folder (e.g: {first_folder_key})\n"
        f"  [3] Apply to the main parent folder (e.g: {first_main_folder_key})\n"
        "  [4] Cancel"
    )
    action_choice = ui.ask_decision(menu_text, ["1", "2", "3", "4"])
    action_choice = int(action_choice)

    skipped_episodes = []
    handled_episodes = []

    if action_choice == 4:
        ui.show_message("Search cancelled.")
        return [], [], episode_no

    if action_choice == 1:
        for idx, episode in enumerate(episode_no):
            ui.show_message(f"\nProcessing: {episode['file_path']}")
            title = ui.ask_input("Series title", default="")
            year = ui.ask_input("First air year (optional)", default="unknown")

            while True:
                result, options = search_api(api_client, 'tmdb_tv', title, year)

                if not options:
                    ui.show_message("No results found.", level="warning")
                    sel = ui.ask_decision("Options: [r] Retry, [s] Skip, [c] Cancel", ["r", "s", "c"])
                    if sel == 'r':
                        title = ui.ask_input("Retry title", default="")
                        continue
                    elif sel == 's':
                        skipped_episodes.append(episode)
                        break
                    elif sel == 'c':
                        remaining = episode_no[idx:]
                        return handled_episodes, skipped_episodes, remaining

                sel = ui.ask_input("Select result by number, or [r] Retry, [s] Skip, [c] Cancel", default="s")
                if sel.isdigit():
                    num = int(sel)
                    if 1 <= num <= len(options):
                        selected = options[num - 1]
                        handled_episodes.append(build_entry(episode, selected))
                        break
                elif sel == 'r':
                    title = ui.ask_input("Retry title", default="")
                    continue
                elif sel == 's':
                    skipped_episodes.append(episode)
                    break
                elif sel == 'c':
                    remaining = episode_no[idx:]
                    return handled_episodes, skipped_episodes, remaining

    elif action_choice == 2:
        processed_folders = []
        folder_list = list(folders.items())
        for idx, (season_dir, episodes) in enumerate(folder_list):
            ui.show_message(f"\nProcessing folder: {season_dir}")
            title = ui.ask_input("Series title", default="")
            year = ui.ask_input("First air year (optional)", default="unknown")

            while True:
                result, options = search_api(api_client, 'tmdb_tv', title, year)

                if not options:
                    ui.show_message("No results found.", level="warning")
                    sel = ui.ask_decision("Options: [r] Retry, [s] Skip, [c] Cancel", ["r", "s", "c"])
                    if sel == 'r':
                        title = ui.ask_input("Retry title", default="")
                        continue
                    elif sel == 's':
                        skipped_episodes.extend(episodes)
                        break
                    elif sel == 'c':
                        remaining = []
                        for _, e in folder_list[idx:]: remaining.extend(e)
                        return handled_episodes, skipped_episodes, remaining

                sel = ui.ask_input("Select result by number, or [r] Retry, [s] Skip, [c] Cancel", default="s")
                if sel.isdigit() and 1 <= int(sel) <= len(options):
                    selected = options[int(sel) - 1]
                    for episode in episodes:
                        handled_episodes.append(build_entry(episode, selected))
                    break
                elif sel == 'r':
                    title = ui.ask_input("Retry title", default="")
                    continue
                elif sel == 's':
                    skipped_episodes.extend(episodes)
                    break
                elif sel == 'c':
                    remaining = []
                    for _, e in folder_list[idx:]: remaining.extend(e)
                    return handled_episodes, skipped_episodes, remaining

    elif action_choice == 3:
        main_folder_list = list(main_folders.items())
        for idx, (series_dir, episodes) in enumerate(main_folder_list):
            ui.show_message(f"\nProcessing main folder: {series_dir}")
            title = ui.ask_input("Series title", default="")
            year = ui.ask_input("First air year (optional)", default="unknown")

            while True:
                result, options = search_api(api_client, 'tmdb_tv', title, year)

                if not options:
                    ui.show_message("No results found.", level="warning")
                    sel = ui.ask_decision("Options: [r] Retry, [s] Skip, [c] Cancel", ["r", "s", "c"])
                    if sel == 'r':
                        title = ui.ask_input("Retry title", default="")
                        continue
                    elif sel == 's':
                        skipped_episodes.extend(episodes)
                        break
                    elif sel == 'c':
                        remaining = []
                        for _, e in main_folder_list[idx:]: remaining.extend(e)
                        return handled_episodes, skipped_episodes, remaining

                sel = ui.ask_input("Select result by number, or [r] Retry, [s] Skip, [c] Cancel", default="s")
                if sel.isdigit() and 1 <= int(sel) <= len(options):
                    selected = options[int(sel) - 1]
                    for episode in episodes:
                        handled_episodes.append(build_entry(episode, selected))
                    break
                elif sel == 'r':
                    title = ui.ask_input("Retry title", default="")
                    continue
                elif sel == 's':
                    skipped_episodes.extend(episodes)
                    break
                elif sel == 'c':
                    remaining = []
                    for _, e in main_folder_list[idx:]: remaining.extend(e)
                    return handled_episodes, skipped_episodes, remaining

    return handled_episodes, skipped_episodes, []

def handle_episodes_with_multiple_matches(episode_mult, api_client, ui: UIInterface):
    if not episode_mult:
        return [], [], []

    ui.show_message("EPISODES WITH MULTIPLE MATCHES", level="info")
    for idx, vid in enumerate(episode_mult, 1):
        ui.show_message(f"{idx}. {vid['file_path']}")

    folders, main_folders = group_by_folders(episode_mult) 
    first_folder_key = next(iter(folders))
    first_main_folder_key = next(iter(main_folders))

    menu_text = (
        "Choose how to apply metadata:\n"
        f"  [1] Apply to a single file only\n"
        f"  [2] Apply to the entire folder (e.g: {first_folder_key})\n"
        f"  [3] Apply to the main parent folder (e.g: {first_main_folder_key})\n"
        "  [4] Cancel"
    )
    action_choice = ui.ask_decision(menu_text, ["1", "2", "3", "4"])
    action_choice = int(action_choice)

    skipped_episodes = []
    handled_episodes = []

    if action_choice == 4:
        return [], [], episode_mult

    if action_choice == 1:
        for idx, episode in enumerate(episode_mult):
            options = extract_results(episode['details'])
            ui.show_message(f"\nSelection for: {episode['file_path']}")
            
            while True:
                sel = ui.ask_input("Select result by number, or [r] Retry, [s] Skip, [c] Cancel", default="s")
                if sel.isdigit():
                    num = int(sel)
                    if 1 <= num <= len(options):
                        selected = options[num - 1]
                        handled_episodes.append(build_entry(episode, selected))
                        break
                elif sel == 'r':
                    title = ui.ask_input("Series title", default="")
                    result, options_new = search_api(api_client, 'tmdb_tv', title)
                    if options_new: options = options_new
                elif sel == 's':
                    skipped_episodes.append(episode)
                    break
                elif sel == 'c':
                    remaining = episode_mult[idx:]
                    return handled_episodes, skipped_episodes, remaining

    elif action_choice == 2:
        folder_list = list(folders.items())
        for idx, (season_dir, episodes) in enumerate(folder_list):
            prototype = episodes[0]
            options = extract_results(prototype['details'])
            ui.show_message(f"\nSelection for folder: {season_dir}")
            
            while True:
                sel = ui.ask_input("Select result by number, or [r] Retry, [s] Skip, [c] Cancel", default="s")
                if sel.isdigit() and 1 <= int(sel) <= len(options):
                    selected = options[int(sel) - 1]
                    for episode in episodes:
                        handled_episodes.append(build_entry(episode, selected))
                    break
                elif sel == 'r':
                    title = ui.ask_input("Series title", default="")
                    result, options_new = search_api(api_client, 'tmdb_tv', title)
                    if options_new: options = options_new
                elif sel == 's':
                    skipped_episodes.extend(episodes)
                    break
                elif sel == 'c':
                    remaining = []
                    for _, e in folder_list[idx:]: remaining.extend(e)
                    return handled_episodes, skipped_episodes, remaining

    elif action_choice == 3:
        main_folder_list = list(main_folders.items())
        for idx, (series_dir, episodes) in enumerate(main_folder_list):
            prototype = episodes[0]
            options = extract_results(prototype['details'])
            ui.show_message(f"\nSelection for main folder: {series_dir}")
            
            while True:
                sel = ui.ask_input("Select result by number, or [r] Retry, [s] Skip, [c] Cancel", default="s")
                if sel.isdigit() and 1 <= int(sel) <= len(options):
                    selected = options[int(sel) - 1]
                    for episode in episodes:
                        handled_episodes.append(build_entry(episode, selected))
                    break
                elif sel == 'r':
                    title = ui.ask_input("Series title", default="")
                    result, options_new = search_api(api_client, 'tmdb_tv', title)
                    if options_new: options = options_new
                elif sel == 's':
                    skipped_episodes.extend(episodes)
                    break
                elif sel == 'c':
                    remaining = []
                    for _, e in main_folder_list[idx:]: remaining.extend(e)
                    return handled_episodes, skipped_episodes, remaining

    return handled_episodes, skipped_episodes, []
