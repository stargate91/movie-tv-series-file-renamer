import os
import logging
from utils.cache import DataStore

logger = logging.getLogger(__name__)


def get_history_list():
    """Returns a list of all available history timestamps (keys) from DataStore."""
    store = DataStore("history")
    return store.get_keys()


def get_history_details(timestamp):
    """Returns the list of renames for a specific history timestamp."""
    store = DataStore("history")
    return store.get(timestamp) or []


def execute_undo(items_to_undo):
    """
    Executes undo on a list of items.
    Each item must be a tuple or dict containing at least old_path and new_path.
    Returns (success_count, fail_count)
    """
    success_count = 0
    fail_count = 0

    for record in items_to_undo:
        # Support both tuple/list and dict formats
        if isinstance(record, (list, tuple)) and len(record) >= 2:
            old_path, new_path = record[0], record[1]
        elif isinstance(record, dict):
            old_path = record.get("old_path")
            new_path = record.get("new_path")
        else:
            logger.warning(f"Skipping invalid entry: {record}")
            continue

        if not old_path or not new_path:
            logger.warning(f"Skipping invalid entry: {record}")
            continue

        if not os.path.exists(new_path):
            logger.warning(f"File not found, skipping: {new_path}")
            fail_count += 1
            continue

        try:
            os.renames(new_path, old_path)
            logger.info(f"[UNDO] {new_path} -> {old_path}")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to undo rename for {new_path}: {e}")
            fail_count += 1

    return success_count, fail_count


def undo_rename(history_file=None, use_emojis=False):
    """
    Legacy CLI wrapper for undo functionality.
    """
    histories = get_history_list()
    if not histories:
        logger.error("No valid rename history found in DataStore.")
        return

    latest = histories[0]
    logger.info(f"Undoing renames using latest history: {latest}")

    history_data = get_history_details(latest)
    if not isinstance(history_data, list):
        logger.error("Invalid history format. Expected a list of rename records.")
        return

    success_count, fail_count = execute_undo(history_data)

    logger.info(f"Undo complete! Renames restored: {success_count}")
    if fail_count:
        logger.warning(f"Failures: {fail_count}")
