import os
import sys

from metadata.collector import get_all_video_files
from utils.sample import collect_sample_videos, expand_sample_keywords
from metadata.metadata import extract_metadata
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
        self.metadata_map = {} # Maps file_path -> result dict
        self.discovery_results = {} # Maps file_path -> discovery dict
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
        self.metadata_map = {} # path -> meta mapping for fast UI lookup

    def step_1_collect_files(self):
        """Collects sample videos and main video files from the target directory."""
        self.ui.update_progress(10, 100, "Status: Scanning...")
        if self.s.sample:
            keywords = expand_sample_keywords(self.s.sample_keywords)
            self.sample_files = collect_sample_videos(self.s.folder_path, self.s.recursive, keywords, self.s.vid_size)
        else:
            self.sample_files = []

        valid_exts = [ext.strip().lower() for ext in self.s.video_extensions.split(",") if ext.strip()]
        raw_files = get_all_video_files(self.s.folder_path, self.s.vid_size, self.s.recursive, valid_exts)
        self.video_files = [os.path.abspath(os.path.normpath(f)) for f in raw_files]
        
        self.ui.update_progress(100, 100, f"Status: Found {len(self.video_files)} files")
        return len(self.video_files) > 0

    def step_1b_discovery(self):
        """Analyzes files for NFOs and internal metadata."""
        from metadata.discovery import MetadataDiscovery
        discovery = MetadataDiscovery()
        self.discovery_results = discovery.discover(self.video_files, ui=self.ui)
        return any(self.discovery_results)

    def step_2_extract_metadata(self, custom_files=None):
        """
        Parses filenames and queries APIs for initial matches.
        Can optionally take a custom list of files (e.g. from skipped menu).
        """
        files_to_process = custom_files if custom_files is not None else self.video_files
        
        # Pass discovered IDs to the extractor if they exist
        discovered = getattr(self, 'discovery_results', {})
        
        self.collected_results, self.unknown_files = extract_metadata(
            files_to_process, self.api, self.s.source_mode, self.ui, 
            language=self.s.metadata_language,
            discovery_data=discovered
        )
        # Build map for UI
        for res in self.collected_results:
            norm_p = os.path.abspath(os.path.normpath(res['file_path']))
            self.metadata_map[norm_p] = res
            
        return any(self.collected_results)

    def step_4_standardize_and_enrich(self):
        """Converts dicts to Models, fetches extra details (ratings, genres) and maps samples."""
        standardized, missing = standardize_metadata(self.handled_results)
        
        if not any([standardized, missing]):
            return False

        new_enriched, unexpected = enricher(
            standardized, self.api, self.ui, 
            language=self.s.metadata_language,
            fallback_language=self.s.fallback_language,
            templates=[self.s.movie_template, self.s.episode_template],
            discovery_data=self.discovery_results
        )
        
        # Accumulate results: use a map to avoid duplicates and preserve previous matches
        # Initialize map from current enriched_files if not exists
        enriched_map = {os.path.abspath(os.path.normpath(f.file_path)): f for f in self.enriched_files}
        
        for item in new_enriched:
            norm_p = os.path.abspath(os.path.normpath(item.file_path))
            enriched_map[norm_p] = item
            
        self.enriched_files = list(enriched_map.values())
        self.unexpected_episodes.extend(unexpected)

        # Update metadata_map for UI with enriched data
        for item in self.enriched_files:
            norm_p = os.path.abspath(os.path.normpath(item.file_path))
            self.metadata_map[norm_p] = {
                'file_path': item.file_path,
                'file_type': item.file_type,
                'status': 'one_match',
                'details': item.__dict__,
                'is_manual': self.metadata_map.get(norm_p, {}).get('is_manual', False)
            }
        
        if self.ui:
            self.ui.update_progress(100, 100, "Status: Data Ready")
                    
        return True

    def step_5_rename(self):
        """Executes the renaming (or dry run) based on the enriched models."""
        self.renamed_files, self.rename_history = rename_video_files(
            self.enriched_files, self.s.live_run, self.s.zero_padding, self.s.custom_variable,
            self.s.movie_template, self.s.episode_template, self.s.filename_case, self.s.separator,
            self.s.sample_action, self.s.sample_suffix, self.ui
        )
        return self.renamed_files
