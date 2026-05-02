from core.renamer import rename_video_files

class RenamingEngine:
    """
    Handles the physical renaming of files and collision checks.
    """
    def __init__(self, settings, ui=None):
        self.s = settings
        self.ui = ui

    def execute(self, enriched_files, metadata_map):
        """
        Executes the renaming process.
        Returns (renamed_files, history).
        """
        renamed, history = rename_video_files(
            enriched_files, 
            self.s.live_run, 
            self.s.zero_padding, 
            self.s.custom_variable,
            self.s.movie_template, 
            self.s.episode_template, 
            self.s.filename_case, 
            self.s.separator,
            self.s.extra_action, 
            self.s.extra_template, 
            self.s.movie_extra_template,
            self.s.episode_extra_template,
            self.s,
            metadata_map, 
            self.ui
        )
        return renamed, history
