from guessit import guessit

def extract_extra_metadata(file, unknown_files, file_name, folder_name):
    file_result = guessit(file_name)
    folder_result = guessit(folder_name)

    file_type = file_result.get('type', 'unknown')

    if file_type not in ["movie", "episode"]:
        print(f"[WARNING] Unknown file type for {file}: {file_type}")
        unknown_files.append(file)
        return None

    keys = [
        'title', 'year', 'season', 'episode', 'type',
        'screen_size', 'video_codec', 'audio_codec',
        'audio_channels', 'language'
    ]

    file_extras = {k: v for k, v in file_result.items() if k not in keys}
    folder_extras = {k: v for k, v in folder_result.items() if k not in keys}

    merged_extras = folder_extras.copy()
    merged_extras.update(file_extras)

    print(f"\nExtra metadata extracted from file and folder names for:\n   {file}")
    print("These will be included in the final metadata:")
    for k, v in merged_extras.items():
        print(f"   • {k.ljust(16)}: {v}")

    return file_result, folder_result, file_type, merged_extras
