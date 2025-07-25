from logger_setup import setup_logging
setup_logging()

from api_client import APIClient
from config import Config
from collector import get_all_video_files
from metadata import extract_metadata
from result_manager import get_handler
from metadata_standardizer import standardize_metadata
from metadata_enricher import enricher
from helper import save_skipped_to_file, load_skipped_menu, save_rename_history_to_file
from renamer import rename_video_files
from ui_ux import start_message, done_message
import sys


def main():

    config = Config()
    config.validate_api_keys()
    config_data = config.get_config()

    folder_path = config_data["folder_path"]
    interactive = config_data["interactive"]
    skipped_mode = config_data["skipped"]
    vid_size = config_data["vid_size"]
    recursive = config_data["recursive"]
    source_mode = config_data["source_mode"]
    undo = config_data['undo']
    history_file = config_data['history_file']
    custom_variable = config_data["custom_variable"]
    movie_template = config_data["movie_template"]
    episode_template = config_data["episode_template"]
    zero_padding = config_data["zero_padding"]
    live_run = config_data["live_run"]
    use_emojis = config_data["use_emojis"]
    filename_case = config_data["filename_case"]
    separator = config_data["separator"]
    
    omdb_key = config_data["omdb_key"]
    tmdb_key = config_data["tmdb_key"]
    tmdb_bearer_token = config_data["tmdb_bearer_token"]

    if undo:
        undo_rename(history_file=history_file, use_emojis=use_emojis)
        sys.exit(0)

    start_message(config.source, folder_path, use_emojis)

    api_client = APIClient(omdb_key, tmdb_key, tmdb_bearer_token)

# -------------------- Skipped mode --------------------

    if interactive and skipped_mode:
        skipped_files = load_skipped_menu()
        if skipped_files is None:
            pass
        else:
            handled, skipped, unprocessed = get_handler(skipped_files, api_client, interactive)
            standardized, eps_w_missing_data = standardize_metadata(handled)

            if not any([standardized, eps_w_missing_data]):
                sys.exit(0)

            enriched, unexpected_eps = enricher(standardized, api_client)
            renamed_skipped, renamed_skipped_history = rename_video_files(enriched, live_run, zero_padding, custom_variable, movie_template, episode_template, use_emojis, filename_case, separator)

            if live_run:
                save_rename_history_to_file(renamed_skipped_history)

            done_message(skipped, unprocessed, eps_w_missing_data, unexpected_eps, renamed_skipped, interactive, skipped_mode)

# -------------------- Normal mode --------------------

    video_files = get_all_video_files(folder_path, vid_size, recursive)
    collected_results, unknown_files = extract_metadata(video_files, api_client, source_mode)

    if not any(collected_results):
        sys.exit(0)

    handled_results, skipped_results, unprocessed_results = get_handler(collected_results, api_client, interactive)
    standardized_files, episodes_with_missing_data = standardize_metadata(handled_results)

    if not any([standardized_files, episodes_with_missing_data]):
        sys.exit(0)

    enriched_files, unexpected_episodes = enricher(standardized_files, api_client)
    renamed_files, rename_history = rename_video_files(enriched_files, live_run, zero_padding, custom_variable, movie_template, episode_template, use_emojis, filename_case, separator)

    if skipped_mode and skipped_results:
        save_skipped_to_file(skipped_results)

    if live_run:
        save_rename_history_to_file(rename_history)

    done_message(skipped_results, unprocessed_results, episodes_with_missing_data, unexpected_episodes, renamed_files, use_emojis, interactive, skipped_mode, unknown_files)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}")
    if getattr(sys, 'frozen', False):
        input("\n[INFO] Press Enter to exit...")
