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
        """Groups video files by directory and pre-fetches sizes with strict normalization."""
        index = {}
        for v in video_paths:
            # Force absolute path, consistent separators and lower case for the key
            v_norm = os.path.normpath(os.path.abspath(v))
            d = os.path.dirname(v_norm).lower()
            if d not in index: index[d] = []
            try: 
                size = os.path.getsize(v_norm)
            except: 
                size = 0
            index[d].append({
                'path': v_norm, 
                'name': os.path.splitext(os.path.basename(v_norm))[0].lower(), 
                'size': size
            })
        return index

    def _find_in_index(self, asset_path, video_index):
        # Normalize paths for cross-platform and case-insensitive comparison
        asset_path = os.path.normpath(os.path.abspath(asset_path))
        asset_dir = os.path.dirname(asset_path).lower()
        asset_name = os.path.splitext(os.path.basename(asset_path))[0].lower()
        
        # Clean target string (remove common extra/sample keywords)
        target = asset_name
        for kw in ['sample', 'trailer', 'bonus', 'minta', 'extra']:
            target = target.replace(kw, '')
        target = target.strip(' -._')
        
        current_lookup = asset_dir
        for _ in range(3):
            folder_vids = video_index.get(current_lookup, [])
            if folder_vids:
                # 1. Name match (prioritize specific naming)
                if target and len(target) > 1:
                    for v in folder_vids:
                        v_name = v['name']
                        if target in v_name or v_name in target:
                            return v['path']
                
                # 2. Heuristics (Largest file in directory)
                # Filter out ourself (using normalized path)
                candidates = [v for v in folder_vids if v['path'].lower() != asset_path.lower()]
                if candidates:
                    # Sort by size to pick the most likely "Main Feature"
                    candidates.sort(key=lambda x: x['size'], reverse=True)
                    return candidates[0]['path']

            # Move up to parent directory
            new_dir = os.path.dirname(current_lookup)
            if new_dir == current_lookup or not new_dir or len(new_dir) < 3: break
            current_lookup = new_dir

        return None
