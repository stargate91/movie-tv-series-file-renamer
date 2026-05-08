import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class HistoryManager:
    """
    Manages the rename_history table and handles Undo operations.
    """
    def __init__(self, db, file_operator):
        self.db = db
        self.operator = file_operator

    def start_batch(self):
        """Generates a unique ID for a new renaming batch."""
        return str(uuid.uuid4())[:8]

    def record_rename(self, batch_id, file_id, old_path, new_path):
        """Saves a rename operation to the history."""
        self.db.history.add_history(batch_id, file_id, old_path, new_path)

    def undo_batch(self, batch_id, settings, progress_callback=None):
        """Reverses all operations in a specific batch."""
        history = self.db.history.get_batch(batch_id)
        if not history: return 0, 0, ["No history found."]

        success, failed, errors = 0, 0, []
        dirs_to_check = set()
        total = len(history)

        for i, entry in enumerate(history):
            if progress_callback:
                if progress_callback(i, total, entry.get('new_path')) is False:
                    errors.append("Undo aborted by user.")
                    break
            
            # Collect the directory we are moving FROM (the one that might become empty)
            import os
            new_path = entry.get('new_path')
            if new_path:
                dirs_to_check.add(os.path.dirname(os.path.normpath(new_path)))

            ok, msg = self.undo_single(entry)
            if ok: 
                success += 1
                # Remove only the successful entry from history
                self.db.history.delete_history_item(entry['id'])
            else:
                failed += 1
                errors.append(msg)

        # Cleanup empty folders if enabled
        if settings.cleanup_empty_folders:
            self.operator.cleanup_empty_dirs(dirs_to_check, settings)

        return success, failed, errors

    def undo_single(self, history_entry):
        """Reverses a single rename operation."""
        import os
        old_path = os.path.normpath(history_entry['old_path']) # Original source
        new_path = os.path.normpath(history_entry['new_path']) # Current location
        
        ok, error = self.operator.move_file(new_path, old_path)
        if ok:
            # Restore to MATCHED status so it goes back to Movies/Shows tab
            # and clear the status so it's no longer 'renamed'
            self.db.files.update_file(
                history_entry['file_id'], 
                current_path=old_path, 
                status=None, 
                match_status='MATCHED'
            )
            return True, "Restored."
        return False, error
