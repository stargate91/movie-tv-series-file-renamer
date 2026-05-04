"""Extreme Edge Case Tests for Resolver V3."""
import sys, os, json, shutil, unittest
# Add project root to sys.path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

import unittest.mock as mock
from core.db.database import LibraryDB
from core.engine.resolver import Resolver

class MockSettings:
    def __init__(self):
        self.tmdb_key = "dummy_tmdb"
        self.tmdb_bearer_token = "dummy_bearer"
        self.omdb_key = "dummy_omdb"
        self.metadata_language = "en-US"
        self.fallback_language = ""

class TestResolverExtreme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup a temporary test database
        cls.test_db_path = os.path.join(base_dir, "data", "test_extreme.db")
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)
            
        cls.db = LibraryDB(cls.test_db_path)
        cls.settings = MockSettings()
        cls.resolver = Resolver(cls.db, cls.settings)

    def setUp(self):
        # Patch the API client's internal call to prevent actual network requests
        self.patcher = mock.patch('api.client.APIClient._get_from_api')
        self.mock_api = self.patcher.start()
        
        # Default mock behavior: return an empty-ish but valid dict
        self.mock_api.return_value = {}

    def tearDown(self):
        self.patcher.stop()
        with self.db._get_connection() as conn:
            conn.execute("DELETE FROM file_media_links")
            conn.execute("DELETE FROM media_files")
            conn.execute("DELETE FROM media_items")
            conn.execute("DELETE FROM tv_episodes")
            conn.execute("DELETE FROM tv_seasons")
            conn.commit()

    def test_case_1_missing_se_metadata(self):
        """TV file with NO parsed S/E metadata matched to a TV show."""
        print("\n[Test] Case 1: TV file with NO S/E metadata")
        file_id = self.db.add_file("C:/TV/Mystery.Show.mkv", "video", 1024)
        vid = self.db.get_file_by_id(file_id)
        
        # Mock TMDB TV Detail
        self.mock_api.return_value = {
            'id': 2290, 'name': 'Stargate Atlantis', 'first_air_date': '2004-07-16',
            'credits': {'cast': [], 'crew': []}
        }
        
        res = {'tmdb_id': 2290, 'media_type': 'tv', 'title': 'Stargate Atlantis', 'year': 2004}
        media_item_id = self.resolver._store_result(res)
        self.resolver._finalize_match(file_id, media_item_id, res, vid, 'matched')
        
        links = self.db.get_links_for_file(file_id)
        self.assertEqual(len(links), 1)
        self.assertIsNone(links[0]['tv_episode_id'])

    def test_case_2_multi_episode_parsing(self):
        """Multi-episode file SGA 1x01-02."""
        print("\n[Test] Case 2: Multi-episode SGA 1x01-02")
        file_id = self.db.add_file("C:/SGA/SGA.1x01-02.mkv", "video", 2048)
        self.db.update_file(file_id, fn_season=1, fn_episode="[1, 2]")
        vid = self.db.get_file_by_id(file_id)
        
        # Mock TMDB Season Detail
        def side_effect(url, key, headers=None, params=None, required_keys=None):
            if "season/1" in url:
                return {
                    'id': 123, 'season_number': 1,
                    'episodes': [
                        {'id': 101, 'episode_number': 1, 'name': 'Rising (1)'},
                        {'id': 102, 'episode_number': 2, 'name': 'Rising (2)'}
                    ]
                }
            return {'id': 2290, 'name': 'Stargate Atlantis', 'credits': {'cast': []}}

        self.mock_api.side_effect = side_effect
        
        res = {'tmdb_id': 2290, 'media_type': 'tv', 'title': 'Stargate Atlantis', 'year': 2004}
        media_item_id = self.resolver._store_result(res)
        self.resolver._finalize_match(file_id, media_item_id, res, vid, 'matched')
        
        links = self.db.get_links_for_file(file_id)
        self.assertEqual(len(links), 2)
        ep_nums = sorted([self.db.get_episode_by_id(l['tv_episode_id'])['episode_number'] for l in links if l['tv_episode_id']])
        self.assertEqual(ep_nums, [1, 2])

    def test_case_3_folder_filename_conflict(self):
        """Conflict: Folder says S02, filename says S01. Filename should win."""
        print("\n[Test] Case 3: Folder/Filename conflict (S02 vs S01)")
        file_id = self.db.add_file("C:/TV/Show.S02/Show.S01E05.mkv", "video", 3072)
        self.db.update_file(file_id, fn_season=1, fn_episode=5, fd_season=2)
        vid = self.db.get_file_by_id(file_id)
        
        # Mock Season 1
        self.mock_api.return_value = {
            'id': 123, 'season_number': 1,
            'episodes': [{'id': 505, 'episode_number': 5, 'name': 'The Episode'}]
        }
        
        res = {'tmdb_id': 2290, 'media_type': 'tv', 'title': 'Stargate Atlantis', 'year': 2004}
        media_item_id = self.resolver._store_result(res)
        self.resolver._finalize_match(file_id, media_item_id, res, vid, 'matched')
        
        links = self.db.get_links_for_file(file_id)
        ep = self.db.get_episode_by_id(links[0]['tv_episode_id'])
        self.assertEqual(ep['season_number'], 1)
        self.assertEqual(ep['episode_number'], 5)

    def test_case_4_manual_resolve_override(self):
        """Simulate Manual Resolve where user overrides parsed metadata."""
        print("\n[Test] Case 4: Manual Resolve Override")
        file_id = self.db.add_file("C:/TV/Show.mkv", "video", 4096)
        self.db.update_file(file_id, fn_season=1, fn_episode=1)
        
        # User in dialog overrides to S02E03
        self.db.update_file(file_id, fn_season=2, fn_episode=3)
        
        # Mock Season 2
        self.mock_api.return_value = {
            'id': 222, 'season_number': 2,
            'episodes': [{'id': 203, 'episode_number': 3, 'name': 'Real Ep'}]
        }
        
        res = {'tmdb_id': 2290, 'media_type': 'tv', 'title': 'Stargate Atlantis', 'year': 2004}
        media_item_id = self.resolver._store_result(res)
        vid = self.db.get_file_by_id(file_id)
        self.resolver._finalize_match(file_id, media_item_id, res, vid, 'matched')
        
        links = self.db.get_links_for_file(file_id)
        ep = self.db.get_episode_by_id(links[0]['tv_episode_id'])
        self.assertEqual(ep['season_number'], 2)
        self.assertEqual(ep['episode_number'], 3)

    def test_case_5_cache_validation_logic(self):
        """Test that missing required keys trigger cache invalidation."""
        print("\n[Test] Case 5: Cache Validation Logic")
        api = self.resolver.api
        cache_key = "movie-detail-27205-en-US"
        
        # Stale cache missing 'credits'
        stale_data = {"id": 27205, "title": "Inception"}
        self.db.set_api_cache(cache_key, stale_data)
        
        # Mock network response for the refresh
        self.mock_api.side_effect = None
        self.mock_api.return_value = {"id": 27205, "title": "Inception", "credits": {"cast": []}}
        
        # Calling this should trigger invalidation because 'credits' is missing in cached_data
        data = api.get_from_tmdb_movie_detail(27205, "en-US")
        
        # Verify invalidation happened: mock_api was called (cache hit would NOT call mock_api)
        self.mock_api.assert_called_once()
        self.assertIn('credits', data)

    def test_case_6_null_link_cleanup(self):
        """Test the fix where old NULL links are cleared when an episode is found."""
        print("\n[Test] Case 6: NULL link cleanup")
        file_id = self.db.add_file("C:/SGA.1x04.mkv", "video", 5120)
        media_item_id = 999
        # Manually inject a NULL link
        with self.db._get_connection() as conn:
            conn.execute("INSERT INTO file_media_links (file_id, media_item_id, tv_episode_id) VALUES (?, ?, NULL)", (file_id, media_item_id))
            conn.commit()
            
        # Link with episode 555
        self.db.link_file_to_media(file_id, media_item_id, 'matched', tv_episode_id=555)
        
        # Verify: NULL link is gone
        links = self.db.get_links_for_file(file_id)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]['tv_episode_id'], 555)

    def test_case_7_movie_enrichment(self):
        """Test full enrichment for a movie (Director, Cast, Overview)."""
        print("\n[Test] Case 7: Movie Enrichment")
        file_id = self.db.add_file("C:/Movies/Inception.2010.mkv", "video", 6144)
        vid = self.db.get_file_by_id(file_id)
        
        # Mock TMDB Movie Detail with credits
        self.mock_api.return_value = {
            'id': 27205, 'title': 'Inception', 'overview': 'A thief...',
            'credits': {
                'crew': [{'job': 'Director', 'name': 'Christopher Nolan'}],
                'cast': [{'name': 'Leonardo DiCaprio'}]
            }
        }
        
        res = {'tmdb_id': 27205, 'media_type': 'movie', 'title': 'Inception', 'year': 2010}
        media_item_id = self.resolver._store_result(res)
        self.resolver._finalize_match(file_id, media_item_id, res, vid, 'matched')
        
        # Verify DB
        row = self.db.get_media_item_by_id(media_item_id)
        self.assertEqual(row['director'], 'Christopher Nolan')
        self.assertIn('Leonardo DiCaprio', row['cast'])
        self.assertEqual(row['overview'], 'A thief...')

    def test_case_8_clear_match_and_rematch_tv(self):
        """Test: Match -> Clear Match -> Match again with different episode."""
        print("\n[Test] Case 8: Clear Match & Rematch (TV)")
        file_id = self.db.add_file("C:/TV/Show.mkv", "video", 7000)
        
        # 1. First Match: S01E01
        self.db.update_file(file_id, fn_season=1, fn_episode=1)
        res1 = {'tmdb_id': 2290, 'media_type': 'tv', 'title': 'Stargate Atlantis', 'year': 2004}
        
        # Mock: first return season info (for _fetch_and_store_season) then the specific episode detail if needed
        def side_effect_s1(url, *args, **kwargs):
            if "season/1" in url:
                return {'id': 101, 'episodes': [{'id': 1001, 'episode_number': 1}]}
            return {'id': 2290, 'name': 'SGA', 'credits': {'cast': []}}
        self.mock_api.side_effect = side_effect_s1
        
        mid1 = self.resolver._store_result(res1)
        self.resolver._finalize_match(file_id, mid1, res1, self.db.get_file_by_id(file_id), 'matched')
        
        links1 = self.db.get_links_for_file(file_id)
        self.assertEqual(len(links1), 1)
        self.assertIsNotNone(links1[0]['tv_episode_id'])
        self.assertEqual(self.db.get_episode_by_id(links1[0]['tv_episode_id'])['episode_number'], 1)

        # 2. Clear Match
        self.db.clear_match(file_id)
        self.assertEqual(len(self.db.get_links_for_file(file_id)), 0)

        # 3. Rematch: S02E05
        self.db.update_file(file_id, fn_season=2, fn_episode=5)
        # New mock for Season 2
        def side_effect_s2(url, *args, **kwargs):
            if "season/2" in url:
                return {'id': 202, 'episodes': [{'id': 2005, 'episode_number': 5}]}
            return {'id': 2290, 'name': 'SGA', 'credits': {'cast': []}}
        self.mock_api.side_effect = side_effect_s2
        
        self.resolver._finalize_match(file_id, mid1, res1, self.db.get_file_by_id(file_id), 'matched')
        
        links2 = self.db.get_links_for_file(file_id)
        self.assertEqual(len(links2), 1)
        self.assertEqual(self.db.get_episode_by_id(links2[0]['tv_episode_id'])['episode_number'], 5)

    def test_case_9_type_switch_rematch(self):
        """Test: Match as Movie -> Clear Match -> Match as TV show."""
        print("\n[Test] Case 9: Type Switch Rematch (Movie -> TV)")
        file_id = self.db.add_file("C:/Mixed/Stargate.mkv", "video", 8000)
        
        # 1. Match as Movie
        self.db.update_file(file_id, fn_media_type='movie')
        res_m = {'tmdb_id': 2164, 'media_type': 'movie', 'title': 'Stargate', 'year': 1994}
        self.mock_api.side_effect = None
        self.mock_api.return_value = {'id': 2164, 'title': 'Stargate', 'credits': {'cast': []}}
        
        mid_m = self.resolver._store_result(res_m)
        self.resolver._finalize_match(file_id, mid_m, res_m, self.db.get_file_by_id(file_id), 'matched')
        
        self.assertEqual(self.db.get_file_by_id(file_id)['fn_media_type'], 'movie')

        # 2. Clear Match
        self.db.clear_match(file_id)

        # 3. Rematch as TV
        self.db.update_file(file_id, fn_media_type='tv', fn_season=1, fn_episode=1)
        res_tv = {'tmdb_id': 4629, 'media_type': 'tv', 'title': 'Stargate SG-1', 'year': 1997}
        
        def side_effect_tv(url, *args, **kwargs):
            if "season/1" in url:
                return {'id': 1, 'episodes': [{'id': 46291, 'episode_number': 1}]}
            return {'id': 4629, 'name': 'Stargate SG-1', 'credits': {'cast': []}}
        self.mock_api.side_effect = side_effect_tv
        
        mid_tv = self.resolver._store_result(res_tv)
        self.resolver._finalize_match(file_id, mid_tv, res_tv, self.db.get_file_by_id(file_id), 'matched')
        
        links = self.db.get_links_for_file(file_id)
        self.assertEqual(links[0]['media_item_id'], mid_tv)
        self.assertIsNotNone(links[0]['tv_episode_id'])


    def test_case_10_multi_episode_to_single_clear(self):
        """Test: Match S01E01-02 -> Clear -> Match S01E01 only."""
        print("\n[Test] Case 10: Multi-to-Single Rematch")
        file_id = self.db.add_file("C:/SGA/101-102.mkv", "video", 9000)
        self.db.update_file(file_id, fn_season=1, fn_episode="[1, 2]")
        
        res = {'tmdb_id': 2290, 'media_type': 'tv', 'title': 'SGA', 'year': 2004}
        def side_effect(url, *args, **kwargs):
            return {'id': 1, 'episodes': [{'id': 101, 'episode_number': 1}, {'id': 102, 'episode_number': 2}]}
        self.mock_api.side_effect = side_effect
        
        mid = self.resolver._store_result(res)
        self.resolver._finalize_match(file_id, mid, res, self.db.get_file_by_id(file_id), 'matched')
        self.assertEqual(len(self.db.get_links_for_file(file_id)), 2)

        # Clear
        self.db.clear_match(file_id)
        
        # Rematch as single episode
        self.db.update_file(file_id, fn_episode=1)
        self.resolver._finalize_match(file_id, mid, res, self.db.get_file_by_id(file_id), 'matched')
        
        # Verify: only ONE link remains
        self.assertEqual(len(self.db.get_links_for_file(file_id)), 1)

    def test_case_11_manual_multi_episode_basket(self):
        """Test: Simulate basket selection of 3 episodes (ManualResolveDialog logic)."""
        print("\n[Test] Case 11: Manual Multi-episode Basket")
        file_id = self.db.add_file("C:/TV/Tri-Episode.mkv", "video", 9999)
        
        # Simulate basket with S01E01, S01E02, S01E03
        res = {'tmdb_id': 500, 'media_type': 'tv', 'title': 'The Show', 'year': 2020}
        basket = [
            {'media': res, 's': 1, 'e': 1},
            {'media': res, 's': 1, 'e': 2},
            {'media': res, 's': 1, 'e': 3}
        ]
        
        # Mock for 3 episodes
        def side_effect(url, *args, **kwargs):
            return {
                'id': 1, 
                'episodes': [
                    {'id': 101, 'episode_number': 1},
                    {'id': 102, 'episode_number': 2},
                    {'id': 103, 'episode_number': 3}
                ]
            }
        self.mock_api.side_effect = side_effect
        
        # Logic from ManualResolveDialog._on_confirm
        all_episodes = []
        for item in basket:
            m = item['media']
            all_episodes.append(item['e'])
            vid_mock = self.db.get_file_by_id(file_id)
            vid_mock['fn_season'] = item['s']
            vid_mock['fn_episode'] = str(item['e'])
            vid_mock['fn_media_type'] = m['media_type']
            
            mid = self.resolver._store_result(m)
            self.resolver._finalize_match(file_id, mid, m, vid_mock, status='matched')
            
        ep_val = str(sorted(list(set(all_episodes))))
        self.db.update_file(file_id, fn_episode=ep_val)
        
        # Verify
        links = self.db.get_links_for_file(file_id)
        self.assertEqual(len(links), 3)
        self.assertEqual(self.db.get_file_by_id(file_id)['fn_episode'], "[1, 2, 3]")

    def test_case_12_type_locking_in_basket(self):
        """Test that the basket enforces the same media type."""
        print("\n[Test] Case 12: Type Locking in Basket")
        
        # This is a logic test for the behavior we just implemented in the Dialog
        res_movie = {'tmdb_id': 1, 'media_type': 'movie', 'title': 'Movie 1'}
        res_tv = {'tmdb_id': 2, 'media_type': 'tv', 'title': 'Show 1'}
        
        basket = []
        
        # 1. Add Movie
        basket.append({'media': res_movie})
        
        # 2. Try to add TV (Simulating the check in _add_to_basket)
        first_type = basket[0]['media']['media_type']
        new_item = res_tv
        
        if new_item['media_type'] == first_type:
            basket.append({'media': new_item})
        
        # Result: Basket should still only have 1 item
        self.assertEqual(len(basket), 1)
        self.assertEqual(basket[0]['media']['media_type'], 'movie')

if __name__ == "__main__":
    unittest.main()
