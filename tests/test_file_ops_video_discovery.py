import os
import tempfile
import pytest

from file_ops import get_vid_files_all

def is_vid_file(path, min_size_bytes):
    _, ext = os.path.splitext(path)
    return ext.lower() in [".mp4", ".mkv", ".avi"] and os.path.getsize(path) >= min_size_bytes

def proc_file_msg(path, root_folder):
    pass

def make_file(path, size_bytes):
    with open(path, "wb") as f:
        f.write(b"x" * size_bytes)

@pytest.mark.parametrize("setup_files, recursive, expected", [
    # 📂 1. Üres mappa
    ([], False, []),

    # 📂 2. Csak nem-videó fájlok
    ([("file.txt", 2_000_000)], False, []),

    # 📂 3. Egy videó, de túl kicsi
    ([("video.mp4", 500_000)], False, []),

    # 📂 4. Egy érvényes videófájl
    ([("movie.mkv", 2_000_000)], False, ["movie.mkv"]),

    # 📂 5. Több fájl, vegyes kiterjesztéssel és mérettel
    ([("movie1.mp4", 2_000_000), ("note.txt", 2_000_000), ("small.avi", 300_000)], False, ["movie1.mp4"]),

    # 📂 6. Almappás fájl, recursive=False → nem találja meg
    ([("sub/video1.mkv", 2_000_000)], False, []),

    # 📂 7. Almappás fájl, recursive=True → megtalálja
    ([("sub/video1.mkv", 2_000_000)], True, ["sub/video1.mkv"]),

    # 📂 8. Több szint mélység recursive=True
    ([("a/b/c/d/video2.mp4", 3_000_000)], True, ["a/b/c/d/video2.mp4"]),

    # 📂 9. Bonyolult fájlnév
    ([("some-cool_movie 2 👽.avi", 2_000_000)], False, ["some-cool_movie 2 👽.avi"]),
])
def test_get_vid_files_all_corner_cases(setup_files, recursive, expected, monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        # GIVEN: fájlszerkezet
        for rel_path, size in setup_files:
            abs_path = os.path.join(tmpdir, rel_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            make_file(abs_path, size)

        monkeypatch.setattr("file_ops.is_vid_file", is_vid_file)
        monkeypatch.setattr("file_ops.proc_file_msg", proc_file_msg)

        # WHEN: videófájlok lekérdezése
        result = get_vid_files_all(tmpdir, vid_size=1, recursive=recursive)

        # THEN: relatív elérési utak összehasonlítása
        rel_result = [os.path.relpath(f, tmpdir).replace("\\", "/") for f in result]
        expected = [e.replace("\\", "/") for e in expected]

        assert sorted(rel_result) == sorted(expected)
