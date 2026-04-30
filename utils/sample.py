import os
import logging

logger = logging.getLogger(__name__)

def expand_sample_keywords(keywords_raw):
        if isinstance(keywords_raw, str):
            keywords = [kw.strip().lower() for kw in keywords_raw.split(",")]
        else:
            keywords = [kw.strip().lower() for kw in keywords_raw]

        expanded = []
        for kw in keywords:
            expanded.extend([kw, f"{kw}_", f"{kw}-"])
        return expanded

def is_sample_file(file_name, parent_folder_name, sample_keywords):
    name_lower = file_name.lower()
    folder_lower = parent_folder_name.lower()
    return any(kw in name_lower or kw in folder_lower for kw in sample_keywords)

def collect_sample_videos(root_folder, recursive, sample_keywords, vid_size_mb):
    valid_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.mpeg', '.mpg']
    sample_video_files = []
    min_size_bytes = vid_size_mb * 1024 * 1024

    def get_video_files_in_dir(directory):
        videos = []
        try:
            for file in os.listdir(directory):
                ext = os.path.splitext(file)[1].lower()
                if ext in valid_extensions:
                    file_path = os.path.join(directory, file)
                    if os.path.isfile(file_path):
                        videos.append((file_path, file, os.path.getsize(file_path)))
        except PermissionError:
            pass
        return videos

    dir_max_sizes = {}
    all_videos = []

    # 1. Collect all videos and record max sizes per directory
    if recursive:
        for root, dirs, files in os.walk(root_folder):
            videos = get_video_files_in_dir(root)
            max_s = max([v[2] for v in videos]) if videos else 0
            dir_max_sizes[root] = max_s
            for v in videos:
                all_videos.append((root, v[0], v[1], v[2]))
    else:
        root = root_folder
        videos = get_video_files_in_dir(root)
        max_s = max([v[2] for v in videos]) if videos else 0
        dir_max_sizes[root] = max_s
        for v in videos:
            all_videos.append((root, v[0], v[1], v[2]))

    # 2. Evaluate each video
    for root, file_path, file_name, file_size in all_videos:
        parent_folder_name = os.path.basename(root)
        
        # Condition 1: Keyword match in filename OR parent folder name
        is_keyword_match = is_sample_file(file_name, parent_folder_name, sample_keywords)
        
        # Condition 2: Size match
        # Check if the current dir OR its parent dir contains a main feature (>= vid_size)
        parent_dir = os.path.dirname(root)
        local_max = dir_max_sizes.get(root, 0)
        parent_max = dir_max_sizes.get(parent_dir, 0)
        context_max = max(local_max, parent_max)
        
        is_size_match = (context_max >= min_size_bytes) and (file_size < min_size_bytes)
        
        # Safety: if this file IS the local max, it's not a sample based on size
        # (unless it's in a subfolder and the parent has the main feature)
        if file_size == local_max and context_max == local_max and not is_keyword_match:
            continue

        if is_keyword_match or is_size_match:
            sample_video_files.append(file_path)

    return sorted(sample_video_files)

def sample_files_summary(sample_files):
    logger.info("Found the following sample files (typically previews or trial clips):")
    for file in sample_files:
        logger.info(f" - {file}")
    logger.info(f"Total sample files found: {len(sample_files)}")

