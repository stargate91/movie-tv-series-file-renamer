import os
import shutil
import unittest
import uuid
import logging
import time
import gc
from datetime import datetime
from core.db.database import LibraryDB
from core.engine.executor import Executor

class TestExecutorUndoExtreme(unittest.TestCase):
    def setUp(self):
        # 1. Setup Temp Environment
        self.test_dir = os.path.abspath("extreme_undo_test_env")
        self._safe_rmtree(self.test_dir)
        os.makedirs(self.test_dir)

        # 2. Setup Mock DB
        self.db_path = os.path.join(self.test_dir, "test_renda.db")
        self.db = LibraryDB(self.db_path)
        
        # 3. Setup Executor
        class MockSettings:
            cleanup_empty_folders = True
            action_extra_video = "rename"
            action_extra_subtitle = "rename"
            action_extra_audio = "rename"
            action_extra_image = "rename"
            action_extra_metadata = "rename"
            
        self.executor = Executor(self.db, None, None, MockSettings())

    def tearDown(self):
        # Explicitly clear objects to release DB file handles
        self.executor = None
        self.db = None
        gc.collect() # Force garbage collection
        time.sleep(0.2) # Small buffer for Windows file system
        self._safe_rmtree(self.test_dir)

    def _safe_rmtree(self, path):
        """Windows-safe rmtree with retries."""
        if not os.path.exists(path):
            return
        for i in range(5):
            try:
                shutil.rmtree(path)
                return
            except PermissionError:
                time.sleep(0.1)
        # Final attempt
        shutil.rmtree(path, ignore_errors=True)

    def create_dummy_file(self, rel_path, content="dummy"):
        full_path = os.path.join(self.test_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        return full_path

    def test_batch_undo_full_success(self):
        """Teszt: Egy teljes köteg (2 fájl) sikeres visszaállítása."""
        f1_orig = self.create_dummy_file("Source/Inception.mkv")
        f2_orig = self.create_dummy_file("Source/Inception.srt")
        
        id1 = self.db.add_file(f1_orig, "video", 1000)
        id2 = self.db.add_file(f2_orig, "subtitle", 500)
        
        f1_new = os.path.join(self.test_dir, "Library/Inception (2010)/Inception.mkv")
        f2_new = os.path.join(self.test_dir, "Library/Inception (2010)/Inception.srt")
        
        plan = [
            {'file_id': id1, 'original_path': f1_orig, 'proposed_path': f1_new, 'action': 'rename', 'status': 'safe'},
            {'file_id': id2, 'original_path': f2_orig, 'proposed_path': f2_new, 'action': 'rename', 'status': 'safe'}
        ]
        
        results = self.executor.execute_plan(plan)
        batch_id = results['batch_id']
        
        self.assertTrue(os.path.exists(f1_new))
        
        success, failed, errors = self.executor.undo_batch(batch_id)
        
        self.assertEqual(success, 2)
        self.assertTrue(os.path.exists(f1_orig))
        self.assertTrue(os.path.exists(f2_orig))

    def test_undo_edge_case_missing_file(self):
        """Teszt: Mi történik, ha az átnevezett fájlt az Undo előtt letörölték?"""
        f_orig = self.create_dummy_file("Source/Gone.mkv")
        fid = self.db.add_file(f_orig, "video", 1000)
        f_new = os.path.join(self.test_dir, "Dest/Gone.mkv")
        
        results = self.executor.execute_plan([
            {'file_id': fid, 'original_path': f_orig, 'proposed_path': f_new, 'action': 'rename', 'status': 'safe'}
        ])
        
        # Remove file manually
        os.remove(f_new)
        
        success, failed, errors = self.executor.undo_batch(results['batch_id'])
        
        self.assertEqual(success, 0)
        self.assertEqual(failed, 1)
        self.assertTrue(any("missing on disk" in str(e).lower() for e in errors))

    def test_undo_edge_case_destination_blocked(self):
        """Teszt: Mi történik, ha az eredeti helyet időközben elfoglalták?"""
        f_orig = self.create_dummy_file("Source/Conflict.mkv")
        fid = self.db.add_file(f_orig, "video", 1000)
        f_new = os.path.join(self.test_dir, "Dest/Conflict.mkv")
        
        results = self.executor.execute_plan([
            {'file_id': fid, 'original_path': f_orig, 'proposed_path': f_new, 'action': 'rename', 'status': 'safe'}
        ])
        
        # Create intruder file at original path
        self.create_dummy_file("Source/Conflict.mkv", "Intruder")
        
        success, failed, errors = self.executor.undo_batch(results['batch_id'])
        # shutil.move will overwrite by default on most systems, which is acceptable
        # but the key is that it doesn't crash the engine.
        self.assertEqual(success, 1)

    def test_directory_cleanup_restoration(self):
        """Teszt: Az Undo-nak vissza kell építenie a törölt üres mappákat."""
        deep_dir = os.path.join(self.test_dir, "A/B/C")
        os.makedirs(deep_dir)
        f_orig = os.path.join(deep_dir, "file.txt")
        with open(f_orig, "w") as f: f.write("test")
        
        fid = self.db.add_file(f_orig, "video", 10)
        f_new = os.path.join(self.test_dir, "NewFolder/file.txt")
        
        results = self.executor.execute_plan([
            {'file_id': fid, 'original_path': f_orig, 'proposed_path': f_new, 'action': 'rename', 'status': 'safe'}
        ])
        
        # Verify dir was cleaned up (it should be empty now)
        # Note: Executor's _cleanup_dirs removes empty folders
        self.assertFalse(os.path.exists(deep_dir)) 
        
        # Undo
        self.executor.undo_batch(results['batch_id'])
        
        # Verify restoration
        self.assertTrue(os.path.exists(deep_dir))
        self.assertTrue(os.path.exists(f_orig))

if __name__ == '__main__':
    unittest.main()
