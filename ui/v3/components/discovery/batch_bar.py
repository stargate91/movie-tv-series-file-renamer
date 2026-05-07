from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QMenu
from PySide6.QtCore import Qt, Signal
from ui.v3.styles.theme import Theme
from core.i18n import T

class BatchBar(QFrame):
    """
    Modular Batch Action Bar for Discovery Console.
    Handles visibility and labels for bulk operations.
    """
    identify_requested = Signal()
    actions_requested = Signal()
    fetch_requested = Signal()
    restore_requested = Signal()
    clear_requested = Signal()
    ignore_requested = Signal()
    open_folder_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setObjectName("BatchBar")
        self.setStyleSheet(Theme.get_batch_bar_style())
        self._init_ui()
        self.hide()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        
        self.label = QLabel(T("discovery.messages.items_selected", count=0))
        self.label.setStyleSheet(Theme.get_batch_label_style())
        
        self.btn_actions = QPushButton(T('discovery.actions.batch_actions'))
        self.btn_actions.setIcon(Theme.get_icon("edit-3", size=16, color=Theme.TEXT_MAIN))
        self.btn_actions.setStyleSheet(Theme.get_batch_button_style('primary'))
        self.btn_actions.clicked.connect(self.actions_requested.emit)
        
        self.btn_identify = QPushButton(T("discovery.actions.batch_identify"))
        self.btn_identify.setIcon(Theme.get_icon("wand-2", size=16, color=Theme.TEXT_MAIN))
        self.btn_identify.setStyleSheet(Theme.get_batch_button_style('identify'))
        self.btn_identify.clicked.connect(self.identify_requested.emit)

        self.btn_restore = QPushButton(T("discovery.actions.restore_multi"))
        self.btn_restore.setIcon(Theme.get_icon("undo", size=16, color=Theme.TEXT_MAIN))
        self.btn_restore.setStyleSheet(Theme.get_batch_button_style('success'))
        self.btn_restore.clicked.connect(self.restore_requested.emit)
        self.btn_restore.hide()

        # Overflow Menu
        self.btn_more = QPushButton()
        self.btn_more.setIcon(Theme.get_icon("more-horizontal", size=20, color=Theme.TEXT_MAIN))
        self.btn_more.setFixedSize(54, 40)
        self.btn_more.setCursor(Qt.PointingHandCursor)
        self.btn_more.setStyleSheet(Theme.get_discovery_action_btn_style('neutral'))
        
        self.menu = QMenu(self)
        self.menu.setStyleSheet(Theme.get_context_menu_style())
        
        self.act_fetch = self.menu.addAction(Theme.get_icon("globe", size=16, color=Theme.TEXT_MAIN), 
                           T("discovery.actions.fetch_multi"))
        self.act_fetch.triggered.connect(self.fetch_requested.emit)

        self.act_clear = self.menu.addAction(Theme.get_icon("refresh", size=16, color=Theme.TEXT_MAIN), 
                           T("discovery.actions.clear_match_multi"))
        self.act_clear.triggered.connect(self.clear_requested.emit)
        
        self.act_ignore = self.menu.addAction(Theme.get_icon("trash-2", size=16, color=Theme.TEXT_MAIN), 
                           T("discovery.actions.ignore_multi"))
        self.act_ignore.triggered.connect(self.ignore_requested.emit)
        
        self.btn_more.setMenu(self.menu)

        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.btn_restore)
        layout.addWidget(self.btn_more)
        layout.addSpacing(6)
        layout.addWidget(self.btn_identify)
        layout.addSpacing(6)
        layout.addWidget(self.btn_actions)

    def set_selection_count(self, count, is_trash=False, category='video'):
        self.label.setText(T("discovery.messages.items_selected", count=count))
        self.btn_restore.setVisible(is_trash)
        
        # Category-based visibility
        is_video = category == 'video'
        self.btn_identify.setVisible(not is_trash and is_video)
        
        # Batch Actions and More menu
        self.btn_actions.setVisible(not is_trash)
        self.btn_more.setVisible(not is_trash)
        
        self.act_fetch.setVisible(is_video)
        self.act_clear.setVisible(is_video)
        self.act_ignore.setVisible(True)
        
        self.setVisible(count > 1)

    def refresh_style(self):
        self.setStyleSheet(Theme.get_batch_bar_style())
        self.label.setStyleSheet(Theme.get_batch_label_style())
        self.menu.setStyleSheet(Theme.get_context_menu_style())
