from ui_ux import process_number_choice, print_cancellation_summary, show_list_and_get_user_choice
from ui_ux import get_title_and_year_input, display_res, action_menu
from helper import build_entry, extract_results, search_api
import os

def handle_episodes_with_no_match(episode_no, api_client):

    if not episode_no:
        print(f"\n[INFO] There are no episodes with no match. Continue with the next task.")
        return [], [], []

    folders, main_folders, action_choice = show_list_and_get_user_choice(
        episode_no,
        content="episodes",
        action="search",
        res_quantity="no match"
    )

    skipped_episodes = []
    handled_episodes = []
    remaining_episodes = [] 

    if action_choice == 1:
        for idx, episode in enumerate(episode_no):
            title, year = get_title_and_year_input(ep=True, file=episode)

            while True:
                result, options = search_api(api_client, 'tmdb_tv', title, year)

                if not options:
                    action_menu(no=True)
                    sel = input("Choice: ").strip().lower()
                    if sel == 'r':
                        title, year = get_title_and_year_input(re=True, ep=True)
                        continue
                    elif sel == 's':
                        skipped_episodes.append(episode)
                        break
                    elif sel == 'c':
                        handled_episodes, skipped_episodes, remaining_episodes = print_cancellation_summary(
                            handled=handled_episodes,
                            skipped=skipped_episodes,
                            source=episode_no,
                            mode=1,
                            idx_or_processed=idx,
                            content="series",
                            action="search"
                        )
                        return handled_episodes, skipped_episodes, remaining_episodes
                    else:
                        print("Invalid input. Please enter r, s, or c.")

                display_res(options)
                action_menu()
                sel = input("Choice: ").strip().lower()
                if process_number_choice(sel, options, episode, handled_episodes):
                    break
                elif sel == 'r':
                    title, year = get_title_and_year_input(re=True, ep=True)
                    continue
                elif sel == 's':
                    skipped_episodes.append(episode)
                    break
                elif sel == 'c':
                    handled_episodes, skipped_episodes, remaining_episodes = print_cancellation_summary(
                        handled=handled_episodes,
                        skipped=skipped_episodes,
                        source=episode_no,
                        mode=1,
                        idx_or_processed=idx,
                        content="series",
                        action="search"
                    )
                    return handled_episodes, skipped_episodes, remaining_episodes
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(options)} or r, s, c.")

    elif action_choice == 2:
        processed_folders = []

        for season_dir, episodes in folders.items():
            title, year = get_title_and_year_input(ep=True, folder=season_dir)

            while True:
                result, options = search_api(api_client, 'tmdb_tv', title, year)

                if not options:
                    action_menu(no=True)
                    sel = input("Choice: ").strip().lower()
                    if sel == 'r':
                        title, year = get_title_and_year_input(re=True, ep=True)
                        continue
                    elif sel == 's':
                        skipped_episodes.extend(episodes)
                        break
                    elif sel == 'c':
                        handled_episodes, skipped_episodes, remaining_episodes = print_cancellation_summary(
                            handled=handled_episodes,
                            skipped=skipped_episodes,
                            source=folders,
                            mode=2,
                            idx_or_processed=processed_folders,
                            content="series",
                            action="search"
                        )
                        return handled_episodes, skipped_episodes, remaining_episodes
                    else:
                        print("Invalid input. Please enter r, s, or c.")

                display_res(options)
                action_menu()
                sel = input("Choice: ").strip().lower()
                if sel.isdigit() and 1 <= int(sel) <= len(options):
                    selected = options[int(sel) - 1]
                    for episode in episodes:
                        handled_episodes.append(build_entry(episode, selected))
                    processed_folders.append(season_dir)
                    break
                elif sel == 'r':
                    title, year = get_title_and_year_input(re=True, ep=True)
                    continue
                elif sel == 's':
                    skipped_episodes.extend(episodes)
                    break
                elif sel == 'c':
                    handled_episodes, skipped_episodes, remaining_episodes = print_cancellation_summary(
                        handled=handled_episodes,
                        skipped=skipped_episodes,
                        source=folders,
                        mode=2,
                        idx_or_processed=processed_folders,
                        content="series",
                        action="search"
                    )
                    return handled_episodes, skipped_episodes, remaining_episodes
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(options)} or r, s, c.")

    elif action_choice == 3:
        processed_folders = []

        for series_dir, episodes in main_folders.items():
            title, year = get_title_and_year_input(ep=True, folder=series_dir)

            while True:
                result, options = search_api(api_client, 'tmdb_tv', title, year)

                if not options:
                    action_menu(no=True)
                    sel = input("Choice: ").strip().lower()
                    if sel == 'r':
                        title, year = get_title_and_year_input(re=True, ep=True)
                        continue
                    elif sel == 's':
                        skipped_episodes.extend(episodes)
                        break
                    elif sel == 'c':
                        handled_episodes, skipped_episodes, remaining_episodes = print_cancellation_summary(
                            handled=handled_episodes,
                            skipped=skipped_episodes,
                            source=main_folders,
                            mode=2,
                            idx_or_processed=processed_folders,
                            content="series",
                            action="search"
                        )
                        return handled_episodes, skipped_episodes, remaining_episodes
                    else:
                        print("Invalid input. Please enter r, s, or c.")

                display_res(options)
                action_menu()
                sel = input("Choice: ").strip().lower()
                if sel.isdigit() and 1 <= int(sel) <= len(options):
                    selected = options[int(sel) - 1]
                    for episode in episodes:
                        handled_episodes.append(build_entry(episode, selected))
                    processed_folders.append(series_dir)
                    break
                elif sel == 'r':
                    title, year = get_title_and_year_input(re=True, ep=True)
                    continue
                elif sel == 's':
                    skipped_episodes.extend(episodes)
                    break
                elif sel == 'c':
                    handled_episodes, skipped_episodes, remaining_episodes = print_cancellation_summary(
                        handled=handled_episodes,
                        skipped=skipped_episodes,
                        source=main_folders,
                        mode=2,
                        idx_or_processed=processed_folders,
                        content="series",
                        action="search"
                    )
                    return handled_episodes, skipped_episodes, remaining_episodes
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(options)} or r, s, c.")

    else:
        handle, skipped, remaining = print_cancellation_summary(handled=None, skipped=None, source=episode_no, mode=1, idx_or_processed=0, content="episodes", action="search")
        return handle, skipped, remaining

    return handled_episodes, skipped_episodes, remaining_episodes

# ======================================================================
# ======================================================================
# ======================================================================

def handle_episodes_with_multiple_matches(episode_mult, api_client):

    if not episode_mult:
        print(f"\n[INFO] There are no episodes with multiple matches. Continue with the next task.")
        return [], [], []

    folders, main_folders, action_choice = show_list_and_get_user_choice(
        episode_mult,
        content="episodes",
        action="selection",
        res_quantity="multiple matches"
    )

    skipped_episodes = []
    handled_episodes = []
    remaining_episodes = [] 

    if action_choice == 1:

        for idx, episode in enumerate(episode_mult):
            details = episode['details']
            options = extract_results(details)

            display_res(options, episode, content="episode")
            action_menu()
            while True:
                sel = input("Choice: ").strip().lower()
                if process_number_choice(sel, options, episode, handled_episodes):
                    break
                elif sel == 'r':
                    title, year = get_title_and_year_input(ep=True)
                    result, options = search_api(api_client, 'tmdb_tv', title, year)
                    if options:
                        display_res(options)
                    else:
                        print("No results.")
                elif sel == 's':
                    skipped_episodes.append(episode)
                    break
                elif sel == 'c':
                    handled_episodes, skipped_episodes, remaining_episodes = print_cancellation_summary(
                        handled=handled_episodes,
                        skipped=skipped_episodes,
                        source=episode_mult,
                        mode=1,
                        idx_or_processed=idx,
                        content="series",
                        action="selection"
                    )
                    return handled_episodes, skipped_episodes, remaining_episodes
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(options)} or r, s, c.")              

    elif action_choice == 2:
        processed_folders = []

        for season_dir, episodes in folders.items():
            prototype = episodes[0]
            details = prototype['details']
            options = extract_results(details)

            display_res(options, file=None, folder=season_dir, content=None)
            action_menu()
            while True:
                sel = input("Choice: ").strip().lower()
                if sel.isdigit() and 1 <= int(sel) <= len(options):
                    selected = options[int(sel) - 1]
                    for episode in episodes:
                        handled_episodes.append(build_entry(episode, selected))
                    processed_folders.append(season_dir)
                    break
                elif sel == 'r':
                    title, year = get_title_and_year_input(ep=True)
                    result, options = search_api(api_client, 'tmdb_tv', title, year)
                    if options:
                        display_res(options)
                    else:
                        print("No results.")
                elif sel == 's':
                    skipped_episodes.extend(episodes)
                    break
                elif sel == 'c':
                    handled_episodes, skipped_episodes, remaining_episodes = print_cancellation_summary(
                        handled=handled_episodes,
                        skipped=skipped_episodes,
                        source=folders,
                        mode=2,
                        idx_or_processed=processed_folders,
                        content="series",
                        action="selection"
                    )
                    return handled_episodes, skipped_episodes, remaining_episodes
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(options)} or r, s, c.")

    elif action_choice == 3:
        processed_folders = []

        for series_dir, episodes in main_folders.items():
            prototype = episodes[0]
            details = prototype['details']
            options = extract_results(details)

            display_res(options, file=None, folder=series_dir, content=None)
            action_menu()
            while True:
                sel = input("Choice: ").strip().lower()
                if sel.isdigit() and 1 <= int(sel) <= len(options):
                    selected = options[int(sel) - 1]
                    for episode in episodes:
                        handled_episodes.append(build_entry(episode, selected))
                    processed_folders.append(series_dir)
                    break
                elif sel == 'r':
                    title, year = get_title_and_year_input(ep=True)
                    result, options = search_api(api_client, 'tmdb_tv', title, year)
                    if options:
                        display_res(options)
                    else:
                        print("No results.")
                elif sel == 's':
                    skipped_episodes.extend(episodes)
                    break
                elif sel == 'c':
                    handled_episodes, skipped_episodes, remaining_episodes = print_cancellation_summary(
                        handled=handled_episodes,
                        skipped=skipped_episodes,
                        source=main_folders,
                        mode=2,
                        idx_or_processed=processed_folders,
                        content="series",
                        action="selection"
                    )
                    return handled_episodes, skipped_episodes, remaining_episodes
                else:
                    print(f"Invalid input. Please enter a number between 1-{len(options)} or r, s, c.")
    else:
        handle, skipped, remaining = print_cancellation_summary(handled=None, skipped=None, source=episode_mult, mode=1, idx_or_processed=0, content="episodes", action="selection")
        return handle, skipped, remaining

    return handled_episodes, skipped_episodes, remaining_episodes
