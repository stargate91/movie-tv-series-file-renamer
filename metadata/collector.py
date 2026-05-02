import os
import logging

logger = logging.getLogger(__name__)

def is_video_file(file_path, valid_extensions):
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension in valid_extensions:
        # Hard floor of 1MB to avoid system/junk files, 
        # but allow small samples/extras to be captured.
        try:
            file_size = os.path.getsize(file_path)
            return file_size >= (1 * 1024 * 1024) 
        except:
            return False
    return False

def get_video_files(directory, min_size_bytes, root_folder, valid_extensions):
    video_files = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path) and is_video_file(file_path, valid_extensions):
            rel_path = os.path.relpath(file_path, os.path.dirname(root_folder))
            logger.info(f"Processing file: {rel_path}")
            video_files.append(file_path)

    video_files = sorted(video_files)
    
    return video_files

def get_all_video_files(root_folder, vid_size, recursive, valid_extensions):
    """Generator that yields found video files one by one."""
    if recursive:
        print(f"DEBUG: Starting recursive scan (os.walk) of {root_folder}")
        for root, dirs, files in os.walk(root_folder):
            for file in files:
                file_path = os.path.join(root, file)
                if is_video_file(file_path, valid_extensions):
                    yield os.path.abspath(os.path.normpath(file_path))
    else:
        try:
            print(f"DEBUG: Starting shallow scan (os.listdir) of {root_folder}")
            for file in os.listdir(root_folder):
                file_path = os.path.join(root_folder, file)
                if os.path.isfile(file_path) and is_video_file(file_path, valid_extensions):
                    yield os.path.abspath(os.path.normpath(file_path))
        except:
            pass

