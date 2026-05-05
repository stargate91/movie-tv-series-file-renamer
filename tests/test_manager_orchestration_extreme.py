import unittest
from unittest.mock import MagicMock, patch, call
from core.engine.manager import RenamerEngineV3

class TestManagerOrchestrationExtreme(unittest.TestCase):
    @patch('core.engine.manager.LibraryDB')
    @patch('core.engine.manager.ConfigManager')
    @patch('core.engine.manager.SmartScanner')
    @patch('core.engine.manager.Collector')
    @patch('core.engine.manager.Resolver')
    @patch('core.engine.manager.Formatter')
    @patch('core.engine.manager.CollisionResolver')
    @patch('core.engine.manager.Executor')
    def setUp(self, MockExecutor, MockCollisionResolver, MockFormatter, MockResolver, MockCollector, MockSmartScanner, MockConfigManager, MockLibraryDB):
        self.mock_db = MockLibraryDB.return_value
        self.mock_config = MockConfigManager.return_value
        self.mock_scanner = MockSmartScanner.return_value
        self.mock_collector = MockCollector.return_value
        self.mock_resolver = MockResolver.return_value
        self.mock_formatter = MockFormatter.return_value
        self.mock_collision_resolver = MockCollisionResolver.return_value
        self.mock_executor = MockExecutor.return_value
        
        self.engine = RenamerEngineV3()

    def test_full_scan_and_resolve_callbacks(self):
        """
        Biztosítja, hogy a callback mechanizmus pontosan hívódik meg minden almodulnál, 
        megfelelő progress arányokkal.
        """
        cb_mock = MagicMock()
        
        # Szimuláljuk, hogy a collector 2 lépésben végez (50%, 100%)
        def collector_side_effect(cb=None):
            if cb:
                cb("Coll step 1", 1, 2)
                cb("Coll step 2", 2, 2)
        self.mock_collector.collect_all.side_effect = collector_side_effect

        # Szimuláljuk, hogy a resolver 2 lépésben végez (50%, 100%)
        def resolver_side_effect(cb=None):
            if cb:
                cb("Res step 1", 1, 2)
                cb("Res step 2", 2, 2)
        self.mock_resolver.resolve_all.side_effect = resolver_side_effect

        self.engine.full_scan_and_resolve("/dummy/path", cb=cb_mock)
        
        self.mock_scanner.scan_directory.assert_called_once_with("/dummy/path")
        self.mock_collector.collect_all.assert_called_once()
        self.mock_resolver.resolve_all.assert_called_once()
        
        # Callback check
        expected_calls = [
            call("Scanning directory...", 0, 100),
            call("Collecting metadata (FFmpeg/GuessIt)...", 20, 100),
            call("Coll step 1", 20 + (1/2 * 30), 100), # 35.0
            call("Coll step 2", 20 + (2/2 * 30), 100), # 50.0
            call("Identifying media with APIs...", 50, 100),
            call("Res step 1", 50 + (1/2 * 50), 100), # 75.0
            call("Res step 2", 50 + (2/2 * 50), 100), # 100.0
            call("Pipeline complete.", 100, 100)
        ]
        cb_mock.assert_has_calls(expected_calls, any_order=False)

    def test_get_rename_plan_no_file_ids_advanced_filtering(self):
        """
        Nagyon szigorú teszt a get_rename_plan query-jére.
        Csak a MATCHED videókat szabad visszaadnia, kihagyva a DELETED/RENAMED státuszúakat.
        Az extrákat akkor is be kell vonnia, ha a szülő MATCHED, kivéve ha az extra IGNORED, DELETED vagy RENAMED.
        """
        # Szimuláljuk a get_files_by_category visszaadott értékét
        self.mock_db.get_files_by_category.return_value = [
            {"id": 1, "match_status": "MATCHED", "status": "PENDING"}, # valid
            {"id": 2, "match_status": "UNMATCHED", "status": "PENDING"}, # invalid
            {"id": 3, "match_status": "MATCHED", "status": "RENAMED"}, # invalid
            {"id": 4, "match_status": "MATCHED", "status": "DELETED"}, # invalid
            {"id": 5, "match_status": "MATCHED", "status": None}, # valid
        ]

        # Szimuláljuk a sqlite cursor execute.fetchall hívásokat az extrákra
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        self.mock_db._get_connection.return_value = mock_conn
        mock_conn.execute.return_value = mock_cursor

        def fetchall_side_effect():
            # A fetchall mindig attól függ, hogy melyik ID-re hívtuk
            args = mock_conn.execute.call_args[0][1]
            if args[0] == 1:
                return [{"id": 11}, {"id": 12}] # Extrák az 1-eshez
            elif args[0] == 5:
                return [{"id": 51}] # Extrák az 5-öshöz
            return []

        mock_cursor.fetchall.side_effect = fetchall_side_effect

        self.mock_executor.create_plan.return_value = "MockPlan"

        result = self.engine.get_rename_plan()

        self.assertEqual(result, "MockPlan")
        
        # A file_ids ami be lett adva az executor.create_plan-nek
        # 1-es, plusz az extrái (11, 12), és az 5-ös, plusz extrája (51)
        expected_ids = [1, 11, 12, 5, 51]
        self.mock_executor.create_plan.assert_called_once()
        
        actual_ids = self.mock_executor.create_plan.call_args[0][0]
        self.assertCountEqual(actual_ids, expected_ids)

if __name__ == '__main__':
    unittest.main()
