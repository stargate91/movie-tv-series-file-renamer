def ask_manual_search():
    return input("\nWould you like to search manually? (y/n): ").strip().lower() == 'y'

def get_manual_search_data():
    search_title = input("Enter movie title: ").strip()
    search_year = input("Enter movie release year (or leave empty to skip): ").strip()
    return search_title, search_year if search_year else None

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