from abc import ABC, abstractmethod

class UIInterface(ABC):
    """
    Absztrakt interfész, amely leírja, hogyan kommunikálhat a logika a felhasználóval.
    Ezt fogja megvalósítani a CLI (ui_ux.py) és később a GUI (gui.py) is.
    """

    @abstractmethod
    def show_message(self, message: str, level: str = "info"):
        """Üzenet megjelenítése (info, warning, error, success)."""
        pass

    @abstractmethod
    def ask_selection(self, options: list, prompt: str) -> int:
        """Választás kérése a felhasználótól egy listából."""
        pass

    @abstractmethod
    def ask_input(self, prompt: str, default: str = "") -> str:
        """Szöveges beviteli mező kérése."""
        pass

    @abstractmethod
    def ask_decision(self, prompt: str, options: list) -> str:
        """Egyszerű döntés kérése (pl: y/n/c)."""
        pass

    @abstractmethod
    def update_progress(self, current: int, total: int, status: str = ""):
        """Folyamatjelző frissítése."""
        pass
