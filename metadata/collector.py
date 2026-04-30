import os
import logging

logger = logging.getLogger(__name__)

def is_video_file(file_path, min_size_bytes, valid_extensions):
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension in valid_extensions:
        file_size = os.path.getsize(file_path)
        return file_size >= min_size_bytes
    return False

def get_video_files(directory, min_size_bytes, root_folder, valid_extensions):
    video_files = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path) and is_video_file(file_path, min_size_bytes, valid_extensions):
            rel_path = os.path.relpath(file_path, os.path.dirname(root_folder))
            logger.info(f"Processing file: {rel_path}")
            video_files.append(file_path)

    video_files = sorted(video_files)
    
    return video_files

def get_all_video_files(root_folder, vid_size, recursive, valid_extensions):
    min_size_mb = vid_size
    min_size_bytes = min_size_mb * 1024 * 1024

    video_files = []

    if recursive:
        for root, dirs, files in os.walk(root_folder):
            video_files.extend(get_video_files(root, min_size_bytes, root_folder, valid_extensions))
    else:
        video_files.extend(get_video_files(root_folder, min_size_bytes, root_folder, valid_extensions))

    return video_files

