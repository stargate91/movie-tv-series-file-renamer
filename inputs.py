def ask_manual_search():
    return input("\nWould you like to search manually? (y/n): ").strip().lower() == 'y'

def get_manual_movie_search_data():
    search_title = input("Enter movie title: ").strip()
    search_year = input("Enter movie release year (or leave empty to skip): ").strip()
    return search_title, search_year if search_year else None

def get_manual_series_search_data():
    search_title = input("Enter series title: ").strip()
    search_year = input("Enter series year (or leave empty to skip): ").strip()
    return search_title, search_year if search_year else "Unknown"

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

def get_series_choice(max_choice):
    try:
        choice = int(input(f"Please select a series by number (1-{max_choice}): "))
        if 1 <= choice <= max_choice:
            return choice
        else:
            print(f"Please enter a number between 1 and {max_choice}.")
            return None
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None


def user_menu_for_selection(files, folders, main_folders):
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