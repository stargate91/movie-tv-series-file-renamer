import os
from PySide6.QtWidgets import QLabel, QWidget, QHBoxLayout
from PySide6.QtCore import Qt

from ui.widgets.group_headers import SeriesHeader, SeasonHeader, CollisionGroupHeader
from ui.components.movie_card import MovieCard
from core.collision_manager import CollisionManager
from core.renamer import get_preview_name

class MediaListManager:
    """
    Handles ranking, grouping, and lazy loading (chunking) of media items in the UI.
    """
    def __init__(self, window, state, pipeline, results_layout, scroll_area):
        self.window = window
        self.state = state
        self.pipeline = pipeline
        self.results_layout = results_layout
        self.scroll_area = scroll_area
        self.collision_mgr = CollisionManager(self.pipeline.s)
        
        self.display_items = []  # Flat list of (type, data, extra) tasks
        self.current_loaded_index = 0
        self.chunk_size = 25
        self.filter_mode = 'all'
        self.search_query = ""

    def clear_results(self):
        """Clears all widgets from the results layout."""
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.current_loaded_index = 0
        self.display_items = []

    def set_filter(self, mode):
        self.filter_mode = mode
        self.refresh()

    def apply_search_filter(self, text):
        self.search_query = text.strip().lower()
        self.refresh()

    def get_rank(self, vid_path):
        """Determines the priority of a file for UI ordering."""
        if not vid_path:
            return 4
        try:
            norm_p = os.path.abspath(os.path.normpath(vid_path))
        except:
            return 4
            
        meta = self.state.metadata_map.get(norm_p)
        if not meta:
            return 4
        
        f_type = meta.get('file_type')
        status = meta.get('status', 'pending')
        is_manual = meta.get('is_manual', False)
        
        if f_type == 'extra' or status == 'extra': return 6
        if status == 'multiple_matches': return 0
        if status == 'no_match': return 1
        if is_manual: return 2
        if status == 'one_match': return 3
        if status == 'complex_match': return 5
        return 4

    def refresh(self):
        """Builds the display task list based on current state and starts loading."""
        self.clear_results()
        
        if not self.pipeline or not self.state.video_files:
            self._show_empty_state()
            self._update_pill_counts()
            return

        # 1. Group by Rank
        norm_files = [os.path.abspath(os.path.normpath(f)) for f in self.state.video_files if f]
        by_rank = {i: [] for i in range(7)}
        for f in norm_files:
            if f:
                by_rank[self.get_rank(f)].append(f)

        # 2. Create Tasks with Filtering
        self.display_items = []
        matched_count = 0
        has_results = len(self.state.collected_results) > 0

        for rank in range(7):
            vids = by_rank[rank]
            if not vids: continue

            # Apply Filter to vids
            filtered_vids = self._apply_filter_to_vids(vids, rank)
            if not filtered_vids: continue

            # Add Section Header
            header_text = self._get_header_text(rank, has_results)
            self.display_items.append(('header', header_text, rank == 6))

            # --- Collision Grouping Logic ---
            # Group files by their predicted target name to detect multi-part media
            target_groups = {} # target_name -> [v_paths]
            ungrouped_vids = []
            
            for v_path in filtered_vids:
                meta = self.state.metadata_map.get(v_path, {})
                status = meta.get('status')
                
                # Only group things that have a match or are extras
                if status in ['one_match', 'complex_match', 'extra']:
                    t_name = get_preview_name(v_path, meta, self.pipeline.s, self.state.metadata_map)
                    if t_name not in target_groups:
                        target_groups[t_name] = []
                    target_groups[t_name].append(v_path)
                else:
                    ungrouped_vids.append(v_path)

            # Process groups and single items
            for t_name, members in target_groups.items():
                if len(members) > 1:
                    # It's a collision group!
                    self.display_items.append(('group_header', t_name, None))
                    for i, v_path in enumerate(members, 1):
                        badge = self.collision_mgr.get_suffix_string(i)
                        self.display_items.append(('group_card', v_path, (i, badge)))
                else:
                    ungrouped_vids.append(members[0])

            # Process leftover ungrouped vids (original series/flat logic)
            if not ungrouped_vids: continue
            
            # Flat vs Grouped logic for non-collision vids
            if not has_results or rank == 6:
                for f in ungrouped_vids:
                    self.display_items.append(('card', f, False))
                continue

            movies, series_groups = self._group_by_series(ungrouped_vids)
            for m in movies:
                self.display_items.append(('card', m, False))
                if rank == 3: matched_count += 1

            for s_title, s_data in series_groups.items():
                all_files = [f for sn in s_data['seasons'] for f in s_data['seasons'][sn]]
                self.display_items.append(('series_header', (s_title, s_data['poster'], all_files, rank == 5), False))
                
                for sn in sorted(s_data['seasons'].keys()):
                    eps = s_data['seasons'][sn]
                    meta = self.state.metadata_map.get(eps[0])
                    det = meta.get('details') if meta and isinstance(meta.get('details'), dict) else {}
                    s_poster = det.get('season_poster_path')
                    s_range = det.get('season_year_range', '')
                    self.display_items.append(('season_header', (sn, s_poster, s_range, eps, rank == 5), False))
                    
                    for ep in eps:
                        self.display_items.append(('card', ep, True))
                        if rank == 3: matched_count += 1

        self.window.stat_matches.setText(f"Matched: {matched_count}")
        self._update_pill_counts()
        self.load_next_chunk()

    def _apply_filter_to_vids(self, vids, rank):
        # 1. Category Filter
        category_filtered = []
        if self.filter_mode == 'all':
            category_filtered = vids
        elif self.filter_mode == 'pending':
            category_filtered = vids if rank == 4 else []
        elif self.filter_mode == 'review':
            category_filtered = vids if rank in [0, 1, 5] else []
        elif self.filter_mode == 'movies':
            category_filtered = [v for v in vids if self.state.metadata_map.get(v, {}).get('file_type') == 'movie']
        elif self.filter_mode == 'series':
            category_filtered = [v for v in vids if self.state.metadata_map.get(v, {}).get('file_type') == 'episode']
        elif self.filter_mode == 'extras':
            category_filtered = vids if rank == 6 else []
        else:
            category_filtered = vids
            
        # 2. Search Filter
        if not self.search_query:
            return category_filtered
            
        search_filtered = []
        for v in category_filtered:
            filename = os.path.basename(v).lower()
            meta = self.state.metadata_map.get(v, {})
            details = meta.get('details') if isinstance(meta.get('details'), dict) else {}
            recognized_title = (details.get('title') or details.get('name') or details.get('series_title') or "").lower()
            
            if self.search_query in filename or self.search_query in recognized_title:
                search_filtered.append(v)
                
        return search_filtered

    def _update_pill_counts(self):
        """Notifies the window to update counts on pills."""
        if hasattr(self.window, 'update_pill_counts'):
            counts = {
                'all': len(self.state.video_files),
                'pending': 0,
                'review': 0,
                'movies': 0,
                'series': 0,
                'extras': 0
            }
            for f in self.state.video_files:
                if not f: continue
                rank = self.get_rank(f)
                if rank == 4: counts['pending'] += 1
                if rank in [0, 1, 5]: counts['review'] += 1
                if rank == 6: counts['extras'] += 1
                
                meta = self.state.metadata_map.get(f, {})
                f_type = meta.get('file_type')
                if f_type == 'movie' and rank != 6: counts['movies'] += 1
                if f_type == 'episode' and rank != 6: counts['series'] += 1
                
            self.window.update_pill_counts(counts)

    def load_next_chunk(self):
        """Appends the next chunk of widgets to the layout."""
        if self.current_loaded_index >= len(self.display_items):
            return
            
        end_idx = min(self.current_loaded_index + self.chunk_size, len(self.display_items))
        
        for i in range(self.current_loaded_index, end_idx):
            item_type, data, extra = self.display_items[i]
            self._create_widget(item_type, data, extra)
                    
        self.current_loaded_index = end_idx

    def handle_scroll(self, value):
        """Triggers next chunk loading when near the bottom."""
        bar = self.scroll_area.verticalScrollBar()
        if value > bar.maximum() - 250:
            self.load_next_chunk()

    def _show_empty_state(self):
        msg = QLabel("\n\n\n📦\nDrag & Drop Files or Folders Here\n<small>or use the 'Select Folder' button</small>")
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("color: #8b949e; font-size: 20px; font-weight: bold;")
        self.results_layout.addWidget(msg)

    def _get_header_text(self, rank, has_results):
        return {
            0: "⚠️ AMBIGUOUS MATCHES (Multiple choices found)",
            1: "❌ NO MATCHES FOUND (Manual search required)",
            2: "✨ RESOLVED BY YOU",
            3: "✅ AUTO-MATCHED",
            4: "📦 MAIN VIDEOS TO PROCESS" if not has_results else "📂 UNRECOGNIZED FILES",
            5: "🚨 COMPLEX CASES (Manual review required)",
            6: "📁 EXTRAS / SAMPLES (Will be skipped or moved to Extras folder)"
        }[rank]

    def _group_by_series(self, vids):
        movies = []
        series_groups = {}
        for v in vids:
            meta = self.state.metadata_map.get(v)
            if not isinstance(meta, dict): meta = {}
            det = meta.get('details') if meta else {}
            if not isinstance(det, dict): det = {}
            
            is_ep = meta and (meta.get('file_type') == 'episode' or meta.get('extras', {}).get('season') is not None)
            
            if is_ep:
                status = meta.get('status')
                extras = meta.get('extras', {})
                if status == 'one_match':
                    name = det.get('series_title') or det.get('series_name') or det.get('name') or extras.get('title') or "Unknown Series"
                else:
                    name = "Unknown Series"
                
                sn = det.get('season_number') or extras.get('season') or 1
                if name not in series_groups:
                    is_generic = name in ["Unknown Series", "Unknown Collection", "Unknown Saga"]
                    poster = (det.get('series_poster_path') or det.get('poster_path')) if not is_generic else None
                    series_groups[name] = {"poster": poster, "seasons": {}}
                if sn not in series_groups[name]["seasons"]:
                    series_groups[name]["seasons"][sn] = []
                series_groups[name]["seasons"][sn].append(v)
            else:
                movies.append(v)
        return movies, series_groups

    def _create_widget(self, item_type, data, extra):
        if item_type == 'header':
            header = QLabel(data)
            color = "#f85149" if extra else "#6b7280"
            header.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 11px; margin-top: 30px; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px;")
            self.results_layout.addWidget(header)
            
        elif item_type == 'group_header':
            header = CollisionGroupHeader(data)
            self.results_layout.addWidget(header)
            
        elif item_type == 'group_card':
            num, badge = extra
            card = MovieCard(data, self.state.metadata_map.get(data), self.pipeline, 
                             self.window.on_card_click, self.window.on_card_edit, self.window.on_card_remove)
            card.set_group_mode(num, badge)
            self.results_layout.addWidget(card)
            
        elif item_type == 'series_header':
            s_title, poster, files, is_complex = data
            header = SeriesHeader(
                s_title, poster,
                on_edit=(lambda _, f=files, t=s_title: self.window.select_files_for_inspector(f, t)) if not is_complex else None
            )
            self.results_layout.addWidget(header)
            
        elif item_type == 'season_header':
            sn, poster, year_range, eps, is_complex = data
            header = SeasonHeader(
                sn, poster, year_range,
                on_edit=(lambda _, f=eps, s=sn: self.window.select_files_for_inspector(f, season=s)) if not is_complex else None
            )
            self.results_layout.addWidget(header)
            
        elif item_type == 'card':
            file_path = data
            meta = self.state.metadata_map.get(file_path)
            card = MovieCard(
                file_path, meta, self.pipeline,
                on_click=lambda _, p=file_path, m=meta: self.window.open_selection(p, m),
                on_edit=lambda _, p=file_path, m=meta: self.window.open_single_edit_popup(p, m),
                on_remove=lambda _, p=file_path: self.window.ctrl.remove_file(p)
            )
            card.selection_changed.connect(lambda s, p=file_path: self.window.update_selection(p, s))
            if file_path in self.state.selected_files:
                if self.state.is_multi_select_mode:
                    card.checkbox.setChecked(True)
                else:
                    card.set_active(True)
            
            if extra: # Indented
                container = QWidget()
                inner_layout = QHBoxLayout(container)
                inner_layout.setContentsMargins(60, 0, 0, 0)
                inner_layout.addWidget(card)
                self.results_layout.addWidget(container)
            else:
                self.results_layout.addWidget(card)
