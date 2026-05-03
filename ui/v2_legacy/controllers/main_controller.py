import os
from PySide6.QtWidgets import QMessageBox

class MainController:
    """
    Handles user actions and business logic.
    Communicates with the Pipeline for processing and AppState for data.
    """
    def __init__(self, window, pipeline, state):
        self.window = window
        self.pipeline = pipeline
        self.state = state

    def remove_file(self, file_path, refresh=True):
        """Removes a single file and cleans up state."""
        if not self.pipeline: return
        v_norm = os.path.abspath(os.path.normpath(file_path))
        
        self.state.video_files = [f for f in self.state.video_files if os.path.abspath(os.path.normpath(f)) != v_norm]
        
        if hasattr(self.state, 'collected_results') and self.state.collected_results:
            self.state.collected_results = [r for r in self.state.collected_results 
                                           if isinstance(r, dict) and os.path.abspath(os.path.normpath(r.get('file_path', ''))) != v_norm]
        
        if v_norm in self.state.metadata_map:
            del self.state.metadata_map[v_norm]
            
        if v_norm in self.state.selected_files:
            self.state.remove_selection(v_norm)
            
        if refresh:
            self.window.refresh_list()
            self.window.stat_total.setText(f"Total Files: {len(self.state.video_files)}")

    def bulk_remove_selected(self, paths=None):
        targets = paths if paths is not None else list(self.state.selected_files)
        if not targets: return
        
        for f in targets:
            self.remove_file(f, refresh=False)
            
        self.state.clear_selection()
        self.window.refresh_list()
        self.window.stat_total.setText(f"Total Files: {len(self.state.video_files)}")

    def bulk_change_type(self, paths, new_type):
        for f in paths:
            meta = self.state.metadata_map.get(f)
            if meta and isinstance(meta, dict):
                meta['file_type'] = new_type
                meta['status'] = 'extra' if new_type == 'extra' else 'no_match'
                meta['details'] = None
        
        self.state.clear_selection()
        self.window.refresh_list()

    def bulk_change_extra_type(self, paths, new_extra_type):
        for f in paths:
            meta = self.state.metadata_map.get(f)
            if meta and isinstance(meta, dict):
                meta['extra_type'] = new_extra_type
                meta['status'] = 'extra'
                meta['file_type'] = 'extra'
        
        self.window.refresh_list()
        self.window.update_selection_ui()

    def bulk_change_season(self, paths, new_season):
        ready_to_enrich = []
        for f in paths:
            meta = self.state.metadata_map.get(f)
            if meta and isinstance(meta, dict):
                try:
                    meta['season_file'] = int(new_season)
                    if meta.get('status') == 'one_match':
                        ready_to_enrich.append(meta)
                except ValueError:
                    pass
        
        self.state.clear_selection()
        self.window.refresh_list()
        if ready_to_enrich:
            self.window.trigger_background_enrichment(ready_to_enrich)

    def bulk_change_episode(self, paths, start_ep):
        try:
            num = int(start_ep)
            ready_to_enrich = []
            for f in paths:
                meta = self.state.metadata_map.get(f)
                if meta and isinstance(meta, dict):
                    meta['episode_file'] = num
                    if meta.get('status') == 'one_match':
                        ready_to_enrich.append(meta)
            
            self.state.clear_selection()
            self.window.refresh_list()
            if ready_to_enrich:
                self.window.trigger_background_enrichment(ready_to_enrich)
        except ValueError:
            pass

    def manual_link_parent(self, extra_paths):
        main_files = [p for p, m in self.state.metadata_map.items() if m.get('file_type') != 'extra']
        if not main_files:
            QMessageBox.information(self.window, "Linking", "No main videos found in current list to link to.")
            return

        from ui.dialogs.parent_selection_dialog import ParentSelectionDialog
        dialog = ParentSelectionDialog(self.window, main_files)
        if dialog.exec():
            parent_abs = dialog.selected_parent
            parent_name = os.path.basename(parent_abs)
            
            for f in extra_paths:
                meta = self.state.metadata_map.get(f)
                if meta:
                    meta['extra_parent'] = parent_name
                    meta['file_type'] = 'extra'
                    meta['status'] = 'extra'
            
            self.window.refresh_list()
            self.window.update_selection_ui()

    def bulk_resolve_selected(self, paths, selected_meta):
        ready_to_enrich = []
        for f_path in sorted(list(paths)):
            meta = self.state.metadata_map.get(f_path)
            if not meta: continue
            
            new_meta = meta.copy()
            
            # Handle Multi-Episode selection (list of metadata)
            if isinstance(selected_meta, list):
                # Sort by episode number to be sure
                sorted_items = sorted(selected_meta, key=lambda x: x.get('episode_number', 0))
                
                # Merge titles: "Title 1 & Title 2"
                merged_title = " & ".join([item.get('name', 'Unknown') for item in sorted_items])
                # Merge numbers: [1, 2]
                merged_nums = [item.get('episode_number') for item in sorted_items]
                # Merge IDs for tracking
                merged_ids = [item.get('id') for item in sorted_items]
                
                primary = sorted_items[0]
                details = primary.copy()
                details['name'] = merged_title
                details['episode_number'] = merged_nums
                details['episode_title'] = merged_title
                details['multi_ids'] = merged_ids
                # Ensure series info is kept
                details['series_title'] = primary.get('series_name') or primary.get('series_title')
                
                new_meta.update({
                    'id': primary.get('id'),
                    'file_type': 'episode',
                    'status': 'one_match',
                    'is_manual': True,
                    'details': details
                })
            elif selected_meta.get('is_season_only'):
                # Partial match: Linked to Series & Season, but no specific episode
                new_meta.update({
                    'id': selected_meta.get('id'),
                    'file_type': 'episode',
                    'status': 'multiple_matches',
                    'is_manual': True,
                    'season_file': selected_meta.get('season_number'),
                    'episode_file': 'unknown',
                    'details': selected_meta
                })
            else:
                # Single episode / Movie
                new_meta.update({
                    'id': selected_meta.get('id'),
                    'file_type': 'episode' if 'episode_number' in selected_meta else 'movie',
                    'status': 'one_match',
                    'is_manual': True,
                    'details': selected_meta
                })
            
            # Common overrides
            s_override = (selected_meta[0] if isinstance(selected_meta, list) else selected_meta).get('season_override')
            if s_override:
                try: new_meta['season_file'] = int(s_override)
                except: pass

            from metadata.classifier import classify_result
            # Classify expects 'results' list, we wrap it
            res_wrapper = {'results': [new_meta['details']], 'total_results': 1}
            classify_result(res_wrapper, new_meta, [], self.pipeline.api)
            
            self.state.metadata_map[f_path] = new_meta
            ready_to_enrich.append(new_meta)
        
        self.state.clear_selection()
        self.window.refresh_list()
        if ready_to_enrich:
            self.window.trigger_background_enrichment(ready_to_enrich)

    def open_sequence_wizard(self, paths):
        if len(paths) < 2: return
        
        # Try to find a common series/season to fetch real titles
        ep_titles_map = {} # num -> title
        first_path = paths[0]
        meta = self.state.metadata_map.get(first_path)
        if meta and meta.get('id') and meta.get('season_file') != 'unknown':
            try:
                tv_id = meta.get('id')
                season_num = meta.get('season_file')
                lang = self.state.settings.metadata_language
                season_data = self.pipeline.api.get_from_tmdb_season(tv_id, season_num, language=lang)
                if season_data and 'episodes' in season_data:
                    for ep in season_data['episodes']:
                        ep_titles_map[ep.get('episode_number')] = ep.get('name')
            except Exception as e:
                print(f"Wizard failed to fetch titles: {e}")

        from ui.dialogs.episode_order_dialog import EpisodeOrderDialog
        from PySide6.QtWidgets import QDialog
        
        dialog = EpisodeOrderDialog(self.window, paths, default_start=1, ep_titles=ep_titles_map)
        if dialog.exec() == QDialog.Accepted:
            ordered_paths, start_num = dialog.get_results()
        else:
            return
            
        ready_to_enrich = []
        for i, f in enumerate(ordered_paths):
            meta = self.state.metadata_map.get(f)
            if meta and isinstance(meta, dict):
                meta['episode_file'] = start_num + i
                if meta.get('status') == 'one_match':
                    ready_to_enrich.append(meta)
        
        self.state.clear_selection()
        self.window.refresh_list()
        if ready_to_enrich:
            self.window.trigger_background_enrichment(ready_to_enrich)
