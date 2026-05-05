import sys
import os
import time
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db.database import LibraryDB
from api.client import APIClient
from core.engine.matching_engine import MatchingEngine
from core.engine.library_manager import LibraryManager
from core.engine.resolver import Resolver

class TestRefactorIntegration(unittest.TestCase):
    def setUp(self):
        # Use a unique temporary database for each test to avoid lock issues on Windows
        import uuid
        self.db_path = f"test_renda_{uuid.uuid4().hex}.db"
        self.db = LibraryDB(self.db_path)
        
        # Mock settings
        self.settings = MagicMock()
        self.settings.tmdb_key = "test_key"
        self.settings.tmdb_bearer_token = "test_token"
        self.settings.omdb_key = "test_omdb"
        self.settings.metadata_language = "en-US"
        self.settings.separator = " "
        self.settings.clean_empty_tags = True
        self.settings.custom_variable = ""
        self.settings.movie_template = "{Title} ({Year})"
        self.settings.episode_template = "{ShowTitle} - {Season}{Episode} - {EpisodeTitle}"
        self.settings.movie_folder_template = "{Title} ({Year})"
        self.settings.show_folder_template = "{ShowTitle}"
        self.settings.season_folder_template = "Season {SeasonNumber}"
        self.settings.base_target_path = ""
        self.settings.target_dir_movies = ""
        self.settings.target_dir_shows = ""
        self.settings.action_extra_video = "rename"
        self.settings.action_extra_subtitle = "rename"
        self.settings.action_extra_audio = "rename"
        self.settings.action_extra_image = "rename"
        self.settings.action_extra_metadata = "rename"
        self.settings.cleanup_empty_folders = False

    def tearDown(self):
        # Explicitly close connections if possible (sqlite3 doesn't have a close on the manager, 
        # but the connection object itself does. Our LibraryDB doesn't keep a persistent one.)
        # However, WAL mode might keep files open.
        
        # Give some time for connections to close
        import gc
        gc.collect() 
        
        if os.path.exists(self.db_path):
            try: os.remove(self.db_path)
            except: pass
        for ext in ['-shm', '-wal']:
            if os.path.exists(self.db_path + ext):
                try: os.remove(self.db_path + ext)
                except: pass

    def test_repository_pattern(self):
        """Verify that the new repository pattern correctly persists data."""
        print("\nTesting Repository Pattern...")
        
        # Test FileRepository
        fid = self.db.files.add_file("C:/Movies/Matrix.mp4", "video", 1024*1024*500)
        self.assertIsNotNone(fid)
        
        f_data = self.db.files.get_file_by_id(fid)
        self.assertEqual(f_data['file_name'], "Matrix.mp4")
        
        # Test MediaRepository
        mid = self.db.media.upsert_media_item(tmdb_id=603, title="The Matrix", year=1999, media_type="movie")
        self.assertIsNotNone(mid)
        
        m_data = self.db.media.get_media_item_by_id(mid)
        self.assertEqual(m_data['title'], "The Matrix")
        
        # Test Linking
        self.db.media.link_file_to_media(fid, mid)
        links = self.db.media.get_links_for_file(fid)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]['media_item_id'], mid)
        
        print("PASSED: Repository Pattern")

    def test_api_throttling(self):
        """Verify that the API client respects the minimum interval."""
        print("\nTesting API Throttling...")
        
        # Use a client WITHOUT a DB to avoid cache hits during the throttle test
        client = APIClient("okey", "tkey", "token", db=None)
        client.tmdb.min_interval = 0.2 
        
        with patch.object(client.tmdb._session, 'get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"results": []}
            
            start_time = time.time()
            # Perform 3 requests. Since db=None, it WILL call _throttle every time.
            for i in range(3):
                client.tmdb.search_movie(f"Test_{i}")
            
            duration = time.time() - start_time
            # 3 requests:
            # 1. Start (0s)
            # 2. Start + 0.2s (after sleep)
            # 3. Start + 0.4s (after sleep)
            self.assertGreaterEqual(duration, 0.38) # allow tiny margin
            print(f"Throttling works: 3 requests took {duration:.2f}s (expected >= 0.4s)")

    def test_library_manager_hydration(self):
        """Verify that LibraryManager correctly hydrates TV seasons/episodes."""
        print("\nTesting TV Season Hydration...")
        
        manager = LibraryManager(self.db, self.settings)
        
        # Mock TMDB API responses
        mock_season = {
            "name": "Season 1",
            "season_number": 1,
            "episodes": [
                {"episode_number": 1, "name": "Pilot", "id": 101},
                {"episode_number": 2, "name": "Deep Throat", "id": 102}
            ],
            "id": 1234
        }
        
        with patch.object(manager.api.tmdb, 'get_season_details', return_value=mock_season):
            with patch.object(manager.api.tmdb, 'get_episode_details', return_value={"external_ids": {"imdb_id": "ep_imdb"}}):
                # We need a media item first
                mid = self.db.media.upsert_media_item(tmdb_id=88, title="The X-Files", media_type="tv")
                
                manager.fetch_and_store_season(88, 1)
                
                # Check if episodes were stored
                with self.db._get_connection() as conn:
                    eps = conn.execute("SELECT * FROM tv_episodes WHERE media_item_id = ?", (mid,)).fetchall()
                    self.assertEqual(len(eps), 2)
                    self.assertEqual(eps[0]['name'], "Pilot")
                    self.assertEqual(eps[1]['name'], "Deep Throat")
        
        print("PASSED: TV Hydration")

    def test_resolver_orchestration(self):
        """Verify that the Resolver (orchestrator) still coordinates correctly."""
        print("\nTesting Resolver Orchestration...")
        from core.engine.resolver import Resolver
        
        resolver = Resolver(self.db, self.settings)
        
        # Mock scanner/collector results
        fid = self.db.files.add_file("C:/Movies/Matrix.mp4", "video", 100)
        self.db.files.update_file(fid, fn_title="The Matrix", fn_year=1999, fn_media_type="movie")
        
        # Mock engine search (Resolver calls self.matcher)
        mock_match = {"tmdb_id": 603, "title": "The Matrix", "year": 1999, "media_type": "movie"}
        
        with patch.object(resolver.matcher, 'search_api', return_value=[mock_match]):
            with patch.object(resolver.matcher, 'confidence_check', return_value=True):
                with patch.object(resolver.library, 'store_result', return_value=1):
                    # Resolve the file
                    resolver.resolve_file(fid)
                    
                    # Check if file status updated
                    f_data = self.db.files.get_file_by_id(fid)
                    self.assertEqual(f_data['match_status'], 'matched')
        
        print("PASSED: Resolver Orchestration")

    def test_collector_decomposition(self):
        """Verify that the modular Collector correctly extracts metadata."""
        print("\nTesting Collector Decomposition...")
        from core.engine.collector import Collector
        
        collector = Collector(self.db)
        
        # 1. Test Filename Parsing
        fid = self.db.files.add_file("C:/Movies/Inception.2010.1080p.mp4", "video", 100)
        collector.collect_single_file(fid)
        
        f_data = self.db.files.get_file_by_id(fid)
        self.assertEqual(f_data['fn_title'], "Inception")
        self.assertEqual(f_data['fn_year'], 2010)
        
        # 2. Test NFO Parsing (Mocked File)
        nfo_path = self.db_path + ".nfo"
        with open(nfo_path, "w") as f:
            f.write('<uniqueid type="imdb">tt1375666</uniqueid>')
        
        nid = self.db.files.add_file(nfo_path, "metadata", 10)
        self.db.files.update_file(nid, parent_file_id=fid, extension=".nfo")
        
        collector._phase_nfo()
        
        f_data = self.db.files.get_file_by_id(fid)
        self.assertEqual(f_data['nfo_imdb_id'], "tt1375666")
        
        if os.path.exists(nfo_path): os.remove(nfo_path)
        print("PASSED: Collector Decomposition")

    def test_naming_engine(self):
        """Verify that Formatter and TagBuilder generate correct names."""
        print("\nTesting Naming Engine (TagBuilder)...")
        from core.engine.formatter import Formatter
        
        formatter = Formatter(self.db)
        
        # 1. Setup file and media
        fid = self.db.files.add_file("Matrix.mp4", "video", 100)
        self.db.files.update_file(fid, resolution="1920x1080", video_codec="H264")
        
        mid = self.db.media.upsert_media_item(tmdb_id=603, title="The Matrix", year=1999, media_type="movie")
        self.db.media.link_file_to_media(fid, mid)
        
        # 2. Generate Name with a template
        mock_settings = MagicMock()
        mock_settings.movie_template = "{Title} ({Year}) [{Resolution}]"
        mock_settings.custom_variable = ""
        mock_settings.separator = " "
        mock_settings.clean_empty_tags = True
        
        name = formatter.generate_name(fid, mock_settings)
        
        self.assertEqual(name, "The Matrix (1999) [1080p]")
        print("PASSED: Naming Engine")

    def test_executor_decomposition(self):
        """Verify that the modular Executor correctly handles planning, execution and undo."""
        print("\nTesting Executor Decomposition...")
        from core.engine.executor import Executor
        from core.engine.formatter import Formatter
        from core.engine.collision_resolver import CollisionResolver
        
        formatter = Formatter(self.db)
        resolver = CollisionResolver(self.settings)
        executor = Executor(self.db, formatter, resolver, self.settings)
        
        # 1. Setup files
        fid = self.db.files.add_file("Matrix.mp4", "video", 100)
        self.db.files.update_file(fid, fn_title="The Matrix", fn_year=1999, fn_media_type="movie")
        mid = self.db.media.upsert_media_item(tmdb_id=603, title="The Matrix", year=1999, media_type="movie")
        self.db.media.link_file_to_media(fid, mid)
        self.settings.movie_template = "{Title} ({Year})"
        
        # 2. Plan
        plan = executor.create_plan([fid])
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['action'], 'rename')
        # Formatter returns Folder/File.ext
        self.assertTrue(plan[0]['proposed_path'].endswith("The Matrix (1999).mp4"))
        
        # 3. Execute (Mocking File Operations)
        with patch.object(executor.op, 'move_file', return_value=(True, None)):
            results = executor.execute_plan(plan)
            self.assertEqual(results['success'], 1)
            
            # Check history
            batch_id = results['batch_id']
            history = self.db.files.get_batch_history(batch_id)
            self.assertEqual(len(history), 1)
            
            # 4. Undo
            with patch.object(executor.op, 'move_file', return_value=(True, None)):
                s, f, errs = executor.undo_batch(batch_id)
                self.assertEqual(s, 1)
                
                # History should be cleared
                self.assertEqual(len(self.db.files.get_batch_history(batch_id)), 0)
        
        print("PASSED: Executor Decomposition")

if __name__ == "__main__":
    unittest.main()
