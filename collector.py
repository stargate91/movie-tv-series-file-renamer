from ui_ux import processing_file_message
import os

def is_video_file(file_path, min_size_bytes):
    file_extension = os.path.splitext(file_path)[1].lower()
    valid_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.mpeg', '.mpg']

    if file_extension in valid_extensions:
        file_size = os.path.getsize(file_path)
        return file_size >= min_size_bytes
    return False

def get_video_files(directory, min_size_bytes, root_folder):
    video_files = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path) and is_video_file(file_path, min_size_bytes):
            processing_file_message(file_path, root_folder)
            video_files.append(file_path)

    video_files = sorted(video_files)
    
    return video_files

def get_all_video_files(root_folder, vid_size, recursive):
    min_size_mb = vid_size
    min_size_bytes = min_size_mb * 1024 * 1024

    video_files = []

    if recursive:
        for root, dirs, files in os.walk(root_folder):
            video_files.extend(get_video_files(root, min_size_bytes, root_folder))
    else:
        video_files.extend(get_video_files(root_folder, min_size_bytes, root_folder))

    return video_files
