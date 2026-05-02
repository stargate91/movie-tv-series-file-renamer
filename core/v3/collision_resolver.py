import re
import os
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class CollisionResolver:
    """
    Detects and auto-resolves naming collisions BEFORE the execution phase.
    Supports Multi-Part (CD1/CD2) auto-grouping via regex on original paths.
    """
    
    def __init__(self, settings):
        self.s = settings

    def detect_collisions(self, rename_plan):
        """
        Takes a list of proposed renames: [{'file_id': 1, 'original_path': '...', 'proposed_path': '...'}, ...]
        Returns:
            - safe_files: list of files with no collisions.
            - collisions: dict mapping `proposed_path` -> list of files colliding there.
        """
        path_map = defaultdict(list)
        for item in rename_plan:
            # We compare lowercase paths to be safe on Windows
            path_map[item['proposed_path'].lower()].append(item)
            
        safe_files = []
        collisions = {}
        
        for lower_path, items in path_map.items():
            if len(items) == 1:
                safe_files.append(items[0])
            else:
                # Use the exact proposed path from the first item as the key
                exact_path = items[0]['proposed_path']
                collisions[exact_path] = items
                
        return safe_files, collisions

    def auto_resolve_group(self, collision_group):
        """
        Attempts to automatically resolve a group of colliding files.
        Looks for CD, Part, Disc in the original file/folder names ONLY if they collide.
        Returns a list of updated items, or None if it couldn't auto-resolve.
        """
        # Regex to find CD1, Part 2, Disc 3, etc.
        # Matches: CD1, CD 1, Part 01, Disc A
        pattern = re.compile(r'(?i)(?:cd|part|disc|disk)[\s\._-]*([0-9a-d]+)')
        
        resolved_items = []
        found_parts = set()
        
        for item in collision_group:
            orig_path = item['original_path']
            filename = os.path.basename(orig_path)
            parent_dir = os.path.basename(os.path.dirname(orig_path))
            
            # Search filename first, then folder
            match = pattern.search(filename)
            if not match:
                match = pattern.search(parent_dir)
                
            if match:
                part_val = match.group(1).upper()
                found_parts.add(part_val)
                item['_detected_part'] = part_val
            else:
                # If even one file is missing a part identifier, we can't safely auto-resolve
                return None
                
        # Make sure they are actually different parts (e.g. no two CD1s)
        if len(found_parts) != len(collision_group):
            return None
            
        # Apply the settings to format the part suffix
        for item in collision_group:
            part_val = item.pop('_detected_part')
            
            # Formatting based on User Settings (ConfigManager)
            keyword = self.s.multi_part_keyword if self.s.multi_part_keyword != "None" else ""
            
            # Separator mapping
            sep_map = {"space": " ", "dot": ".", "dash": "-", "underscore": "_", "none": ""}
            sep_char = sep_map.get(self.s.multi_part_separator, " ")
            
            # Build suffix (e.g., " - CD1" or ".Part01")
            suffix = ""
            if sep_char:
                if sep_char in ('-', '_'):
                    suffix += f" {sep_char} " # e.g. " - "
                else:
                    suffix += sep_char
                    
            if keyword:
                suffix += f"{keyword}"
                if sep_char != "none": suffix += " "
                
            # TODO: Add Roman Numerals, Zero Padding (01) via self.s.multi_part_style later
            suffix += str(part_val)
            
            # Inject it before the extension
            base, ext = os.path.splitext(item['proposed_path'])
            item['proposed_path'] = f"{base}{suffix}{ext}"
            item['collision_status'] = 'auto_resolved'
            resolved_items.append(item)
            
        return resolved_items
