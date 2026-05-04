"""Discovery V3 Logic and Edge Case Tests."""
import sys, os, unittest
# Add project root to sys.path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

from core.db.database import LibraryDB
from core.engine.scanner import SmartScanner
import tempfile
import shutil

class MockSettings:
    def __init__(self):
        self.video_extensions = "mkv,mp4,avi"
        self.subtitle_extensions = "srt,ass"
        self.audio_extensions = "mp3,flac"
        self.image_extensions = "jpg,png"
        self.metadata_extensions = "nfo,xml"
        self.vid_size = 0.1  # MB (Small for testing)
        self.sample_keywords = "sample,trailer,minta"

class TestDiscoveryV3Logic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup a temporary test database
        cls.test_db_path = os.path.join(base_dir, "data", "test_discovery_v3.db")
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)
            
        cls.db = LibraryDB(cls.test_db_path)
        cls.settings = MockSettings()
        cls.scanner = SmartScanner(cls.settings, cls.db)

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        with self.db._get_connection() as conn:
            conn.execute("DELETE FROM media_files")
            conn.execute("DELETE FROM file_media_links")
            conn.commit()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _create_dummy_file(self, name, size_mb=1):
        path = os.path.join(self.temp_dir, name)
        with open(path, 'wb') as f:
            f.write(b'\0' * int(size_mb * 1024 * 1024))
        return path

    def test_scan_single_file_movie(self):
        """Test dropping a single movie file."""
        path = self._create_dummy_file("Inception (2010).mkv", size_mb=2)
        fid = self.scanner.scan_single_file(path)
        self.assertIsNotNone(fid)
        
        file_data = self.db.get_file_by_id(fid)
        self.assertEqual(file_data['category'], 'video')
        self.assertEqual(file_data['file_name'], "Inception (2010).mkv")

    def test_scan_single_file_extra_with_parent_linking(self):
        """Test dropping an extra that should link to an existing movie in DB."""
        # 1. Add movie first
        movie_path = self._create_dummy_file("Batman.mkv", size_mb=2)
        mid = self.scanner.scan_single_file(movie_path)
        
        # 2. Add extra in same dir
        extra_path = self._create_dummy_file("Batman-trailer.mkv", size_mb=0.1)
        eid = self.scanner.scan_single_file(extra_path)
        
        file_data = self.db.get_file_by_id(eid)
        self.assertEqual(file_data['category'], 'extra')
        self.assertEqual(file_data['sub_category'], 'trailer')
        
        # Check link
        self.assertEqual(file_data['parent_file_id'], mid)

    def test_scan_single_file_subtitle_deep_lookup(self):
        """Test dropping a subtitle that should find parent up 2 levels."""
        # movies/
        #   The Matrix/
        #     The Matrix.mkv
        #     subs/
        #       English.srt  <-- Drop this
        
        movie_dir = os.path.join(self.temp_dir, "The Matrix")
        subs_dir = os.path.join(movie_dir, "subs")
        os.makedirs(subs_dir)
        
        movie_path = os.path.join(movie_dir, "The Matrix.mkv")
        with open(movie_path, 'wb') as f: f.write(b'\0' * 200000) # ~200KB > 0.1MB
        mid = self.scanner.scan_single_file(movie_path)
        
        sub_path = os.path.join(subs_dir, "English.srt")
        with open(sub_path, 'w') as f: f.write('sub')
        sid = self.scanner.scan_single_file(sub_path)
        
        file_data = self.db.get_file_by_id(sid)
        self.assertEqual(file_data['parent_file_id'], mid)

    def test_duplicate_dropping(self):
        """Test that dropping the same file twice doesn't create 2 records."""
        path = self._create_dummy_file("Double.mkv")
        fid1 = self.scanner.scan_single_file(path)
        fid2 = self.scanner.scan_single_file(path)
        
        self.assertIsNotNone(fid1)
        self.assertEqual(fid1, fid2)
        
        with self.db._get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM media_files").fetchone()[0]
            self.assertEqual(count, 1)

    def test_is_manual_logic(self):
        """Test manual flag management."""
        path = self._create_dummy_file("Manual.mkv")
        fid = self.scanner.scan_single_file(path)
        
        # Default is 0
        self.assertEqual(self.db.get_file_by_id(fid)['is_manual'], 0)
        
        # Set to 1 (Dropped tab)
        self.db.update_file(fid, is_manual=1)
        self.assertEqual(self.db.get_file_by_id(fid)['is_manual'], 1)
        
        # Clear manual (Import to Library)
        self.db.update_file(fid, is_manual=0)
        self.assertEqual(self.db.get_file_by_id(fid)['is_manual'], 0)

    def test_hard_delete_from_db(self):
        """Test that we can physically remove files from DB (for Dropped tab)."""
        path = self._create_dummy_file("Goodbye.mkv")
        fid = self.scanner.scan_single_file(path)
        
        # Simulate what the UI does for Dropped deletion
        with self.db._get_connection() as conn:
            conn.execute("DELETE FROM media_files WHERE id = ?", (fid,))
            conn.commit()
            
        self.assertIsNone(self.db.get_file_by_id(fid))

    def test_edge_case_size_boundary(self):
        """Test file at exactly the size boundary between video and extra."""
        # Temporarily set vid_size to 1.5MB for this test
        old_size = self.scanner.s.vid_size
        self.scanner.s.vid_size = 1.5
        
        # 1.4 MB -> extra
        path1 = self._create_dummy_file("Small.mkv", size_mb=1.4)
        fid1 = self.scanner.scan_single_file(path1)
        self.assertEqual(self.db.get_file_by_id(fid1)['category'], 'extra')
        
        # 1.6 MB -> video
        path2 = self._create_dummy_file("Big.mkv", size_mb=1.6)
        fid2 = self.scanner.scan_single_file(path2)
        self.assertEqual(self.db.get_file_by_id(fid2)['category'], 'video')
        
        self.scanner.s.vid_size = old_size

if __name__ == "__main__":
    unittest.main()
