def ask_manual_search():
    return input("\nWould you like to search manually? (y/n): ").strip().lower() == 'y'

def get_manual_search_data():
    search_title = input("Enter movie title: ").strip()
    search_year = input("Enter movie release year (or leave empty to skip): ").strip()
    return search_title, search_year if search_year else None


def search_movie_tmdb(api_client, title, year):
    return api_client.get_from_tmdb_movie(title, year)

def search_movie_omdb(api_client, title, year):
    return api_client.get_from_omdb(title, year)

def process_search_results(api_source, data, file_data):
    if api_source == "omdb":
        if data.get("Response") == "True":
            print(f"Found result: {data['Title']} ({data['Year']})")
            return {
                "file_path": file_data['file_path'],
                "data": data,
                "extras": extras
                }
        else:
            print(f"No manual results found.")
            return None
    elif api_source == "tmdb":
        if data.get("total_results") > 0:
            results = data['results']
            print("Found results:")
            for idx, result in enumerate(results, start=1):
                print(f"{idx}. {result['title']} ({result['release_date']})")

            choice = ask_for_movie_choice(len(results))
            if choice:
                selected_result = results[choice - 1]
                print(f"User selected: {selected_result['title']} ({selected_result['release_date']})")
                return {
                    "file_path": file_data['file_path'],
                    "data": selected_result,
                    "extras": file_data['extras']
                    }
            else:
                print("Invalid choice. No movie selected.")
                return None
        else:
            print("No manual results found.")
            return None

def ask_for_movie_choice(max_choice):
    try:
        choice = int(input(f"Please select a movie by number (1-{max_choice}): "))
        if 1 <= choice <= max_choice:
            return choice
        else:
            return None
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None

def handle_no_movie_results(no_res, api_client, api_source):
    handled_files = []

    for file_data in no_res:
        extras = file_data.get('extras')
        print(f"\nAttempting manual search for: {file_data['file_path']}")
        
        if ask_manual_search():
            search_title, search_year = get_manual_search_data()

            if api_source == "omdb":
                data = search_movie_omdb(api_client, search_title, search_year)
            elif api_source == "tmdb":
                data = search_movie_tmdb(api_client, search_title, search_year)
            else:
                print("[ERROR] Unsupported API source for manual search.")
                continue

            if data:
                handled_files.append(process_search_results(api_source, data, file_data))

        else:
            print(f"Skipping manual search for {file_data['file_path']}.")

    return handled_files


def display_results(results):
    for idx, result in enumerate(results, start=1):
        title = result.get("title")
        release_date = result.get("release_date")
        print(f"{idx}. {title} ({release_date})")


def get_movie_choice(max_choice):
    try:
        choice = int(input(f"Please select a movie by number (1-{max_choice}): "))
        if 1 <= choice <= max_choice:
            return choice
        else:
            return None
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None

def handle_multiple_movie_results(mult_res):
    handled_files = []

    for file_data in mult_res:
        extras = file_data.get('extras')
        print(f"\nMultiple movie results found for: {file_data['file_path']}")
        results = file_data['data']['results']
        
        display_results(results)

        choice = get_movie_choice(len(results))
        
        if choice:
            selected_result = results[choice - 1]
            selected_title = selected_result.get('title')
            selected_release_date = selected_result.get("release_date")
            print(f"User selected: {selected_title} ({selected_release_date})")
            
            handled_files.append({
                "file_path": file_data['file_path'],
                "data": selected_result,
                "extras": extras
                })
        else:
            print("Invalid choice. No movie selected.")
    
    return handled_files
