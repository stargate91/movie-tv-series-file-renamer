"""
v3.1 Executor: Orchestrates the execution pipeline.
Decomposed into ExecutionPlanner, FileOperator, and HistoryManager.
"""

import logging
import os
from .planner import ExecutionPlanner
from .operator import FileOperator
from .history import HistoryManager

logger = logging.getLogger(__name__)

class Executor:
    """
    Main entry point for planning and executing file operations.
    Coordinates specialized components for a clean pipeline.
    """
    
    def __init__(self, db, formatter, collision_resolver, settings):
        self.db = db
        self.settings = settings
        self.planner = ExecutionPlanner(db, formatter, collision_resolver)
        self.op = FileOperator()
        self.history = HistoryManager(db, self.op)

    def create_plan(self, file_ids):
        """Generates a pre-flight plan for the given files."""
        return self.planner.create_plan(file_ids, self.settings)

    def execute_plan(self, plan, progress_callback=None):
        """Executes a validated plan and records history."""
        results = {'success': 0, 'failed': 0, 'skipped': 0, 'deleted': 0, 'errors': [], 'batch_id': None}
        batch_id = self.history.start_batch()
        results['batch_id'] = batch_id
        
        dirs_to_check = set()
        total = len(plan)
        
        for i, p in enumerate(plan):
            if progress_callback:
                if progress_callback(i, total, p.get('original_path')) is False:
                    logger.info("Plan execution aborted by user.")
                    break
                
            if p['action'] == 'skip':
                results['skipped'] += 1
                continue
                
            if p['status'] in ('collision', 'missing_data', 'error'):
                results['failed'] += 1
                results['errors'].append(f"Ignored ({p['status']}): {p['original_path']}")
                continue
                
            orig = p['original_path']
            dirs_to_check.add(os.path.dirname(orig))
            
            # 1. DELETE ACTION
            if p['action'] == 'delete':
                ok, err = self.op.delete_file(orig)
                if ok:
                    # Remove from DB (or mark as deleted)
                    # For now, we follow legacy and delete from DB
                    self.db.files.delete_file(p['file_id'])
                    results['deleted'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Delete failed: {err}")
                continue
                
            # 2. RENAME ACTION
            if p['action'] == 'rename':
                dest = p['proposed_path']
                
                def sub_cb(pct):
                    if progress_callback:
                        if progress_callback(i + pct, total, f"Moving ({int(pct*100)}%): {os.path.basename(orig)}") is False:
                            return False # Signal to op.move_file to abort
                    return True

                ok, err = self.op.move_file(orig, dest, progress_callback=sub_cb)
                if ok:
                    # Update DB
                    self.db.files.update_file(p['file_id'], last_path=orig, current_path=dest, status='renamed')
                    # Record for Undo
                    self.history.record_rename(batch_id, p['file_id'], orig, dest)
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Rename failed: {err}")

        # 3. CLEANUP
        if self.settings.cleanup_empty_folders:
            results['leftovers'] = self.op.cleanup_empty_dirs(dirs_to_check, self.settings)
            
        return results

    def undo_batch(self, batch_id, progress_callback=None):
        """Reverses a whole batch of operations."""
        return self.history.undo_batch(batch_id, progress_callback)
