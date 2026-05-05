import os
import shutil
import logging

logger = logging.getLogger(__name__)

class FileOperator:
    """
    Handles physical file system operations (move, delete) and directory cleanup.
    """
    def move_file(self, source, destination, progress_callback=None):
        """Safely moves a file, creating parent directories if needed. Supports intra-file progress."""
        try:
            if not os.path.exists(source):
                raise FileNotFoundError(f"Source missing: {source}")
            
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            # Check if it's the same device
            if hasattr(os, 'stat') and os.stat(os.path.dirname(source)).st_dev == os.stat(os.path.dirname(destination)).st_dev:
                shutil.move(source, destination)
                if progress_callback: progress_callback(1.0)
            else:
                # Inter-device move: Manual copy with progress + delete
                total_size = os.path.getsize(source)
                copied = 0
                
                with open(source, 'rb') as fsrc:
                    with open(destination, 'wb') as fdst:
                        while True:
                            buf = fsrc.read(1024 * 1024) # 1MB chunks
                            if not buf:
                                break
                            fdst.write(buf)
                            copied += len(buf)
                            if progress_callback:
                                if progress_callback(copied / total_size) is False:
                                    fdst.close()
                                    fsrc.close()
                                    if os.path.exists(destination): os.remove(destination)
                                    return False, "Aborted by user"
                
                # Copy metadata (permissions, times)
                shutil.copystat(source, destination)
                # Remove original
                os.remove(source)
                
            return True, None
        except Exception as e:
            logger.error(f"Move failed: {source} -> {destination} | {e}")
            return False, str(e)

    def delete_file(self, path):
        """Deletes a file from disk."""
        try:
            if os.path.exists(path):
                os.remove(path)
            return True, None
        except Exception as e:
            logger.error(f"Delete failed: {path} | {e}")
            return False, str(e)

    def cleanup_empty_dirs(self, dirs, settings):
        """Recursively removes empty directories moving upwards."""
        roots = {os.path.normpath(p).lower() for p in [
            settings.default_scan_path, 
            settings.folder_path, 
            settings.base_target_path, 
            settings.target_dir_movies, 
            settings.target_dir_shows
        ] if p}
        
        leftovers = {}
        for d in dirs:
            self._remove_empty_dir_recursive(d, roots, leftovers)
        return leftovers

    def _remove_empty_dir_recursive(self, dir_path, roots, leftovers):
        if not dir_path or not os.path.exists(dir_path): return
            
        norm_dir = os.path.normpath(dir_path).lower()
        if norm_dir in roots: return
            
        try:
            items = os.listdir(dir_path)
            if not items:
                os.rmdir(dir_path)
                self._remove_empty_dir_recursive(os.path.dirname(dir_path), roots, leftovers)
            else:
                if dir_path not in leftovers: leftovers[dir_path] = items
        except OSError: pass
