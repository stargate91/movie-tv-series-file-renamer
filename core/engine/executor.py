import os
import shutil
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class Executor:
    """
    v3.0 Executor: The physical execution engine.
    Orchestrates the Formatter, CollisionResolver, and file system operations.
    """
    
    def __init__(self, db, formatter, collision_resolver, settings):
        self.db = db
        self.formatter = formatter
        self.resolver = collision_resolver
        self.s = settings

    def create_plan(self, file_ids):
        """
        Creates a 'Pre-flight Check' plan for a list of file IDs.
        Returns a list of plan dicts and handles collisions.
        """
        plan = []
        for fid in file_ids:
            file_data = self.db.get_file_by_id(fid)
            if not file_data:
                continue
                
            cat = file_data.get('category')
            is_extra = cat != 'video'
            
            # Check Actions for Extras
            action = 'rename'
            if is_extra:
                action_map = {
                    'extra': self.s.action_extra_video,
                    'subtitle': self.s.action_extra_subtitle,
                    'audio': self.s.action_extra_audio,
                    'image': self.s.action_extra_image,
                    'metadata': self.s.action_extra_metadata
                }
                action = action_map.get(cat, 'rename')
                
            media_type = file_data.get('fn_media_type') or file_data.get('fd_media_type') or 'unknown'

            if action == 'skip':
                plan.append({
                    'file_id': fid,
                    'original_path': file_data['current_path'],
                    'proposed_path': file_data['current_path'],
                    'action': 'skip',
                    'status': 'safe',
                    'category': cat,
                    'media_type': media_type
                })
                continue
                
            if action == 'delete':
                plan.append({
                    'file_id': fid,
                    'original_path': file_data['current_path'],
                    'proposed_path': None,
                    'action': 'delete',
                    'status': 'safe',
                    'category': cat,
                    'media_type': media_type
                })
                continue
                
            # Action is rename
            proposed_path = self.formatter.generate_full_path(fid, self.s)
            if not proposed_path:
                plan.append({
                    'file_id': fid,
                    'original_path': file_data['current_path'],
                    'proposed_path': None,
                    'action': 'error',
                    'status': 'missing_data',
                    'category': cat,
                    'media_type': media_type
                })
                continue
                
            # If path hasn't changed, skip
            if proposed_path.lower() == file_data['current_path'].lower():
                plan.append({
                    'file_id': fid,
                    'original_path': file_data['current_path'],
                    'proposed_path': proposed_path,
                    'action': 'skip',
                    'status': 'safe', # No change needed
                    'category': cat,
                    'media_type': media_type
                })
                continue
                
            plan.append({
                'file_id': fid,
                'original_path': file_data['current_path'],
                'proposed_path': proposed_path,
                'action': 'rename',
                'status': 'pending',
                'category': cat,
                'media_type': media_type
            })
            
        # Run Collision Detection on 'rename' actions
        rename_items = [p for p in plan if p['action'] == 'rename']
        safe, collisions = self.resolver.detect_collisions(rename_items)
        
        for p in safe:
            p['status'] = 'safe'
            
        # Try Auto-Resolve
        for exact_path, group in collisions.items():
            resolved = self.resolver.auto_resolve_group(group)
            if resolved:
                for p in resolved:
                    p['status'] = 'safe'
            else:
                for p in group:
                    p['status'] = 'collision'
                    
        return plan

    def execute_plan(self, plan, progress_callback=None):
        """
        Executes the file system operations based on a validated plan.
        Only processes items with status='safe' or 'auto_resolved'.
        Returns a summary of successes and errors.
        """
        results = {'success': 0, 'failed': 0, 'skipped': 0, 'deleted': 0, 'errors': [], 'batch_id': None}
        batch_id = str(uuid.uuid4())[:8] # Short unique ID for the batch
        results['batch_id'] = batch_id
        
        dirs_to_check = set()
        total = len(plan)
        
        for i, p in enumerate(plan):
            if progress_callback:
                progress_callback(i, total, p.get('original_path'))
            if p['action'] == 'skip':
                results['skipped'] += 1
                continue
                
            if p['status'] == 'collision' or p['status'] == 'missing_data':
                results['failed'] += 1
                results['errors'].append(f"Ignored due to status: {p['status']} ({p['original_path']})")
                continue
                
            orig = p['original_path']
            dirs_to_check.add(os.path.dirname(orig))
            
            if p['action'] == 'delete':
                try:
                    if os.path.exists(orig):
                        os.remove(orig)
                        # Remove from DB to prevent ghosts
                        conn = self.db._get_connection()
                        try:
                            conn.execute("DELETE FROM media_files WHERE id = ?", (p['file_id'],))
                            conn.commit()
                        finally:
                            conn.close()
                        results['deleted'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"Delete failed {orig}: {str(e)}")
                continue
                
            if p['action'] == 'rename':
                dest = p['proposed_path']
                try:
                    if not os.path.exists(orig):
                        raise FileNotFoundError("Source file missing from disk.")
                        
                    # Create target directory if needed
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    
                    # Physically rename/move the file (shutil handles cross-device)
                    shutil.move(orig, dest)
                    
                    # Update Database
                    conn = self.db._get_connection()
                    try:
                        conn.execute("""
                            UPDATE media_files 
                            SET last_path = current_path, current_path = ?, status = 'renamed'
                            WHERE id = ?
                        """, (dest, p['file_id']))
                        
                        conn.execute("""
                            INSERT INTO rename_history (batch_id, file_id, old_path, new_path, timestamp)
                            VALUES (?, ?, ?, ?, ?)
                        """, (batch_id, p['file_id'], orig, dest, datetime.now()))
                        conn.commit()
                    finally:
                        conn.close()
                        
                    results['success'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"Rename failed {orig} -> {dest}: {str(e)}")

        if progress_callback:
            progress_callback(total, total, "Cleanup...")

        # Cleanup empty folders
        if self.s.cleanup_empty_folders:
            results['leftovers'] = self._cleanup_dirs(dirs_to_check)
            
        return results

    def undo_rename(self, history_id):
        """
        Reverses a previous rename operation using the history entry.
        Returns (success, message).
        """
        with self.db._get_connection() as conn:
            history = conn.execute("SELECT * FROM rename_history WHERE id = ?", (history_id,)).fetchone()
            
        if not history:
            return False, "History entry not found."
            
        old_path = history['old_path'] # This was the original source
        new_path = history['new_path'] # This is the current location
        
        try:
            if not os.path.exists(new_path):
                return False, f"Current file missing on disk: {new_path}"
                
            # Ensure the original directory exists
            os.makedirs(os.path.dirname(old_path), exist_ok=True)
            
            # Physically move back
            shutil.move(new_path, old_path)
            
            # Update DB state
            conn = self.db._get_connection()
            try:
                conn.execute("""
                    UPDATE media_files SET current_path = ?, status = 'restored' 
                    WHERE id = ?
                """, (old_path, history['file_id']))
                
                # We remove the history entry once undone
                conn.execute("DELETE FROM rename_history WHERE id = ?", (history_id,))
                conn.commit()
            finally:
                conn.close()
                
            return True, "Successfully restored to original location."
        except Exception as e:
            logger.error(f"Undo failed: {e}")
            return False, str(e)

    def undo_batch(self, batch_id, progress_callback=None):
        """
        Reverses all rename operations in a specific batch.
        Returns (success_count, fail_count, errors)
        """
        history = self.db.get_batch_history(batch_id)
        if not history:
            return 0, 0, ["No history found for this batch."]

        success = 0
        failed = 0
        errors = []
        total = len(history)

        for i, entry in enumerate(history):
            if progress_callback:
                progress_callback(i, total, entry.get('new_path'))
            
            ok, msg = self.undo_rename(entry['id'])
            if ok:
                success += 1
            else:
                failed += 1
                errors.append(msg)

        # Clean up history for this batch if it was fully/partially undone
        # (undo_rename already deletes individual entries, but let's be sure)
        self.db.delete_batch_history(batch_id)
        
        return success, failed, errors
        
    def _cleanup_dirs(self, dirs):
        """Iterates over directories and removes them if they are completely empty. Returns leftovers."""
        leftovers = {}
        # Define protected root paths to never delete
        roots = {os.path.normpath(p).lower() for p in [
            self.s.default_scan_path, 
            self.s.folder_path, 
            self.s.base_target_path, 
            self.s.target_dir_movies, 
            self.s.target_dir_shows
        ] if p}
        
        for d in dirs:
            self._remove_empty_dir(d, roots, leftovers)
        return leftovers
            
    def _remove_empty_dir(self, dir_path, roots, leftovers):
        """Recursively removes empty directories moving upwards. Records leftovers."""
        if not dir_path or not os.path.exists(dir_path):
            return
            
        norm_dir = os.path.normpath(dir_path).lower()
        if norm_dir in roots:
            return
            
        try:
            items = os.listdir(dir_path)
            if not items: # Empty check
                os.rmdir(dir_path)
                logger.info(f"Cleaned up empty folder: {dir_path}")
                # Check parent recursively
                self._remove_empty_dir(os.path.dirname(dir_path), roots, leftovers)
            else:
                # Not empty. Gather leftovers.
                if dir_path not in leftovers:
                    leftovers[dir_path] = items
        except OSError:
            pass # Directory not empty, or permission denied
