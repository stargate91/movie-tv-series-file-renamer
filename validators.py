import os

def is_video_file(file_path, min_size_bytes):
    file_extension = os.path.splitext(file_path)[1].lower()
    valid_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.mpeg', '.mpg']

    if file_extension in valid_extensions:
        file_size = os.path.getsize(file_path)
        return file_size >= min_size_bytes
    return False