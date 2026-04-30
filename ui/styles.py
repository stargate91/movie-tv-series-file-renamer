QSS = """
QMainWindow {
    background-color: #f3f4f6;
}
#Sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e5e7eb;
}
#MainArea {
    background-color: #f9fafb;
}
QPushButton {
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 8px 16px;
    color: #374151;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #f3f4f6;
    border-color: #9ca3af;
}
QPushButton#PrimaryBtn {
    background-color: #0078d4;
    color: #ffffff;
    border: none;
}
QPushButton#PrimaryBtn:hover {
    background-color: #005a9e;
}
QPushButton#PrimaryBtn:disabled {
    background-color: #cccccc;
    color: #666666;
}
#Card {
    background-color: #ffffff;
    border: 1px solid #e1e1e1;
    border-radius: 8px;
}
#Card:hover {
    border-color: #0078d4;
    background-color: #f9f9f9;
}
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 6px;
    color: #333333;
}
QLineEdit:focus {
    border-color: #0078d4;
}
QListWidget {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    outline: none;
}
QListWidget::item {
    padding: 8px;
}
QListWidget::item:selected {
    background-color: #0078d4;
    color: white;
}
QProgressBar {
    border: 1px solid #cccccc;
    border-radius: 3px;
    text-align: center;
    background-color: #e6e6e6;
}
QProgressBar::chunk {
    background-color: #0078d4;
}
QScrollArea, QScrollArea QWidget {
    background-color: #ffffff;
    border: none;
}
QTabWidget::pane {
    border: 1px solid #cccccc;
    background-color: #ffffff;
}
QTabBar::tab {
    background-color: #f3f3f3;
    padding: 8px 15px;
    border: 1px solid #cccccc;
    border-bottom: none;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    border-bottom: 2px solid #0078d4;
    font-weight: bold;
}
"""
