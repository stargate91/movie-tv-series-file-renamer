import os
import logging

logger = logging.getLogger(__name__)

class CollisionManager:
    """
    Handles detection and resolution of target filename collisions.
    Provides formatting for multi-part media (CD1, Part I, etc.) based on settings.
    """
    def __init__(self, settings):
        self.s = settings
        # path -> manual order (1, 2, 3...)
        self.manual_orders = {}

    def set_manual_order(self, file_path, order):
        """Sets the index for a file within a multi-part group."""
        self.manual_orders[file_path] = order

    def get_suffix_string(self, number):
        """
        Builds the part string (e.g., 'Part 01', 'CD I') based on settings.
        Does NOT include the separator here, just the keyword and the formatted number.
        """
        keyword = self.s.multi_part_keyword if self.s.multi_part_keyword != "None" else ""
        style = self.s.multi_part_style
        
        # 1. Format the number/letter
        formatted_num = str(number)
        if style == "zero_padded":
            formatted_num = f"{number:02}"
        elif style == "roman":
            formatted_num = self._int_to_roman(number)
        elif style == "letter":
            formatted_num = chr(64 + number) if 1 <= number <= 26 else str(number)

        # 2. Combine with keyword
        sep_between = " " if keyword and formatted_num else ""
        return f"{keyword}{sep_between}{formatted_num}"

    def resolve_collision(self, base_name, number):
        """
        Combines the base filename with the formatted multi-part string.
        Handles separators and prefix/suffix positioning.
        """
        if number is None or number < 1:
            return base_name

        part_str = self.get_suffix_string(number)
        sep_char = self._get_separator_char()
        
        if self.s.multi_part_position == "prefix":
            return f"{part_str}{sep_char}{base_name}"
        else:
            return f"{base_name}{sep_char}{part_str}"

    def _get_separator_char(self):
        mapping = {
            "space": " ",
            "dot": ".",
            "dash": " - ",
            "underscore": "_",
            "none": ""
        }
        return mapping.get(self.s.multi_part_separator, " ")

    def _int_to_roman(self, n):
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
        roman_num = ''
        i = 0
        while n > 0:
            for _ in range(n // val[i]):
                roman_num += syb[i]
                n -= val[i]
            i += 1
        return roman_num

    def find_collision_groups(self, tasks):
        """
        Groups RenamingTask objects that share the same new_path.
        Returns a dict: { normalized_path: [task1, task2, ...] }
        """
        groups = {}
        for task in tasks:
            if not task.new_path: continue
            norm = os.path.abspath(task.new_path)
            if norm not in groups:
                groups[norm] = []
            groups[norm].append(task)
            
        # Only return groups with more than one item
        return {p: t for p, t in groups.items() if len(t) > 1}
