import os

class PathCrawler:
    """
    Handles recursive directory traversal and file discovery.
    Supports excluding specific folders and files.
    """
    def walk(self, root_path, exclude_dirs=None, exclude_files=None):
        """Recursively walks a directory and returns a list of absolute paths."""
        if exclude_dirs is None: exclude_dirs = {'.git', '.svn', '.gemini', '$RECYCLE.BIN', 'System Volume Information'}
        if exclude_files is None: exclude_files = {'thumbs.db', 'desktop.ini', '.DS_Store'}
        
        all_files = []
        for root, dirs, files in os.walk(root_path):
            # In-place directory filtering to prevent descending into excluded dirs
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for f in files:
                if f.lower() in exclude_files: continue
                
                abs_path = os.path.abspath(os.path.join(root, f))
                all_files.append(abs_path)
        return all_files

    def check_exists(self, path):
        return os.path.exists(path)

    def get_stats(self, path):
        """Returns size and other metadata for a path."""
        try:
            if not os.path.exists(path): return None
            return {
                'size_bytes': os.path.getsize(path),
                'basename': os.path.basename(path),
                'ext': os.path.splitext(path)[1].lower()
            }
        except OSError:
            return None
