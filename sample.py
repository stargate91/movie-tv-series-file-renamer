import os

def expand_sample_keywords(keywords_raw):
        if isinstance(keywords_raw, str):
            keywords = [kw.strip().lower() for kw in keywords_raw.split(",")]
        else:
            keywords = [kw.strip().lower() for kw in keywords_raw]

        expanded = []
        for kw in keywords:
            expanded.extend([kw, f"{kw}_", f"{kw}-"])
        return expanded

def is_sample_file(file_name, sample_keywords):
    file_name_lower = file_name.lower()
    return any(kw in file_name_lower for kw in sample_keywords)

def collect_sample_videos(root_folder, recursive, sample_keywords):
    valid_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.mpeg', '.mpg']
    sample_video_files = []

    def is_valid_sample(file_path, file_name):
        ext = os.path.splitext(file_name)[1].lower()
        return ext in valid_extensions and is_sample_file(file_name, sample_keywords)

    if recursive:
        for root, dirs, files in os.walk(root_folder):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path) and is_valid_sample(file_path, file):
                    sample_video_files.append(file_path)
    else:
        for file in os.listdir(root_folder):
            file_path = os.path.join(root_folder, file)
            if os.path.isfile(file_path) and is_valid_sample(file_path, file):
                sample_video_files.append(file_path)

    return sorted(sample_video_files)

def sample_files_summary(sample_files):
    print("[INFO] Found the following sample files (typically previews or trial clips):\n")
    for file in sample_files:
        print(f" - {file}")
    print(f"\nTotal sample files found: {len(sample_files)}\n")
    #print("You may choose to delete or handle these files differently to keep your library organized.\n")

