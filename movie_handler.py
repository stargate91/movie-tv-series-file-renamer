from datetime import datetime

def normalize_movies(movies):
    handled_files = []

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

        handled_files.append({
            'file_path': file_data['file_path'],
            'file_type': file_data['file_type'],
            'extras': file_data['extras'],
            'movie_details': movie_details
            })

    return handled_files


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
    print(f"Available APIs: {', '.join(others)}")
    new_api = input("Switch to: ").strip()
    if new_api in available:
        return new_api
    print("Invalid API, staying on current.")
    return current

def handle_movie_no(movie_no, api_client, current_api='omdb'):
    print("\n--- MOVIES WITH NO MATCH ---")
    for idx, movie in enumerate(movie_no, 1):
        print(f"{idx}. {movie['file_path']}")
    print("\nManual search required for these movies.\n")
    
    print("Options:\n1: Manual search for all\n2: Decide per movie (y/n/c)\n3: Cancel")
    mode = input("Choose an option: ").strip()

    if mode == '3':
        print("Cancelled.")
        return []

    handled_movies = []
    skipped_movies = []

    for movie in movie_no:
        if mode == '2':
            choice = input(f"\nSearch for: {movie['file_path']}? (y/n/c): ").strip().lower()
            if choice == 'c':
                print("Cancelled.")
                break
            if choice != 'y':
                continue

        print(f"\n Search for: {movie['file_path']}")
        title = input("Title: ").strip()
        year = input("Year (optional): ").strip() or 'unknown'

        while True:
            api_func = get_api_func(api_client, current_api)
            result = api_func(title, year)

            if not result or not has_results(result, current_api):
                print("No results found.")
            else:
                options = extract_results(result, current_api)
                for i, opt in enumerate(options, 1):
                    print(f"{i}. {opt.get('title') or opt.get('Title')} ({opt.get('year') or opt.get('release_date') or 'unknown'})")

                print("Select result by number, or:")
                print("r: retry search")
                print("a: try another API")
                print("s: skip")
                print("c: cancel")
                sel = input("Choice: ").strip().lower()

                if sel.isdigit() and 1 <= int(sel) <= len(options):
                    selected = options[int(sel) - 1]
                    handled_movies.append({
                        'file_path': movie['file_path'],
                        'file_type': movie['file_type'],
                        'extras': movie['extras'],
                        'details': selected
                    })
                    break

                elif sel == 'r':
                    continue
                elif sel == 'a':
                    current_api = switch_api(current_api)
                    continue
                elif sel == 's':
                    skipped_movies.append(movie)
                    break
                elif sel == 'c':
                    print("Cancelled.")
                    return handled_movies
                else:
                    print("Invalid input.")
            title = input("Retry title: ").strip()
            year = input("Year (optional): ").strip() or 'unknown'

    return handled_movies, skipped_movies

def handle_movie_mult(movie_mult, api_client, current_api='omdb'):
    print("\n--- MOVIES WITH MULTIPLE MATCHES ---")
    for idx, movie in enumerate(movie_mult, 1):
        print(f"{idx}. {movie['file_path']}")
    print("\nMultiple matches found for these movies. Manual selection is required.\n")

    print("Options:\n1: Manually choose for each\n2: Cancel")
    mode = input("Choose an option: ").strip()

    if mode == '2':
        print("Cancelled.")
        return [], []

    handled_movies = []
    skipped_movies = []

    for movie in movie_mult:
        print(f"\n--- {movie['file_path']} ---")
        details = movie['details']
        results = extract_results(details, current_api)

        for i, res in enumerate(results, 1):
            print(f"{i}. {res.get('title') or res.get('Title')} ({res.get('year') or res.get('release_date') or 'unknown'})")

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
                    for i, res in enumerate(results, 1):
                        print(f"{i}. {res.get('title') or res.get('Title')} ({res.get('year') or res.get('release_date') or 'unknown'})")
                else:
                    print("No results.")
            elif sel == 'a':
                current_api = switch_api(current_api)
            elif sel == 's':
                skipped_movies.append(movie)
                break
            elif sel == 'c':
                print("Cancelled.")
                return handled_movies, skipped_movies
            else:
                print("Invalid input.")

    return handled_movies, skipped_movies

