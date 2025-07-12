import os

def check_if_video_file(file_path, min_size_bytes):
    file_extension = os.path.splitext(file_path)[1].lower()
    valid_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.mpeg', '.mpg']

    if file_extension in valid_extensions:
        file_size = os.path.getsize(file_path)
        return file_size >= min_size_bytes
    return False

def get_video_files_from_directory(directory, min_size_bytes):
    video_files = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path) and check_if_video_file(file_path, min_size_bytes):
            video_files.append(file_path)

    video_files = sorted(video_files)
    
    return video_files

def get_video_files(root_folder, recursive):
    min_size_mb = 500
    min_size_bytes = min_size_mb * 1024 * 1024

    video_files = []

    if recursive:
        for root, dirs, files in os.walk(root_folder):
            video_files.extend(get_video_files_from_directory(root, min_size_bytes))
    else:
        video_files.extend(get_video_files_from_directory(root_folder, min_size_bytes))

    return video_files
