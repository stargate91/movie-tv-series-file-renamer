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
            
        return self._apply_part_formatting(collision_group)

    def force_resolve_group(self, collision_group):
        """
        Forces a group of items into multi-part formatting (Part 1, Part 2, etc.)
        regardless of their original filenames. Uses the order provided.
        """
        for i, item in enumerate(collision_group):
            item['_detected_part'] = str(i + 1)
            
        return self._apply_part_formatting(collision_group)

    def _apply_part_formatting(self, collision_group):
        resolved_items = []
        # Apply the settings to format the part string
        for item in collision_group:
            part_val = item.pop('_detected_part')
            formatted_val = self._format_part_val(part_val, self.s.multi_part_style)
            
            # Formatting based on User Settings
            keyword = self.s.multi_part_keyword if self.s.multi_part_keyword not in ("None", "") else ""
            
            # Separator mapping
            sep_map = {"space": " ", "dot": ".", "dash": "-", "underscore": "_", "none": ""}
            sep_char = sep_map.get(self.s.multi_part_separator, " ")
            
            # Build part string (e.g., " - CD1" or ".Part01")
            part_str = ""
            if sep_char:
                if sep_char in ('-', '_'):
                    part_str += f" {sep_char} " # e.g. " - "
                else:
                    part_str += sep_char
                    
            if keyword:
                part_str += f"{keyword}"
                if sep_char: part_str += sep_char
                
            part_str += formatted_val
            
            # Position Handling
            base, ext = os.path.splitext(item['proposed_path'])
            path_parts = os.path.split(base) # [dir, filename_base]
            
            if self.s.multi_part_position == "prefix":
                # e.g. "CD1 - Movie Title"
                new_base = f"{part_str}{sep_char if sep_char else ' '}{path_parts[1]}"
                item['proposed_path'] = os.path.join(path_parts[0], f"{new_base}{ext}")
            else:
                # Suffix: "Movie Title - CD1"
                item['proposed_path'] = f"{base}{part_str}{ext}"
                
            item['status'] = 'manual_resolved'
            item['collision_status'] = 'manual_resolved'
            resolved_items.append(item)
            
        return resolved_items

    def _format_part_val(self, val, style):
        try:
            num = int(val)
            if style == "zero_padded":
                return f"{num:02d}"
            if style == "roman":
                return self._int_to_roman(num)
            if style == "letter":
                return chr(64 + num) if 1 <= num <= 26 else str(num)
            return str(num)
        except:
            # val is likely 'A', 'B', etc.
            return str(val).upper()

    def _int_to_roman(self, n):
        # Basic roman numeral conversion
        if not (0 < n < 4000): return str(n)
        m = ["", "M", "MM", "MMM"]
        c = ["", "C", "CC", "CCC", "CD", "D", "DC", "DCC", "DCCC", "CM"]
        x = ["", "X", "XX", "XXX", "XL", "L", "LX", "LXX", "LXXX", "XC"]
        i = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
        return m[n // 1000] + c[(n % 1000) // 100] + x[(n % 100) // 10] + i[n % 10]
