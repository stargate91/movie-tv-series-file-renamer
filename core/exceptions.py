class AppError(Exception):
    """Alap kivétel osztály minden saját alkalmazás hibához."""
    pass

class ConfigError(AppError):
    """Konfigurációval kapcsolatos hiba."""
    pass

class APIKeyMissingError(ConfigError):
    """Hiányzó vagy érvénytelen API kulcsok."""
    pass

class APIAuthError(AppError):
    """Az API elutasította a hívást (pl. lejárt vagy érvénytelen kulcs, 401/403)."""
    pass

class NetworkConnectionError(AppError):
    """Hálózati csatlakozási hiba (nincs internet)."""
    pass
