from ui.ui_interface import UIInterface
from utils.helper import extract_results, search_api, build_entry

def handle_movies_with_no_match(movie_no, api_client, ui: UIInterface):
    if not movie_no:
        return [], [], []
    
    # Selection logic moved here from ui_ux to make UI generic
    ui.show_message(f"MOVIES WITH NO MATCH", level="info")
    for idx, vid in enumerate(movie_no, 1):
        ui.show_message(f"{idx}. {vid['file_path']}")
    
    ui.show_message("Manual search required for these movies.", level="info")
    choice = ui.ask_decision("Options: 1: Manual search for all, 2: Cancel", ["1", "2"])

    if choice == "2":
        # Handle cancellation
        ui.show_message("Manual search cancelled by user.")
        return [], [], movie_no

    handled_movies = []
    skipped_movies = []
    
    for idx, movie in enumerate(movie_no):
        ui.show_message(f"\nProcessing: {movie['file_path']}")
        decision = ui.ask_decision("Do you want to search manually? (y/n/c)", ["y", "n", "c"])
        
        if decision == 'c':
            ui.show_message("Search cancelled.")
            remaining = movie_no[idx:]
            return handled_movies, skipped_movies, remaining
        elif decision == 'n':
            skipped_movies.append(movie)
            continue

        title = ui.ask_input("Title", default="")
        year = ui.ask_input("Year (optional)", default="unknown")
        
        while True:
            result, options = search_api(api_client, 'tmdb', title, year)

            if not options:
                ui.show_message("No results found.", level="warning")
                sel = ui.ask_decision("Options: [r] Retry search, [s] Skip, [c] Cancel", ["r", "s", "c"])
                if sel == 'r':
                    title = ui.ask_input("Retry title", default="")
                    year = ui.ask_input("Year (optional)", default="unknown")
                    continue
                elif sel == 's':
                    skipped_movies.append(movie)
                    break
                elif sel == 'c':
                    remaining = movie_no[idx:]
                    return handled_movies, skipped_movies, remaining

            sel = ui.ask_input("Select result by number, or [r] Retry, [s] Skip, [c] Cancel", default="s")
            
            if sel.isdigit():
                num = int(sel)
                if 1 <= num <= len(options):
                    selected = options[num - 1]
                    handled_movies.append(build_entry(movie, selected))
                    break
                else:
                    ui.show_message("Invalid number.", level="error")
            elif sel == 'r':
                title = ui.ask_input("Retry title", default="")
                year = ui.ask_input("Year (optional)", default="unknown")
                continue
            elif sel == 's':
                skipped_movies.append(movie)
                break
            elif sel == 'c':
                remaining = movie_no[idx:]
                return handled_movies, skipped_movies, remaining

    return handled_movies, skipped_movies, []

def handle_movies_with_multiple_matches(movie_mult, api_client, ui: UIInterface):
    if not movie_mult:
        return [], [], []
    
    ui.show_message(f"MOVIES WITH MULTIPLE MATCHES", level="info")
    for idx, vid in enumerate(movie_mult, 1):
        ui.show_message(f"{idx}. {vid['file_path']}")
    
    choice = ui.ask_decision("Options: 1: Manual selection for all, 2: Cancel", ["1", "2"])

    if choice == "2":
        return [], [], movie_mult

    handled_movies = []
    skipped_movies = []

    for idx, movie in enumerate(movie_mult):
        details = movie['details']
        options = extract_results(details)

        ui.show_message(f"\nSelection for: {movie['file_path']}")
        
        while True:
            # We use ask_selection which handles the display of options
            sel = ui.ask_input("Select result by number, or [r] Retry search, [s] Skip, [c] Cancel", default="s")
            
            if sel.isdigit():
                num = int(sel)
                if 1 <= num <= len(options):
                    selected = options[num - 1]
                    handled_movies.append(build_entry(movie, selected))
                    break
                else:
                    ui.show_message("Invalid number.", level="error")
            elif sel == 'r':
                title = ui.ask_input("Title", default="")
                year = ui.ask_input("Year (optional)", default="unknown")
                result, options_new = search_api(api_client, 'tmdb', title, year)
                if options_new:
                    options = options_new
                    # The loop continues with new options
                else:
                    ui.show_message("No results found.", level="warning")
            elif sel == 's':
                skipped_movies.append(movie)
                break
            elif sel == 'c':
                remaining = movie_mult[idx:]
                return handled_movies, skipped_movies, remaining

    return handled_movies, skipped_movies, []
