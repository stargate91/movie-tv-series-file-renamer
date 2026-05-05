import unittest
from unittest.mock import MagicMock
from core.engine.collision_resolver import CollisionResolver

class TestCollisionResolverExtreme(unittest.TestCase):
    def setUp(self):
        # Mocking user settings
        self.mock_settings = MagicMock()
        self.mock_settings.multi_part_style = "number"
        self.mock_settings.multi_part_keyword = "CD"
        self.mock_settings.multi_part_separator = "dash"
        self.mock_settings.multi_part_position = "suffix"
        
        self.resolver = CollisionResolver(self.mock_settings)

    def test_detect_collisions_case_insensitivity_and_grouping(self):
        """
        Biztosítja, hogy a detektálás Windows-biztos (case-insensitive),
        és pontosan csoportosítja az ütközéseket.
        """
        plan = [
            {'file_id': 1, 'proposed_path': '/movies/Avatar.mp4'},
            {'file_id': 2, 'proposed_path': '/Movies/avatar.mp4'}, # Ütközik az 1-essel
            {'file_id': 3, 'proposed_path': '/movies/Matrix.mp4'},
            {'file_id': 4, 'proposed_path': '/movies/matrix.MP4'}, # Ütközik a 3-assal
            {'file_id': 5, 'proposed_path': '/movies/Inception.mp4'} # Nincs ütközés
        ]

        safe, collisions = self.resolver.detect_collisions(plan)

        self.assertEqual(len(safe), 1)
        self.assertEqual(safe[0]['file_id'], 5)

        self.assertEqual(len(collisions), 2)
        # Az első tétel pontos útvonala lesz a kulcs
        self.assertIn('/movies/Avatar.mp4', collisions)
        self.assertIn('/movies/Matrix.mp4', collisions)

        self.assertEqual(len(collisions['/movies/Avatar.mp4']), 2)
        self.assertEqual(len(collisions['/movies/Matrix.mp4']), 2)

    def test_auto_resolve_regex_and_fallback(self):
        """
        Teszteli a CD/Part detektálást filenévből és mappanévből,
        és hogy elbukik-e, ha duplikált vagy hiányzó part van.
        """
        # Siker eset: filenévből és mappanévből vegyesen
        group_success = [
            {'original_path': '/downloads/Matrix CD 1/video.mp4', 'proposed_path': '/movies/Matrix.mp4'},
            {'original_path': '/downloads/Matrix/video_part02.mp4', 'proposed_path': '/movies/Matrix.mp4'}
        ]
        
        resolved = self.resolver.auto_resolve_group(group_success)
        self.assertIsNotNone(resolved)
        self.assertTrue(resolved[0]['proposed_path'].endswith(' - CD 1.mp4'))
        self.assertTrue(resolved[1]['proposed_path'].endswith(' - CD 2.mp4'))

        # Bukás eset: Két CD1
        group_fail_duplicate = [
            {'original_path': '/d/cd1.mp4', 'proposed_path': '/movies/M.mp4'},
            {'original_path': '/d/CD 1.mp4', 'proposed_path': '/movies/M.mp4'}
        ]
        self.assertIsNone(self.resolver.auto_resolve_group(group_fail_duplicate))

        # Bukás eset: Egyik fájlban sincs azonosító
        group_fail_missing = [
            {'original_path': '/d/cd1.mp4', 'proposed_path': '/movies/M.mp4'},
            {'original_path': '/d/unknown.mp4', 'proposed_path': '/movies/M.mp4'}
        ]
        self.assertIsNone(self.resolver.auto_resolve_group(group_fail_missing))

    def test_apply_part_formatting_styles_and_positions(self):
        """
        Szigorú teszt a formázási beállítások teljes palettájára 
        (Roman, zero-padded, prefix, suffix, különböző separatorok).
        """
        group = [
            {'_detected_part': '1', 'proposed_path': '/m/Film.mp4'},
            {'_detected_part': '2', 'proposed_path': '/m/Film.mp4'}
        ]

        # Teszt 1: Prefix, Nincs separator, Zero-padded
        self.mock_settings.multi_part_position = "prefix"
        self.mock_settings.multi_part_separator = "none"
        self.mock_settings.multi_part_keyword = "Part"
        self.mock_settings.multi_part_style = "zero_padded"
        
        # Másolatot küldünk be, mert a függvény törli a _detected_part-ot
        res1 = self.resolver._apply_part_formatting([dict(g) for g in group])
        self.assertEqual(res1[0]['proposed_path'], '/m/Part01 Film.mp4')
        self.assertEqual(res1[1]['proposed_path'], '/m/Part02 Film.mp4')

        # Teszt 2: Suffix, Dot separator, Roman numerals, Nincs keyword
        self.mock_settings.multi_part_position = "suffix"
        self.mock_settings.multi_part_separator = "dot"
        self.mock_settings.multi_part_keyword = "None" # vagy ""
        self.mock_settings.multi_part_style = "roman"

        res2 = self.resolver._apply_part_formatting([dict(g) for g in group])
        self.assertEqual(res2[0]['proposed_path'], '/m/Film.I.mp4')
        self.assertEqual(res2[1]['proposed_path'], '/m/Film.II.mp4')
        
    def test_roman_numeral_conversion_edge_cases(self):
        """
        A római szám konvertáló beépített logikájának ellenőrzése.
        """
        self.assertEqual(self.resolver._int_to_roman(4), "IV")
        self.assertEqual(self.resolver._int_to_roman(9), "IX")
        self.assertEqual(self.resolver._int_to_roman(42), "XLII")
        self.assertEqual(self.resolver._int_to_roman(1999), "MCMXCIX")
        self.assertEqual(self.resolver._int_to_roman(0), "0") # határon kívül, visszaadja a számot stringként
        self.assertEqual(self.resolver._int_to_roman(4000), "4000")

if __name__ == '__main__':
    unittest.main()
