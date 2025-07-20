from datetime import datetime

def normalize_movies(movies, source=None):

    if not movies:
        print(f"\n[INFO] There are no movies to normalize in this pack: {source}.\n")
        return []
    
    handled_movies = []

    for file_data in movies:
        movie_details = file_data['details']

        if movie_details.get('results'):
            movie_details = movie_details['results'][0]

        if 'release_date' in movie_details:
            movie_details.update({'year': movie_details['release_date'].split('-')[0]})

        if 'Title' in movie_details:
            movie_details['title'] = movie_details.pop('Title')

        if 'Released' in movie_details:
            movie_details['release_date'] = movie_details.pop('Released')
            movie_details['release_date'] = datetime.strptime(movie_details['release_date'], "%d %b %Y").strftime("%Y-%m-%d")

        if 'Year' in movie_details:
            movie_details['year'] = movie_details.pop('Year')

        handled_movies.append({
            'file_path': file_data['file_path'],
            'file_type': file_data['file_type'],
            'extras': file_data['extras'],
            'movie_details': movie_details
            })

    return handled_movies

def get_api_func(api_client, source):
    return {
        'omdb': api_client.get_from_omdb,
        'tmdb': api_client.get_from_tmdb_movie
    }.get(source)

def has_results(result, source):
    if source == 'omdb':
        return result.get("Response") == "True"
    if source == 'tmdb':
        return result.get("total_results", 0) > 0
    return False

def extract_results(result, source):
    if source == 'omdb':
        return [result]
    if source == 'tmdb':
        return result.get('results', [])
    return []

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

def handle_cancellation(handled_movies, skipped_movies, movie_no, idx):
    print("\n[INFO] Manual search cancelled by user.\n")

    if handled_movies:
        print("\nMetada stored for the following movies:\n")
        for file in handled_movies:
            print(f"[SAVED] {file['file_path']}")
    else:
        print("\nNo metadata was stored.")

    if skipped_movies:
        print("\nThe following movies were deferred for later:\n")
        for skip in skipped_movies:
            print(f"[SKIPPED] {skip['file_path']}")

    remaining_movies = movie_no[idx:]

    if remaining_movies:
        print("\nThe following movies were not processed:\n")
        for leftover in remaining_movies:
            print(f"[INFO] {leftover['file_path']}")
    else:
        print("\n[INFO] All movies have been processed.")

    return handled_movies, skipped_movies, remaining_movies


def handle_movie_no(movie_no, api_client, current_api='omdb'):
    print("\n=== MOVIES WITH NO MATCH ===")

    if not movie_no:
        print("\n[INFO] There are no movies with no match. Continue with the next task.")
        return

    print(f"\n[INFO] Current API: {current_api.upper()}\n")

    for idx, movie in enumerate(movie_no, 1):
        print(f"{idx}. {movie['file_path']}")

    print("\nManual search required for these movies.\n")
    
    print("Options:\n1: Manual search for all\n2: Decide per movie (y/n/c)\n3: Cancel")
    mode = input("Choose an option (1/2/3): ").strip()
    while mode not in {'1', '2', '3'}:
        print("Invalid input. Please enter 1, 2, or 3.")
        mode = input("Choose an option (1/2/3): ").strip()

    if mode == '3':
        print("\n[INFO] Manual search cancelled by user.")
        return [], [], []

    handled_movies = []
    skipped_movies = []
    remaining_movies = []

    for idx, movie in enumerate(movie_no):
        if mode == '2':
            valid_choices = {'y', 'n', 'c'}
            choice = input(f"\nSearch for: {movie['file_path']}? (y/n/c): ").strip().lower()
            while choice not in valid_choices:
                print("Invalid input. Please enter y, n, or c.")
                choice = input(f"\nSearch for: {movie['file_path']}? (y/n/c): ").strip().lower()
            if choice == 'c':
                return handle_cancellation(handled_movies, skipped_movies, movie_no, idx)
            if choice != 'y':
                skipped_movies.append(movie)
                continue

        print(f"\n Search for: {movie['file_path']}")
        print(f"[API: {current_api.upper()}]")
        title = input("Title: ").strip()
        year = input("Year (optional): ").strip() or 'unknown'

        while True:
            api_func = get_api_func(api_client, current_api)
            result = api_func(title, year)

            options = extract_results(result, current_api) if result else []

            if not options:
                print("No results found.")
                print("Options:")
                print("r: retry search")
                print("a: try another API")
                print("s: skip")
                print("c: cancel")
                sel = input("Choice: ").strip().lower()
                if sel == 'r':
                    title = input("Retry title: ").strip()
                    year = input("Year (optional): ").strip() or 'unknown'
                    continue
                elif sel == 'a':
                    current_api = switch_api(current_api)
                    continue
                elif sel == 's':
                    skipped_movies.append(movie)
                    break
                elif sel == 'c':
                    return handle_cancellation(handled_movies, skipped_movies, movie_no, idx)
                else:
                    print("Invalid input. Please enter r, a, s, or c.")

            print("\nFound results:")
            for i, opt in enumerate(options, 1):
                print(f"{i}. {opt.get('title') or opt.get('Title')} ({opt.get('Year') or opt.get('release_date') or 'unknown'})")

            print("Select result by number, or:")
            print("r: retry search")
            print("a: try another API")
            print("s: skip")
            print("c: cancel")
            sel = input("Choice: ").strip().lower()
            valid_cmds = {'r', 'a', 's', 'c'}
            if sel.isdigit():
                num = int(sel)
                if 1 <= num <= len(options):
                    selected = options[num - 1]
                    handled_movies.append({
                        'file_path': movie['file_path'],
                        'file_type': movie['file_type'],
                        'extras': movie['extras'],
                        'details': selected
                    })
                    break
                else:
                    print("Invalid number.")
            elif sel in valid_cmds:
                if sel == 'r':
                    title = input("Retry title: ").strip()
                    year = input("Year (optional): ").strip() or 'unknown'
                    continue
                elif sel == 'a':
                    current_api = switch_api(current_api)
                    continue
                elif sel == 's':
                    skipped_movies.append(movie)
                    break
                elif sel == 'c':
                    return handle_cancellation(handled_movies, skipped_movies, movie_no, idx)
            else:
                print(f"Invalid input. Please enter a number between 1-{len(options)} or r, a, s, c.")

    return handled_movies, skipped_movies, remaining_movies

def handle_movie_mult(movie_mult, api_client, current_api='omdb'):
    print("\n=== MOVIES WITH MULTIPLE MATCHES ===")

    if not movie_mult:
        print("\n[INFO] There are no movies with multiple matches.")
        return

    print(f"\n[INFO] Current API: {current_api.upper()}\n")

    for idx, movie in enumerate(movie_mult, 1):
        print(f"{idx}. {movie['file_path']}")

    print("\nnMultiple matches found for these movies. Manual selection is required.\n")

    print("Options:\n1: Manually choose for each\n2: Cancel")
    mode = input("Choose an option: ").strip()

    if mode == '2':
        print("\n[INFO] Manual selection cancelled by user.")
        return [], [], []

    handled_movies = []
    skipped_movies = []
    remaining_movies = []

    for idx, movie in enumerate(movie_mult):
        print(f"\n Choose a result or an action for this movie: {movie['file_path']}")
        details = movie['details']
        results = extract_results(details, current_api)

        for i, res in enumerate(results, 1):
            print(f"{i}. {res.get('title') or res.get('Title')} ({res.get('Year') or res.get('release_date') or 'unknown'})")

        print("Select result by number, or:")
        print("r: retry search")
        print("a: try another API")
        print("s: skip")
        print("c: cancel")

        while True:
            sel = input("Choice: ").strip().lower()

            if sel.isdigit() and 1 <= int(sel) <= len(results):
                selected = results[int(sel) - 1]
                handled_movies.append({
                    'file_path': movie['file_path'],
                    'file_type': movie['file_type'],
                    'extras': movie['extras'],
                    'details': selected
                })
                break
            elif sel == 'r':
                title = input("Title: ").strip()
                year = input("Year (optional): ").strip() or 'unknown'
                result = get_api_func(api_client, current_api)(title, year)
                if has_results(result, current_api):
                    results = extract_results(result, current_api)
                    print("Found results:")
                    for i, res in enumerate(results, 1):
                        print(f"{i}. {res.get('title') or res.get('Title')} ({res.get('Year') or res.get('release_date') or 'unknown'})")
                else:
                    print("No results.")
            elif sel == 'a':
                current_api = switch_api(current_api)
                continue
            elif sel == 's':
                skipped_movies.append(movie)
                break
            elif sel == 'c':
                return handle_cancellation(handled_movies, skipped_movies, movie_mult, idx)
            else:
                print(f"Invalid input. Please enter a number between 1-{len(results)} or r, a, s, c.")

    return handled_movies, skipped_movies, remaining_movies
