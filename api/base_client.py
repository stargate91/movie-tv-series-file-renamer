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
    _session = None
    _lock = threading.Lock()

    def __init__(self, db=None, min_interval=0.1):
        self.db = db
        self.min_interval = min_interval
        self._last_request_time = 0
        
        if BaseClient._session is None:
            BaseClient._session = requests.Session()

    def _throttle(self):
        """Ensures a minimum interval between requests."""
        with self._lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_request_time = time.time()

    def _get_from_api(self, api_url, cache_key, headers=None, params=None, required_keys=None):
        # 1. Cache Check
        if self.db:
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

        # 2. Throttling
        self._throttle()

        # 3. Network Request
        try:
            response = self._session.get(api_url, headers=headers, params=params, timeout=10)
            
            if response.status_code in (401, 403):
                raise APIAuthError(f"API Authentication failed (Status: {response.status_code}). Check keys.")
                
            response.raise_for_status()
            data = response.json()

            # 4. Store in Cache
            if self.db:
                self.db.set_api_cache(cache_key, data)
            return data

        except APIAuthError:
            raise
        except requests.exceptions.ConnectionError as e:
            raise NetworkConnectionError(f"Failed to connect to API: {str(e)}")
        except requests.exceptions.Timeout:
            raise NetworkConnectionError(f"API request timed out for {cache_key}")
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {cache_key}: {str(e)}")
            raise AppError(f"API request failed: {str(e)}")
        except ValueError as e:
            logger.error(f"API JSON parse failed for {cache_key}: {str(e)}")
            raise AppError(f"Invalid API response format: {str(e)}")
