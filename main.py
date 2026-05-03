import sys
from utils.logger import setup_logger
from ui.v3.views.main_window import start_v3_ui

def main():
    # 1. Initialize Global Logging
    setup_logger()
    
    # 2. Launch V3 Modern UI
    start_v3_ui()

if __name__ == "__main__":
    main()
