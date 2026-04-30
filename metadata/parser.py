from guessit import guessit
import logging

logger = logging.getLogger(__name__)

def extract_extra_metadata(file, unknown_files, file_name, folder_name):
    # Probing both
    file_result = guessit(file_name)
    folder_result = guessit(folder_name)

    # Smart Merge: Start with folder, overwrite with file (file has priority)
    merged = folder_result.copy()
    merged.update(file_result)

    file_type = merged.get('type', 'unknown')

    if file_type not in ["movie", "episode"]:
        logger.warning(f"Unknown file type for {file}: {file_type}")
        unknown_files.append(file)
        return None

    # We return the merged result for extras, 
    # but keep originals for the fallback API logic if needed
    
    # Filter out internal keys for 'extras'
    internal_keys = ['type']
    merged_extras = {k: v for k, v in merged.items() if k not in internal_keys}

    logger.debug(f"Metadata merged for: {file}")
    return file_result, folder_result, file_type, merged_extras
