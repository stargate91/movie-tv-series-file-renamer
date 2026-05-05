import os

class AssetLinker:
    """
    Handles the logic for finding the most likely parent video for an asset (subtitle, extra, etc.).
    """
    def find_best_parent(self, asset_path, video_paths):
        """Legacy wrapper for single file lookups."""
        video_index = self._build_index(video_paths)
        return self._find_in_index(asset_path, video_index)

    def link_batch(self, asset_ids, video_ids):
        """Efficiently links a batch of assets using a pre-built directory index."""
        video_index = self._build_index(list(video_ids.keys()))
        results = []
        for path, category, db_id in asset_ids:
            parent_path = self._find_in_index(path, video_index)
            if parent_path:
                results.append((db_id, video_ids[parent_path]))
        return results

    def _build_index(self, video_paths):
        """Groups video files by directory and pre-fetches sizes."""
        index = {}
        for v in video_paths:
            d = os.path.normpath(os.path.dirname(v)).lower()
            if d not in index: index[d] = []
            try: size = os.path.getsize(v)
            except: size = 0
            index[d].append({'path': v, 'name': os.path.splitext(os.path.basename(v))[0].lower(), 'size': size})
        return index

    def _find_in_index(self, asset_path, video_index):
        asset_dir = os.path.normpath(os.path.dirname(asset_path)).lower()
        asset_name = os.path.splitext(os.path.basename(asset_path))[0].lower()
        target = asset_name.replace('sample', '').replace('trailer', '').replace('bonus', '').strip(' -._')
        
        current_lookup = asset_dir
        for _ in range(3):
            folder_vids = video_index.get(current_lookup, [])
            if folder_vids:
                # 1. Name match
                for v in folder_vids:
                    if target and (target in v['name'] or v['name'] in target):
                        return v['path']
                
                # 2. Heuristics (Largest)
                if len(folder_vids) == 1: return folder_vids[0]['path']
                
                # Sort by pre-fetched size
                folder_vids.sort(key=lambda x: x['size'], reverse=True)
                return folder_vids[0]['path']

            # Move up
            new_dir = os.path.dirname(current_lookup)
            if new_dir == current_lookup or not new_dir: break
            current_lookup = new_dir
            
        return None
