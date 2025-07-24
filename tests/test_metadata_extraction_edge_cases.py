import os
import tempfile
import pytest
from meta import extract_metadata

def make_dummy_file(path, name, size=2_000_000):
    file_path = os.path.join(path, name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(b"x" * size)
    return file_path

class DummyAPIClient:
    def __init__(self, behavior):
        self.behavior = behavior

    def get_from_tmdb_movie(self, title, year):
        return self.behavior.get("movie", None)

    def get_from_tmdb_tv(self, title, year):
        return self.behavior.get("tv", None)

@pytest.mark.parametrize("file_name, file_type, api_behavior, expected_counts, description", [
    # 1. Egy film, egy találat
    ("Inception.2010.mkv", "movie", {"movie": {"total_results": 1, "results": [{"id": 1}]}}, [1, 0, 0, 0, 0, 0, 0], "🎬 Egyértelmű film"),

    # 2. Egy film, több találat
    ("Matrix.1999.mp4", "movie", {"movie": {"total_results": 3, "results": [{"id": 1}, {"id": 2}, {"id": 3}]}}, [0, 0, 1, 0, 0, 0, 0], "🎬 Több találatos film"),

    # 3. Egy film, nincs találat
    ("UnknownMovie.2077.avi", "movie", {"movie": None}, [0, 1, 0, 0, 0, 0, 0], "❌ Nincs találat filmre"),

    # 4. Epizód, egy találat
    ("Breaking.Bad.S01E01.mkv", "episode", {"tv": {"total_results": 1, "results": [{"id": 101}]}}, [0, 0, 0, 1, 0, 0, 0], "📺 Epizód egy találattal"),

    # 5. Epizód, több találat
    ("Lost.S02E03.mp4", "episode", {"tv": {"total_results": 4, "results": [{"id": i} for i in range(4)]}}, [0, 0, 0, 0, 0, 1, 0], "📺 Epizód több találattal"),

    # 6. Epizód, nincs találat
    ("FakeShow.S01E01.avi", "episode", {"tv": None}, [0, 0, 0, 0, 1, 0, 0], "❌ Nincs találat epizódra"),

    # 7. Ismeretlen fájltípus
    ("some_random_file.xyz", "unknown", {}, [0, 0, 0, 0, 0, 0, 1], "🪲 Ismeretlen fájltípus"),

    # 8. Üres fájllista
    (None, None, {}, [0, 0, 0, 0, 0, 0, 0], "📁 Üres fájllista"),

    # 9. Hiányos metaadat (nincs év)
    ("Gladiator.avi", "movie", {"movie": {"total_results": 1, "results": [{"id": 10}]}}, [1, 0, 0, 0, 0, 0, 0], "❗ Hiányzó év metaadat"),
])
def test_extract_metadata_edge_cases(monkeypatch, file_name, file_type, api_behavior, expected_counts, description):
    # GIVEN
    if file_name:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = make_dummy_file(tmpdir, file_name)

            def dummy_guessit(name):
                if file_type == "movie":
                    return {"title": "Dummy", "year": 2000, "type": "movie"} if "Gladiator" not in name else {"title": "Gladiator", "type": "movie"}
                elif file_type == "episode":
                    return {"title": "DummyShow", "year": 2010, "season": 1, "episode": 1, "type": "episode"}
                return {"type": "unknown"}

            monkeypatch.setattr("meta.guessit", dummy_guessit)

            api_client = DummyAPIClient(api_behavior)

            # WHEN
            result = extract_metadata(
                video_files=[file_path],
                api_client=api_client,
                api_source="tmdb",
                source_mode="fallback"
            )
    else:
        # Üres fájllista eset
        api_client = DummyAPIClient(api_behavior)
        result = extract_metadata(
            video_files=[],
            api_client=api_client,
            api_source="tmdb",
            source_mode="fallback"
        )

    # THEN
    counts = [len(group) for group in result]
    assert counts == expected_counts, f"Hibás eredmény a teszthez: {description}"
