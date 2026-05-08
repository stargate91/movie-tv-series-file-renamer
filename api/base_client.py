import requests
import logging
import time
import threading
from core.exceptions import APIAuthError, NetworkConnectionError, AppError

logger = logging.getLogger(__name__)

class BaseClient:
    """
    Base class for API clients with shared session, caching, and rate-limiting.
    """
    _session_internal = None
    _lock = threading.Lock()

    @property
    def _session(self):
        """Thread-safe access to the shared session, with auto-initialization."""
        if BaseClient._session_internal is None:
            with BaseClient._lock:
                if BaseClient._session_internal is None:
                    BaseClient._session_internal = requests.Session()
        return BaseClient._session_internal

    @classmethod
    def reset_session(cls):
        """Clears the shared session, forcing a new one on next access."""
        with cls._lock:
            cls._session_internal = None

    def __init__(self, db=None, min_interval=0.1):
        self.db = db
        self.min_interval = min_interval
        self._last_request_time = 0
        # Access the property once to ensure it's initialized
        _ = self._session

    def _throttle(self):
        """Ensures a minimum interval between requests."""
        with self._lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_request_time = time.time()

    def _get_from_api(self, api_url, cache_key, headers=None, params=None, required_keys=None, bypass_cache=False):
        # 1. Cache Check
        if self.db and not bypass_cache:
            cached_data = self.db.get_api_cache(cache_key)
            if cached_data:
                if required_keys and isinstance(cached_data, dict):
                    missing = [k for k in required_keys if k not in cached_data]
                    if not missing:
                        logger.debug(f"Cache hit: {cache_key}")
                        return cached_data
                    logger.info(f"Cache stale (missing {missing}), re-fetching: {cache_key}")
                    self.db.delete_api_cache(cache_key)
                else:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_data

        # 2. Throttling & Network Request with Retries
        max_retries = 3
        retry_delay = 2 # seconds
        
        for attempt in range(max_retries):
            try:
                self._throttle()
                response = self._session.get(api_url, headers=headers, params=params, timeout=15)
                
                if response.status_code in (401, 403):
                    raise APIAuthError(f"API Authentication failed (Status: {response.status_code}). Check keys.")
                
                # If it's a server error (500, 502, 503, 504), we retry
                if response.status_code >= 500:
                    if attempt < max_retries - 1:
                        logger.warning(f"Server Error {response.status_code} for {cache_key}. Retrying in {retry_delay}s... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2 # Exponential backoff
                        continue
                
                response.raise_for_status()
                data = response.json()

                # 3. Store in Cache
                if self.db:
                    self.db.set_api_cache(cache_key, data)
                return data

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Network error for {cache_key}: {e}. Retrying... ({attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise NetworkConnectionError(f"Failed to connect to API after {max_retries} attempts: {str(e)}")
            except APIAuthError:
                raise
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1 and hasattr(e, 'response') and e.response is not None and e.response.status_code >= 500:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                logger.error(f"API request failed for {cache_key}: {str(e)}")
                raise AppError(f"API request failed: {str(e)}")
            except ValueError as e:
                logger.error(f"API JSON parse failed for {cache_key}: {str(e)}")
                raise AppError(f"Invalid API response format: {str(e)}")
        
        return None
