class UIStyles:
    MAIN_WINDOW = """
        QMainWindow {
            background-color: #ffffff;
        }
        QWidget#MainArea {
            background-color: #ffffff;
        }
    """
    
    CARD_BASE = """
        QFrame#Card {
            border-radius: 8px;
        }
    """
    
    PRIMARY_BUTTON = """
        QPushButton#PrimaryBtn {
            background-color: #0078d4;
            color: white;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: 600;
        }
        QPushButton#PrimaryBtn:hover {
            background-color: #005a9e;
        }
        QPushButton#PrimaryBtn:disabled {
            background-color: #e2e8f0;
            color: #94a3b8;
        }
    """
    
    SECONDARY_BUTTON = """
        QPushButton#SecondaryBtn {
            background-color: #ffffff;
            color: #334155;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: 500;
        }
        QPushButton#SecondaryBtn:hover {
            background-color: #f8fafc;
            border-color: #94a3b8;
        }
    """

    DANGER_BUTTON = """
        QPushButton#DangerBtn {
            background-color: #ef4444;
            color: white;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: 600;
        }
        QPushButton#DangerBtn:hover {
            background-color: #dc2626;
        }
    """
    
    INSPECTOR_PANEL = """
        QWidget#InspectorPanel {
            background-color: #ffffff;
            border-left: 1px solid #cbd5e1;
        }
        QLabel { color: #0f172a; }
        QLabel#Title { font-size: 16px; font-weight: 700; color: #0078d4; }
        QLabel#SubTitle { color: #64748b; font-size: 10px; text-transform: uppercase; font-weight: 700; letter-spacing: 1px; }
        
        QLineEdit {
            background-color: #fcfcfc;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            padding: 8px 10px;
            color: #0f172a;
        }
        QLineEdit:focus { border-color: #0078d4; background-color: #ffffff; }
        
        QComboBox {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
            padding: 6px 10px;
            color: #0f172a;
        }
        QListWidget {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 4px;
        }
        QListWidget::item {
            padding: 8px;
            border-bottom: 1px solid #f1f5f9;
        }
        QListWidget::item:selected {
            background-color: #eff6ff;
            color: #0078d4;
            border-left: 3px solid #0078d4;
        }
    """
    
    SCROLL_AREA = """
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        QScrollBar:vertical {
            border: none;
            background: #f8fafc;
            width: 8px;
        }
        QScrollBar::handle:vertical {
            background: #cbd5e1;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover {
            background: #94a3b8;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """

    PROGRESS_BAR = """
        QProgressBar {
            background-color: #f1f5f9;
            border-radius: 4px;
            border: none;
        }
        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 4px;
        }
    """

    SIDEBAR = """
        QWidget#Sidebar {
            background-color: #ffffff;
            border-right: 1px solid #cbd5e1;
        }
        QLabel#SidebarTitle {
            font-size: 20px;
            font-weight: 800;
            color: #1e293b;
            letter-spacing: -0.5px;
        }
        QLabel#SidebarTagline {
            font-size: 10px;
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        QLabel#StatLabel {
            color: #475569;
            font-size: 11px;
            font-weight: 700;
            margin-bottom: 2px;
        }
        QPushButton#SidebarToggle {
            background: #f1f5f9;
            color: #475569;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 18px;
            font-weight: bold;
        }
        QPushButton#SidebarToggle:hover {
            background: #e2e8f0;
            color: #6366f1;
        }
    """

    SIDEBAR_BUTTON = """
        QPushButton#SidebarBtn {
            background-color: #f8fafc;
            color: #334155;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 10px 14px;
            text-align: left;
            font-size: 13px;
            font-weight: 600;
        }
        QPushButton#SidebarBtn:hover {
            background-color: #ffffff;
            color: #0078d4;
            border-color: #0078d4;
        }
        QPushButton#SidebarBtn:pressed {
            background-color: #f1f5f9;
        }
        QPushButton#SidebarBtn:disabled {
            background-color: #f1f5f9;
            color: #94a3b8;
            border-color: #e2e8f0;
        }
        
        /* Action Colors */
        QPushButton#SidebarBtn[action="primary"] {
            background-color: #0078d4;
            color: white;
            border-color: #0078d4;
        }
        QPushButton#SidebarBtn[action="primary"]:hover {
            background-color: #005a9e;
        }
        
        QPushButton#SidebarBtn[action="success"] {
            background-color: #10b981;
            color: white;
            border-color: #059669;
        }
        QPushButton#SidebarBtn[action="success"]:hover {
            background-color: #059669;
        }

        QPushButton#SidebarBtn[action="danger"] {
            color: #ef4444;
            border-color: #fecaca;
        }
        QPushButton#SidebarBtn[action="danger"]:hover {
            background-color: #fef2f2;
            color: #dc2626;
            border-color: #ef4444;
        }
    """

    FILTER_PILL = """
        QPushButton#FilterPill {
            background-color: #f1f5f9;
            color: #475569;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 5px 12px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        QPushButton#FilterPill:hover {
            background-color: #e2e8f0;
            color: #0f172a;
        }
        QPushButton#FilterPill[active="true"] {
            background-color: #0078d4;
            color: #ffffff;
            border-color: #0078d4;
        }
        QLabel#PillCount {
            background-color: rgba(0, 0, 0, 0.1);
            color: inherit;
            border-radius: 8px;
            padding: 1px 6px;
            font-size: 10px;
            font-weight: 800;
        }
    """

    SEPARATOR = """
        QFrame#Separator {
            background-color: #cbd5e1;
        }
    """

    FOLDER_LABEL = "color: #64748b; font-style: italic; font-size: 13px;"
    STATUS_LABEL = "color: #94a3b8; font-size: 11px; margin-top: 5px;"
    LIVE_MODE_CHECKBOX = "color: #475569; font-weight: bold; font-size: 12px;"
    
    CLEAR_CACHE_BUTTON = """
        QPushButton { 
            background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; 
            border-radius: 6px; font-size: 11px; margin-top: 10px; padding: 6px;
        }
        QPushButton:hover { background: #e2e8f0; color: #0f172a; border-color: #cbd5e1; }
    """

    @staticmethod
    def get_card_style(is_extra=False, is_active=False):
        bg = "#f0f9ff" if is_extra else "#ffffff"
        border = "#0078d4" if is_active else "#cbd5e1"
        border_width = "2px" if is_active else "1px"
        
        return f"""
            QFrame#Card {{
                background-color: {bg};
                border: {border_width} solid {border};
                border-radius: 8px;
            }}
            QFrame#Card:hover {{
                border-color: #0078d4;
                background-color: #f8fafc;
            }}
        """
