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

    def undo_batch(self, batch_id, progress_callback=None):
        """Reverses all operations in a specific batch."""
        history = self.db.history.get_batch(batch_id)
        if not history: return 0, 0, ["No history found."]

        success, failed, errors = 0, 0, []
        total = len(history)

        for i, entry in enumerate(history):
            if progress_callback:
                progress_callback(i, total, entry.get('new_path'))
            
            ok, msg = self.undo_single(entry)
            if ok: success += 1
            else:
                failed += 1
                errors.append(msg)

        # Cleanup batch history after attempt
        self.db.history.delete_batch(batch_id)
        return success, failed, errors

    def undo_single(self, history_entry):
        """Reverses a single rename operation."""
        old_path = history_entry['old_path'] # Original source
        new_path = history_entry['new_path'] # Current location
        
        ok, error = self.operator.move_file(new_path, old_path)
        if ok:
            self.db.files.update_file(history_entry['file_id'], current_path=old_path, status='restored')
            return True, "Restored."
        return False, error
