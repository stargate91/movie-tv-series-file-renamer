import os
from core.scan_manager import ScanManager
from core.metadata_manager import MetadataManager
from core.renaming_engine import RenamingEngine

class RenamePipeline:
    """
    Orchestrates the entire renaming process.
    Uses AppState for centralized data storage.
    """
    def __init__(self, config_manager, api_client, ui_interface, state):
        self.cfg = config_manager
        self.api = api_client
        self.ui = ui_interface
        self.s = self.cfg.settings
        self.state = state # Centralized state

        # Specialized Managers
        self.scanner = ScanManager(self.s, self.ui)
        self.metadata = MetadataManager(self.api, self.s, self.ui)
        self.renamer = RenamingEngine(self.s, self.ui)

    @property
    def metadata_map(self): return self.state.metadata_map
    @metadata_map.setter
    def metadata_map(self, v): self.state.metadata_map = v

    @property
    def video_files(self): return self.state.video_files
    @video_files.setter
    def video_files(self, v): self.state.video_files = v

    @property
    def collected_results(self): return self.state.collected_results
    @collected_results.setter
    def collected_results(self, v): self.state.collected_results = v

    @property
    def enriched_files(self): return self.state.enriched_files
    @enriched_files.setter
    def enriched_files(self, v): self.state.enriched_files = v

    @property
    def discovery_results(self): return self.state.discovery_results
    @discovery_results.setter
    def discovery_results(self, v): self.state.discovery_results = v

    @property
    def renamed_files(self): return self.state.renamed_files
    @renamed_files.setter
    def renamed_files(self, v): self.state.renamed_files = v

    @property
    def rename_history(self): return self.state.rename_history
    @rename_history.setter
    def rename_history(self, v): self.state.rename_history = v


    def step_1_collect_files(self):
        """Delegates file collection to ScanManager, writing results to state."""
        self.state.video_files = self.scanner.collect_files(self.state.metadata_map)
        return len(self.state.video_files) > 0

    def unified_analysis(self):
        """One-click analysis: Discovery -> Match -> Enrich."""
        if not self.state.video_files:
            self.step_1_collect_files()
        if not self.state.video_files:
            return False

        # Filter out extras for analysis
        analyze_files = [f for f in self.state.video_files if self.state.metadata_map.get(f, {}).get('file_type') != 'extra']
        if not analyze_files:
            if self.ui:
                self.ui.update_progress(100, 100, "Status: Scan Complete (Only Extras Found)")
            return True

        # 1. Local Discovery
        self.state.discovery_results = self.metadata.discover(analyze_files)
        
        # 2. Matching
        self.state.collected_results, unknown = self.metadata.extract(analyze_files, self.state.discovery_results)
        
        # Update state map
        for res in self.state.collected_results:
            if isinstance(res, dict) and res.get('file_path'):
                norm_p = os.path.abspath(os.path.normpath(res['file_path']))
                self.state.metadata_map[norm_p] = res

        # 3. Enrichment
        to_enrich = [r for r in self.state.collected_results if isinstance(r, dict) and r.get('status') == 'one_match' and not r.get('is_enriched')]
        already_enriched_dicts = [r for r in self.state.collected_results if isinstance(r, dict) and r.get('status') == 'one_match' and r.get('is_enriched')]
        
        self.state.enriched_files = self.metadata.hydrate_from_cache(already_enriched_dicts)

        if to_enrich:
            self.state.enriched_files, self.state.unexpected_episodes = self.metadata.standardize_and_enrich(
                to_enrich, self.state.discovery_results, self.state.metadata_map, self.state.enriched_files
            )
            
        if self.ui:
            self.ui.update_progress(100, 100, "Status: Analysis Complete!")
        return True

    def step_1b_discovery(self, target_files=None):
        files = target_files if target_files is not None else self.state.video_files
        self.state.discovery_results = self.metadata.discover(files)
        return any(self.state.discovery_results)

    def step_2_extract_metadata(self, custom_files=None):
        files = custom_files if custom_files is not None else self.state.video_files
        self.state.collected_results, unknown = self.metadata.extract(files, self.state.discovery_results)
        
        for res in self.state.collected_results:
            if isinstance(res, dict) and res.get('file_path'):
                norm_p = os.path.abspath(os.path.normpath(res['file_path']))
                self.state.metadata_map[norm_p] = res
        return any(self.state.collected_results)

    def step_4_standardize_and_enrich(self):
        results_to_enrich = [r for r in self.state.collected_results if isinstance(r, dict) and r.get('status') == 'one_match']
        self.state.enriched_files, self.state.unexpected_episodes = self.metadata.standardize_and_enrich(
            results_to_enrich, self.state.discovery_results, self.state.metadata_map, self.state.enriched_files
        )
        return True

    def step_5_rename(self):
        self.state.renamed_files, self.state.rename_history = self.renamer.execute(self.state.enriched_files, self.state.metadata_map)
        return self.state.renamed_files
