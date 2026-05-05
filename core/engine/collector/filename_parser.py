import os
from guessit import guessit

class FilenameParser:
    """
    Uses GuessIt to extract media info from file and folder names.
    """
    def parse(self, file_path, folder_cache=None, lock=None):
        """Parses both filename and foldername and returns unified update dict."""
        update = {}
        filename = os.path.splitext(os.path.basename(file_path))[0]
        fn_guess = guessit(filename)
        
        # Map GuessIt results to DB columns
        update.update(self._map_guess(fn_guess, 'fn'))
        
        # Parent folder context
        parent_dir = os.path.basename(os.path.dirname(file_path))
        if parent_dir:
            fd_guess = None
            if folder_cache is not None and lock is not None:
                with lock:
                    if parent_dir in folder_cache: fd_guess = folder_cache[parent_dir]
                    else:
                        fd_guess = guessit(parent_dir)
                        folder_cache[parent_dir] = fd_guess
            else:
                fd_guess = guessit(parent_dir)
            
            if fd_guess:
                update.update(self._map_guess(fd_guess, 'fd'))

        # Standardize sub_category
        mtype = update.get('fn_media_type') or update.get('fd_media_type', 'movie')
        update['sub_category'] = 'tv' if mtype == 'episode' else mtype
        
        return update

    def _map_guess(self, guess, prefix):
        def _flat(val):
            if isinstance(val, list): return val[0]
            return val

        # Handle episode list conversion to string for DB
        ep = guess.get('episode')
        ep_str = str(ep) if ep is not None else None

        res = {
            f'{prefix}_title': _flat(guess.get('title')),
            f'{prefix}_year': _flat(guess.get('year')),
            f'{prefix}_season': _flat(guess.get('season')),
            f'{prefix}_episode': ep_str,
            f'{prefix}_media_type': _flat(guess.get('type')),
            'edition': _flat(guess.get('edition'))
        }
        if guess.get('language'):
            res['language'] = str(guess['language'][0]) if isinstance(guess['language'], list) else str(guess['language'])
        return {k: v for k, v in res.items() if v is not None}
