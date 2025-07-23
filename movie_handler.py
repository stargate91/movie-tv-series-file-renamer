from ui_ux import show_list_and_get_user_choice, print_cancellation_summary, switch_api, prompt_search_decision, get_title_and_year_input
from ui_ux import display_res, action_menu, process_number_choice
from helper import extract_results, search_api

def handle_movie_no(movie_no, api_client, current_api='omdb'):
    
    handled, skipped, remaining, choice = show_list_and_get_user_choice(
        movie_no,
        current_api=current_api,
        content="movies",
        action="search",
        res_quantity="no match"
    )

    if choice == 2:
        return handled, skipped, remaining

    handled_movies = []
    skipped_movies = []
    remaining_movies = []

    for idx, movie in enumerate(movie_no):
        choice, handled_movies, skipped_movies, remaining_movies = prompt_search_decision(
        movie, idx, handled_movies, skipped_movies, movie_no, content="movies", action="search"
        )
        if choice == 'c':
            return handled_movies, skipped_movies, remaining_movies
        if choice == 'n' or choice == 's':
            continue

        title, year = get_title_and_year_input(mo=True, file=movie, current_api=current_api)
        while True:
            result, options = search_api(api_client, current_api, title, year)

            if not options:
                action_menu(no=True, mult_api=True)
                sel = input("Choice: ").strip().lower()
                if sel == 'r':
                    title, year = get_title_and_year_input(re=True, mo=True)
                    continue
                elif sel == 'a':
                    current_api = switch_api(current_api)
                    continue
                elif sel == 's':
                    skipped_movies.append(movie)
                    break
                elif sel == 'c':
                    handled_movies, skipped_movies, remaining_movies = print_cancellation_summary(
                        handled=handled_movies,
                        skipped=skipped_movies,
                        source=movie_no,
                        mode=1,
                        idx_or_processed=idx,
                        content="movies",
                        action="search"
                    )
                    return handled_movies, skipped_movies, remaining_movies
                else:
                    print("Invalid input. Please enter r, a, s, or c.")

            display_res(options)
            action_menu(mult_api=True)
            sel = input("Choice: ").strip().lower()
            if process_number_choice(sel, options, movie, handled_movies):
                break
            if sel == 'r':
                title, year = get_title_and_year_input(re=True, mo=True)
                continue
            elif sel == 'a':
                current_api = switch_api(current_api)
                continue
            elif sel == 's':
                skipped_movies.append(movie)
                break
            elif sel == 'c':
                handled_movies, skipped_movies, remaining_movies = print_cancellation_summary(
                    handled=handled_movies,
                    skipped=skipped_movies,
                    source=movie_no,
                    mode=1,
                    idx_or_processed=idx,
                    content="movies",
                    action="search"
                )
                return handled_movies, skipped_movies, remaining_movies
            else:
                print(f"Invalid input. Please enter a number between 1-{len(options)} or r, a, s, c.")

    return handled_movies, skipped_movies, remaining_movies

# ======================================================================
# ======================================================================
# ======================================================================

def handle_movie_mult(movie_mult, api_client, current_api='omdb'):
    
    handled, skipped, remaining, choice = show_list_and_get_user_choice(
        movie_mult,
        current_api=current_api,
        content="movies",
        action="selection",
        res_quantity="multiple matches"
    )

    if choice == 2:
        return handled, skipped, remaining

    handled_movies = []
    skipped_movies = []
    remaining_movies = []

    for idx, movie in enumerate(movie_mult):
        details = movie['details']
        options = extract_results(details, current_api)

        display_res(options, movie, content="movie")
        action_menu(mult_api=True)
        while True:
            sel = input("Choice: ").strip().lower()
            if process_number_choice(sel, options, movie, handled_movies):
                break
            elif sel == 'r':
                title, year = get_title_and_year_input(mo=True)
                result, options = search_api(api_client, current_api, title, year)
                if options:
                    display_res(options)
                else:
                    print("No results.")
            elif sel == 'a':
                current_api = switch_api(current_api)
                continue
            elif sel == 's':
                skipped_movies.append(movie)
                break
            elif sel == 'c':
                handled_movies, skipped_movies, remaining_movies = print_cancellation_summary(
                    handled=handled_movies,
                    skipped=skipped_movies,
                    source=movie_mult,
                    mode=1,
                    idx_or_processed=idx,
                    content="movies",
                    action="selection"
                )
                return handled_movies, skipped_movies, remaining_movies
            else:
                print(f"Invalid input. Please enter a number between 1-{len(options)} or r, a, s, c.")

    return handled_movies, skipped_movies, remaining_movies
