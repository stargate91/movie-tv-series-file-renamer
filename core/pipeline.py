import os
import sys

from metadata.collector import get_all_video_files
from utils.sample import collect_sample_videos, expand_sample_keywords
from metadata.metadata import extract_metadata
from handlers.result_manager import get_handler
from metadata.metadata_standardizer import standardize_metadata
from metadata.metadata_enricher import enricher
from core.renamer import rename_video_files


class RenamePipeline:
    """
    Orchestrates the entire renaming process step-by-step.
    Designed to be used both by CLI (synchronously) and GUI (asynchronously/step-by-step).
    """
    
    def __init__(self, config_manager, api_client, ui_interface):
        self.cfg = config_manager
        self.api = api_client
        self.ui = ui_interface
        self.s = self.cfg.settings

        # State tracking for GUI/CLI
        self.sample_files = []
        self.video_files = []
        self.collected_results = []
        self.unknown_files = []
        
        self.handled_results = []
        self.skipped_results = []
        self.unprocessed_results = []
        
        self.standardized_files = []
        self.episodes_with_missing_data = []
        
        self.enriched_files = []
        self.unexpected_episodes = []
        
        self.renamed_files = []
        self.rename_history = []

    def step_1_collect_files(self):
        """Collects sample videos and main video files from the target directory."""
        self.ui.update_progress(10, 100, "Status: Scanning...")
        if self.s.sample:
            keywords = expand_sample_keywords(self.s.sample_keywords)
            self.sample_files = collect_sample_videos(self.s.folder_path, self.s.recursive, keywords, self.s.vid_size)
        else:
            self.sample_files = []

        valid_exts = [ext.strip().lower() for ext in self.s.video_extensions.split(",") if ext.strip()]
        self.video_files = get_all_video_files(self.s.folder_path, self.s.vid_size, self.s.recursive, valid_exts)
        
        self.ui.update_progress(100, 100, f"Status: Found {len(self.video_files)} files")
        return len(self.video_files) > 0

    def step_2_extract_metadata(self, custom_files=None):
        """
        Parses filenames and queries APIs for initial matches.
        Can optionally take a custom list of files (e.g. from skipped menu).
        """
        files_to_process = custom_files if custom_files is not None else self.video_files
        self.collected_results, self.unknown_files = extract_metadata(files_to_process, self.api, self.s.source_mode, self.ui)
        return any(self.collected_results)

    def step_3_resolve_conflicts(self, custom_results=None):
        """Prompts the UI (CLI/GUI) to resolve multiple or no-matches."""
        results_to_process = custom_results if custom_results is not None else self.collected_results
        self.handled_results, self.skipped_results, self.unprocessed_results = get_handler(
            results_to_process, self.api, self.s.interactive, self.ui
        )

    def step_4_standardize_and_enrich(self):
        """Converts dicts to Models, fetches extra details (ratings, genres) and maps samples."""
        self.standardized_files, self.episodes_with_missing_data = standardize_metadata(self.handled_results)
        
        if not any([self.standardized_files, self.episodes_with_missing_data]):
            return False

        self.enriched_files, self.unexpected_episodes = enricher(self.standardized_files, self.api)
        
        # Map samples to enriched objects
        if self.sample_files:
            unassigned_samples = set(self.sample_files)
            for item in self.enriched_files:
                item_dir = os.path.dirname(item.file_path)
                assigned = []
                for sample in list(unassigned_samples):
                    if sample.startswith(item_dir):
                        item.associated_samples.append(sample)
                        assigned.append(sample)
                for sample in assigned:
                    unassigned_samples.remove(sample)
                    
        return True

    def step_5_rename(self):
        """Executes the renaming (or dry run) based on the enriched models."""
        self.renamed_files, self.rename_history = rename_video_files(
            self.enriched_files, self.s.live_run, self.s.zero_padding, self.s.custom_variable,
            self.s.movie_template, self.s.episode_template, self.s.filename_case, self.s.separator,
            self.s.sample_action, self.s.sample_suffix, self.s.download_posters
        )
        return self.renamed_files
