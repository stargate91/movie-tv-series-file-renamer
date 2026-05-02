from PySide6.QtCore import QObject, Signal

class AppState(QObject):
    """
    Centralized state management for the application.
    Enables reactive UI by emitting signals when data changes.
    """
    # Signals for UI updates
    selection_changed = Signal(set)     # Current set of absolute paths
    metadata_updated = Signal(str)      # File path that was updated
    list_reset = Signal()               # Emitted when the entire list is cleared or rescanned
    status_msg = Signal(str)            # Global status message

    def __init__(self):
        super().__init__()
        self.video_files = []           # List of absolute paths
        self.metadata_map = {}          # path -> meta dict
        self.selected_files = set()     # Set of absolute paths
        self.is_multi_select_mode = False
        
        # Discovery and enrichment state
        self.discovery_results = {}
        self.collected_results = []
        self.enriched_files = []
        self.unexpected_episodes = []
        self.renamed_files = []
        self.rename_history = []

    def set_selected(self, paths, multi_select=None):
        """Updates the selection and notifies listeners."""
        self.selected_files = set(paths)
        if multi_select is not None:
            self.is_multi_select_mode = multi_select
        elif not self.selected_files:
            self.is_multi_select_mode = False
            
        self.selection_changed.emit(self.selected_files)

    def add_selection(self, path):
        self.selected_files.add(path)
        self.is_multi_select_mode = True
        self.selection_changed.emit(self.selected_files)

    def remove_selection(self, path):
        self.selected_files.discard(path)
        if not self.selected_files:
            self.is_multi_select_mode = False
        self.selection_changed.emit(self.selected_files)

    def clear_selection(self):
        self.selected_files.clear()
        self.is_multi_select_mode = False
        self.selection_changed.emit(self.selected_files)

    def reset_state(self):
        """Full reset of the session state."""
        self.video_files = []
        self.metadata_map = {}
        self.selected_files = set()
        self.is_multi_select_mode = False
        self.discovery_results = {}
        self.collected_results = []
        self.enriched_files = []
        self.unexpected_episodes = []
        self.renamed_files = []
        self.rename_history = []
        self.list_reset.emit()
        self.status_msg.emit("Ready")

    def update_metadata(self, path, meta):
        self.metadata_map[path] = meta
        self.metadata_updated.emit(path)
