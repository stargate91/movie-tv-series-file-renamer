import json
import os
import logging

logger = logging.getLogger(__name__)

class Translator:
    """
    Singleton translator for handling multi-language support via JSON.
    Usage: T("sidebar.dashboard")
    """
    _instance = None

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(Translator, cls).__new__(cls)
            cls._instance.data = {}
            cls._instance.current_locale = 'en'
            cls._instance._load_initial()
        return cls._instance

    def _load_initial(self):
        # Determine path to locales
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        locales_dir = os.path.join(base_dir, 'resources', 'locales')
        os.makedirs(locales_dir, exist_ok=True)
        
        self.locales_path = locales_dir
        self.load_locale(self.current_locale)

    def load_locale(self, locale):
        """Loads a JSON locale file into memory."""
        path = os.path.join(self.locales_path, f"{locale}.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                self.current_locale = locale
                logger.info(f"Loaded locale: {locale}")
            except Exception as e:
                logger.error(f"Failed to load locale {locale}: {e}")
        else:
            # Create empty if not exists for 'en'
            if locale == 'en':
                self.data = {}
                self._save_locale('en')

    def _save_locale(self, locale):
        path = os.path.join(self.locales_path, f"{locale}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def get(self, key, **kwargs):
        """
        Retrieves a translated string. Supports nesting (e.g. 'ui.buttons.ok')
        and formatting (e.g. T('msg', count=5)).
        """
        keys = key.split('.')
        val = self.data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                val = None
                break
        
        if val is None:
            return key # Fallback to the key itself
        
        if kwargs:
            try:
                return val.format(**kwargs)
            except Exception:
                return val
        return val

# Global shorthand
translator = Translator()
T = translator.get
