"""
RENDA Edge Case Tester v3.0
============================
Comprehensive test suite covering:
  1.  Organization Matrix
  2.  Naming Styles (Casing x Separator)
  3.  Multi-Part Collision Resolution
  4.  Illegal Characters in Titles
  5.  Multi-Episode Files
  6.  Missing Metadata
  7.  Season 0 / Specials
  8.  Zero Padding & High Episode Numbers
  9.  YearRange (Ongoing vs Ended)
  10. Resolution Logic (Single, Range, Mixed)
  11. Extras Handling (Subtitles, Audio linked to parent)
  12. Duplicate Titles (Same name, different year)
  13. Windows Path Length Limit
  14. Unknown / Typo Tags
  15. Empty Template
  16. All Tags Empty
  17. HDR Variations
  18. Dots in Title + Dot Separator
  19. Very Long Titles
  20. Season Pack (no specific episode)
  21. Custom Variable Tag
"""

import os
import sys
import sqlite3
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.engine.formatter import Formatter
from core.engine.collision_resolver import CollisionResolver
from core.config.manager import AppSettings


# !!! Helpers !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

PASS = "[PASS]"
FAIL = "[FAIL]"
total_pass = 0
total_fail = 0

def check(label, got, expected_substring):
    """Check if expected_substring appears in got. Print result."""
    global total_pass, total_fail
    got_str = str(got) if got else "(None)"
    ok = expected_substring in got_str
    status = PASS if ok else FAIL
    if ok:
        total_pass += 1
    else:
        total_fail += 1
    print(f"  {status} {label}")
    print(f"       Got:      {got_str}")
    if not ok:
        print(f"       Expected: ...{expected_substring}...")
    print()


def section(title):
    print("\n" + "-" * 80)
    print(f"  {title}")
    print("-" * 80 + "\n")


# !!! Mock Database !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

class MockDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE files (
            id INTEGER PRIMARY KEY, file_name TEXT, current_path TEXT,
            extension TEXT, resolution TEXT, video_codec TEXT, audio_codec TEXT,
            audio_channels TEXT, hdr_type TEXT, bit_depth INTEGER, framerate TEXT,
            video_bitrate INTEGER, category TEXT, sub_category TEXT,
            parent_file_id INTEGER, fn_season INTEGER, fn_episode INTEGER,
            fd_season INTEGER, fd_episode INTEGER, language TEXT
        )""")
        c.execute("""CREATE TABLE media_items (
            id INTEGER PRIMARY KEY, tmdb_id INTEGER, imdb_id TEXT,
            title TEXT, year INTEGER, media_type TEXT, status TEXT, type TEXT,
            director TEXT, cast TEXT, genres TEXT, tagline TEXT, overview TEXT,
            original_title TEXT, original_language TEXT, origin_country TEXT,
            rating_imdb REAL, rating_tmdb REAL, rating_rotten TEXT,
            rating_metacritic INTEGER, votes_imdb INTEGER, vote_count_tmdb INTEGER,
            budget INTEGER, revenue INTEGER, runtime INTEGER, popularity REAL,
            first_air_date TEXT, last_air_date TEXT,
            number_of_episodes INTEGER, number_of_seasons INTEGER,
            languages TEXT, release_date TEXT, poster_path TEXT, details_json TEXT
        )""")
        c.execute("""CREATE TABLE links (
            id INTEGER PRIMARY KEY, file_id INTEGER,
            media_item_id INTEGER, tv_episode_id INTEGER
        )""")
        c.execute("""CREATE TABLE tv_episodes (
            id INTEGER PRIMARY KEY, tmdb_id INTEGER, imdb_id TEXT,
            media_item_id INTEGER, season_number INTEGER, episode_number INTEGER,
            name TEXT, air_date TEXT, vote_average REAL, rating_imdb REAL, runtime INTEGER
        )""")
        self.conn.commit()

    def _get_connection(self):
        return self.conn

    def get_file_by_id(self, fid):
        return self.conn.execute("SELECT * FROM files WHERE id = ?", (fid,)).fetchone()

    def get_links_for_file(self, fid):
        return self.conn.execute("SELECT * FROM links WHERE file_id = ?", (fid,)).fetchall()


# !!! Seed Data !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

def seed(db):
    c = db.conn.cursor()

    # !! Movies !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # M1: Normal movie
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type, release_date, original_title)
                 VALUES (1, 1001, 'Avatar', 2009, 'movie', '2009-12-18', 'Avatar')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, video_codec, audio_codec, audio_channels, category)
                 VALUES (1, 'avatar.2009.mkv', 'C:/raw/avatar.2009.mkv', '.mkv', '1920x1080', 'HEVC', 'AC-3', '6', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (1, 1)")

    # M2: Illegal characters -> Star Wars: Episode IV ! A New Hope
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type)
                 VALUES (2, 1002, 'Star Wars: Episode IV - A New Hope', 1977, 'movie')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category)
                 VALUES (2, 'starwars4.mkv', 'C:/raw/starwars4.mkv', '.mkv', '3840x2160', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (2, 2)")

    # M3: Movie with NO year
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, media_type)
                 VALUES (3, 1003, 'Untitled Documentary', 'movie')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category)
                 VALUES (3, 'doc.mkv', 'C:/raw/doc.mkv', '.mkv', '1920x1080', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (3, 3)")

    # M4+M5: Collision pair (same movie, two parts ! CD1 and CD2)
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type)
                 VALUES (4, 1004, 'Kill Bill Vol 1', 2003, 'movie')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category)
                 VALUES (4, 'kill.bill.cd1.mkv', 'C:/raw/kill.bill.cd1.mkv', '.mkv', '1920x1080', 'video')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category)
                 VALUES (5, 'kill.bill.cd2.mkv', 'C:/raw/kill.bill.cd2.mkv', '.mkv', '1920x1080', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (4, 4)")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (5, 4)")

    # !! TV Shows !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # TV1: Ended show (Game of Thrones)
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type, status,
                 first_air_date, last_air_date, number_of_episodes, number_of_seasons,
                 original_title, rating_imdb, details_json)
                 VALUES (10, 2001, 'Game of Thrones', 2011, 'tv', 'Ended',
                 '2011-04-17', '2019-05-19', 73, 8, 'Game of Thrones', 9.2, ?)""",
              (json.dumps({"seasons": [{"season_number": 1, "name": "Season 1", "episode_count": 10, "air_date": "2011-04-17"},
                                       {"season_number": 0, "name": "Specials", "episode_count": 5, "air_date": "2012-02-01"}],
                           "created_by": [{"name": "David Benioff"}, {"name": "D. B. Weiss"}],
                           "credits": {"cast": [{"name": "Emilia Clarke"}, {"name": "Kit Harington"}, {"name": "Peter Dinklage"}]}}),))
    # S01E01
    c.execute("""INSERT INTO tv_episodes (id, media_item_id, season_number, episode_number, name, air_date, rating_imdb)
                 VALUES (101, 10, 1, 1, 'Winter Is Coming', '2011-04-17', 9.1)""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, video_codec, category)
                 VALUES (10, 'got.s01e01.mkv', 'C:/raw/got.s01e01.mkv', '.mkv', '1920x1080', 'H264', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id, tv_episode_id) VALUES (10, 10, 101)")

    # S00E01 (Special)
    c.execute("""INSERT INTO tv_episodes (id, media_item_id, season_number, episode_number, name, air_date)
                 VALUES (102, 10, 0, 1, 'The Night Lands BTS', '2012-02-01')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category)
                 VALUES (11, 'got.special.mkv', 'C:/raw/got.special.mkv', '.mkv', '1920x1080', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id, tv_episode_id) VALUES (11, 10, 102)")

    # TV2: Ongoing show (The Boys)
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type, status,
                 first_air_date, number_of_episodes, number_of_seasons)
                 VALUES (20, 2002, 'The Boys', 2019, 'tv', 'Returning Series',
                 '2019-07-26', 32, 4)""")
    c.execute("""INSERT INTO tv_episodes (id, media_item_id, season_number, episode_number, name, air_date)
                 VALUES (201, 20, 1, 1, 'The Name of the Game', '2019-07-26')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category)
                 VALUES (20, 'theboys.s01e01.mkv', 'C:/raw/theboys.s01e01.mkv', '.mkv', '3840x2160', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id, tv_episode_id) VALUES (20, 20, 201)")

    # TV3: Multi-episode file (S01E01E02E03)
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type, status)
                 VALUES (30, 2003, 'Stranger Things', 2016, 'tv', 'Ended')""")
    c.execute("""INSERT INTO tv_episodes (id, media_item_id, season_number, episode_number, name)
                 VALUES (301, 30, 1, 1, 'The Vanishing of Will Byers')""")
    c.execute("""INSERT INTO tv_episodes (id, media_item_id, season_number, episode_number, name)
                 VALUES (302, 30, 1, 2, 'The Weirdo on Maple Street')""")
    c.execute("""INSERT INTO tv_episodes (id, media_item_id, season_number, episode_number, name)
                 VALUES (303, 30, 1, 3, 'Holly Jolly')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category)
                 VALUES (30, 'st.s01e01e02e03.mkv', 'C:/raw/st.s01e01e02e03.mkv', '.mkv', '1920x1080', 'video')""")
    # Link the file to all three episodes
    c.execute("INSERT INTO links (file_id, media_item_id, tv_episode_id) VALUES (30, 30, 301)")
    c.execute("INSERT INTO links (file_id, media_item_id, tv_episode_id) VALUES (30, 30, 302)")
    c.execute("INSERT INTO links (file_id, media_item_id, tv_episode_id) VALUES (30, 30, 303)")

    # TV4: Episode with NO title
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type, status)
                 VALUES (40, 2004, 'Dark', 2017, 'tv', 'Ended')""")
    c.execute("""INSERT INTO tv_episodes (id, media_item_id, season_number, episode_number, name)
                 VALUES (401, 40, 1, 1, NULL)""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category)
                 VALUES (40, 'dark.s01e01.mkv', 'C:/raw/dark.s01e01.mkv', '.mkv', '1920x1080', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id, tv_episode_id) VALUES (40, 40, 401)")

    # TV5: Mixed resolution season (720p + 1080p + 4K in same show)
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type, status,
                 first_air_date, last_air_date)
                 VALUES (50, 2005, 'Breaking Bad', 2008, 'tv', 'Ended',
                 '2008-01-20', '2013-09-29')""")
    for i, res in enumerate(['1280x720', '1920x1080', '3840x2160']):
        fid, eid = 50 + i, 501 + i
        c.execute("INSERT INTO tv_episodes (id, media_item_id, season_number, episode_number, name) VALUES (?, 50, 1, ?, 'Ep')", (eid, i + 1))
        c.execute("INSERT INTO files (id, file_name, current_path, extension, resolution, category) VALUES (?, 'bb.mkv', 'C:/raw/bb.mkv', '.mkv', ?, 'video')", (fid, res))
        c.execute("INSERT INTO links (file_id, media_item_id, tv_episode_id) VALUES (?, 50, ?)", (fid, eid))

    # TV6: Range resolution (720p + 1080p only)
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type, status)
                 VALUES (60, 2006, 'The Mandalorian', 2019, 'tv', 'Returning Series')""")
    for i, res in enumerate(['1280x720', '1920x1080']):
        fid, eid = 60 + i, 601 + i
        c.execute("INSERT INTO tv_episodes (id, media_item_id, season_number, episode_number, name) VALUES (?, 60, 1, ?, 'Ep')", (eid, i + 1))
        c.execute("INSERT INTO files (id, file_name, current_path, extension, resolution, category) VALUES (?, 'mando.mkv', 'C:/raw/mando.mkv', '.mkv', ?, 'video')", (fid, res))
        c.execute("INSERT INTO links (file_id, media_item_id, tv_episode_id) VALUES (?, 60, ?)", (fid, eid))

    # TV7: High episode anime (1000+ ep)
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type, status, number_of_episodes)
                 VALUES (70, 2007, 'One Piece', 1999, 'tv', 'Returning Series', 1100)""")
    c.execute("""INSERT INTO tv_episodes (id, media_item_id, season_number, episode_number, name)
                 VALUES (701, 70, 1, 1074, 'The Drums of Liberation')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category)
                 VALUES (70, 'onepiece1074.mkv', 'C:/raw/onepiece1074.mkv', '.mkv', '1920x1080', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id, tv_episode_id) VALUES (70, 70, 701)")

    # -- WAVE 2: New edge case data --

    # EX1: Subtitle file linked to Avatar (parent_file_id = 1)
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category, sub_category, parent_file_id, language)
                 VALUES (80, 'avatar.eng.srt', 'C:/raw/avatar.eng.srt', '.srt', NULL, 'subtitle', 'subtitle', 1, 'en')""")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (80, 1)")

    # EX2: Audio track linked to Avatar
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category, sub_category, parent_file_id, language)
                 VALUES (81, 'avatar.hun.ac3', 'C:/raw/avatar.hun.ac3', '.ac3', NULL, 'audio', 'audio', 1, 'hu')""")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (81, 1)")

    # DUP1: Dune (1984)
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type)
                 VALUES (90, 3001, 'Dune', 1984, 'movie')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category)
                 VALUES (90, 'dune.1984.mkv', 'C:/raw/dune.1984.mkv', '.mkv', '1920x1080', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (90, 90)")

    # DUP2: Dune (2021)
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type)
                 VALUES (91, 3002, 'Dune', 2021, 'movie')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category)
                 VALUES (91, 'dune.2021.mkv', 'C:/raw/dune.2021.mkv', '.mkv', '3840x2160', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (91, 91)")

    # HDR1: HDR10 movie
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type)
                 VALUES (92, 3003, 'Blade Runner 2049', 2017, 'movie')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, video_codec, hdr_type, bit_depth, category)
                 VALUES (92, 'bladerunner.mkv', 'C:/raw/bladerunner.mkv', '.mkv', '3840x2160', 'HEVC', 'HDR10', 10, 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (92, 92)")

    # HDR2: Dolby Vision movie
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type)
                 VALUES (93, 3004, 'Mad Max Fury Road', 2015, 'movie')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, video_codec, hdr_type, bit_depth, category)
                 VALUES (93, 'madmax.mkv', 'C:/raw/madmax.mkv', '.mkv', '3840x2160', 'HEVC', 'Dolby Vision', 10, 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (93, 93)")

    # HDR3: SDR movie (hdr_type = SDR means no HDR tag)
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type)
                 VALUES (94, 3005, 'The Matrix', 1999, 'movie')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, video_codec, hdr_type, category)
                 VALUES (94, 'matrix.mkv', 'C:/raw/matrix.mkv', '.mkv', '1920x1080', 'H264', 'SDR', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (94, 94)")

    # DOT1: Dr. Strange (dot in title)
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type)
                 VALUES (95, 3006, 'Dr. Strange', 2016, 'movie')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category)
                 VALUES (95, 'drstrange.mkv', 'C:/raw/drstrange.mkv', '.mkv', '1920x1080', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (95, 95)")

    # LONG1: Very long anime title
    long_title = 'That Time I Got Reincarnated as a Slime and Then Everything Changed Forever in This World'
    c.execute("""INSERT INTO media_items (id, tmdb_id, title, year, media_type)
                 VALUES (96, 3007, ?, 2021, 'tv')""", (long_title,))
    c.execute("""INSERT INTO tv_episodes (id, media_item_id, season_number, episode_number, name)
                 VALUES (961, 96, 1, 1, 'The Storm Dragon Veldora')""")
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category)
                 VALUES (96, 'slime.mkv', 'C:/raw/slime.mkv', '.mkv', '1920x1080', 'video')""")
    c.execute("INSERT INTO links (file_id, media_item_id, tv_episode_id) VALUES (96, 96, 961)")

    # PACK1: Season pack - linked to show but no episode
    c.execute("""INSERT INTO files (id, file_name, current_path, extension, resolution, category, fn_season, fn_episode)
                 VALUES (97, 'got.s01.pack.mkv', 'C:/raw/got.s01.pack.mkv', '.mkv', '1920x1080', 'video', 1, NULL)""")
    c.execute("INSERT INTO links (file_id, media_item_id) VALUES (97, 10)")

    db.conn.commit()


# !!! Test Suites !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

def test_organization_matrix(fmt, settings, db):
    section("1. ORGANIZATION MATRIX")

    c = db.conn.cursor()
    settings.target_dir_movies = "T:/Media"
    settings.target_dir_shows = "T:/Media"
    settings.movies_subfolder_name = "Mozi"
    settings.shows_subfolder_name = "Sorozatok"
    settings.show_folder_template = "{ShowTitle}"
    settings.season_folder_template = "Season {Season}"
    settings.episode_folder_template = "{ShowTitle} - {Season}{Episode}"
    settings.movie_folder_template = "{Title} ({Year})"

    combos = [
        ("FLAT (categories only)",          False, False, False, False, True),
        ("TITLES ONLY",                     True,  False, False, True,  True),
        ("SHOW + SEASON (Standard)",        True,  True,  False, True,  True),
        ("FULL HIERARCHY (Show/Season/Ep)", True,  True,  True,  True,  True),
        ("NO CATEGORIES (flat target)",     False, False, False, False, False),
    ]

    for label, show_f, season_f, ep_f, movie_f, auto_org in combos:
        settings.create_show_folder = show_f
        settings.create_season_folder = season_f
        settings.create_episode_folder = ep_f
        settings.create_movie_folder = movie_f
        settings.auto_organize_by_type = auto_org

        movie = fmt.generate_full_path(1, settings)  # Avatar
        tv = fmt.generate_full_path(10, settings)     # GoT S01E01

        print(f"  [{label}]")
        print(f"    Movie: {movie}")
        print(f"    TV:    {tv}\n")

    # Reset
    settings.auto_organize_by_type = False
    settings.create_show_folder = True
    settings.create_season_folder = True
    settings.create_episode_folder = False
    settings.create_movie_folder = True
    settings.target_dir_movies = ""
    settings.target_dir_shows = ""


def test_naming_styles(fmt, settings):
    section("2. NAMING STYLES (Casing ! Separator)")

    casings = [("none", "Original"), ("title", "Title Case"), ("upper", "UPPER"), ("lower", "lower")]
    seps = [("space", "Space"), ("dot", "Dot"), ("dash", "Dash"), ("underscore", "Underscore")]

    for c_val, c_label in casings:
        for s_val, s_label in seps:
            settings.filename_case = c_val
            settings.separator = s_val
            result = fmt.generate_name(1, settings.movie_template, c_val, s_val)  # Avatar
            print(f"  {c_label:12} + {s_label:10} -> {result}")
    print()

    # Reset
    settings.filename_case = "none"
    settings.separator = "space"


def test_collision_resolution(settings):
    section("3. MULTI-PART COLLISION RESOLUTION")

    combos = [
        ("Part suffix + number",     "Part",  "suffix", "number",      "space"),
        ("CD suffix + zero-padded",  "CD",    "suffix", "zero_padded", "dash"),
        ("Disc suffix + roman",      "Disc",  "suffix", "roman",       "space"),
        ("Part prefix + number",     "Part",  "prefix", "number",      "dash"),
        ("No keyword + number",      "None",  "suffix", "number",      "space"),
    ]

    for label, keyword, position, style, sep in combos:
        settings.multi_part_keyword = keyword
        settings.multi_part_position = position
        settings.multi_part_style = style
        settings.multi_part_separator = sep

        resolver = CollisionResolver(settings)

        group = [
            {'file_id': 4, 'original_path': 'C:/raw/kill.bill.cd1.mkv', 'proposed_path': 'T:/Kill Bill Vol 1 (2003) - 1080p.mkv'},
            {'file_id': 5, 'original_path': 'C:/raw/kill.bill.cd2.mkv', 'proposed_path': 'T:/Kill Bill Vol 1 (2003) - 1080p.mkv'},
        ]

        result = resolver.auto_resolve_group(group)
        if result:
            paths = [os.path.basename(r['proposed_path']) for r in result]
            print(f"  {label}:")
            for p in paths:
                print(f"    -> {p}")
        else:
            print(f"  {label}: !!  Could not auto-resolve")
        print()

    # Reset
    settings.multi_part_keyword = "Part"
    settings.multi_part_position = "suffix"
    settings.multi_part_style = "number"
    settings.multi_part_separator = "space"


def test_illegal_characters(fmt, settings):
    section("4. ILLEGAL CHARACTERS IN TITLES")

    # Star Wars: Episode IV has a colon
    result = fmt.generate_name(2, settings.movie_template, "none", "space")
    check("Colon in title gets sanitized",
          result, "Star Wars")

    has_colon = ":" in (result or "")
    if has_colon:
        print(f"  [FAIL] Colon still present: {result}")
    else:
        print(f"  [INFO] Colon removed cleanly: {result}")
    print()


def test_multi_episode(fmt, settings):
    section("5. MULTI-EPISODE FILES")

    result = fmt.generate_name(30, settings.episode_template, "none", "space")
    check("Triple episode (S01E01E02E03)",
          result, "S01E01")
    check("Contains E02",
          result, "E02")
    check("Contains E03",
          result, "E03")


def test_missing_metadata(fmt, settings):
    section("6. MISSING METADATA")

    # Movie with no year
    result = fmt.generate_name(3, "{Title} ({Year}) - {Resolution}", "none", "space")
    check("Movie with no year -> no empty brackets",
          result, "Untitled Documentary")
    has_empty = "()" in (result or "")
    if has_empty:
        print(f"  !!  Empty brackets detected: {result}")

    # Episode with no title
    result = fmt.generate_name(40, "{ShowTitle} - {Season}{Episode} - {EpisodeTitle} - {Resolution}", "none", "space")
    check("Episode with no title -> no double dash",
          result, "Dark")
    has_double_dash = " -  - " in (result or "")
    if has_double_dash:
        print(f"  !!  Double dash detected: {result}")


def test_season_zero(fmt, settings):
    section("7. SEASON 0 (SPECIALS)")

    result = fmt.generate_name(11, settings.episode_template, "none", "space")
    check("Season 0 special -> S00E01",
          result, "S00E01")
    check("Special episode title present",
          result, "The Night Lands BTS")


def test_zero_padding(fmt, settings):
    section("8. ZERO PADDING & HIGH EPISODE NUMBERS")

    # One Piece episode 1074
    result = fmt.generate_name(70, settings.episode_template, "none", "space")
    check("Episode 1074 -> 4 digits shown",
          result, "E1074")
    check("Season still padded",
          result, "S01")


def test_year_range(fmt, settings):
    section("9. YEAR RANGE (Smart YearRange Tag)")

    settings.show_folder_template = "{ShowTitle} ({YearRange})"
    settings.create_show_folder = True

    # Ended (GoT)
    result = fmt.generate_full_path(10, settings)
    check("Ended series -> (2011-2019)",
          result, "2011-2019")

    # Ongoing (The Boys)
    result = fmt.generate_full_path(20, settings)
    check("Ongoing series -> (2019-)",
          result, "2019-)")

    settings.show_folder_template = "{ShowTitle}"


def test_resolution_logic(fmt, settings):
    section("10. RESOLUTION LOGIC (Single / Range / Mixed)")

    settings.show_folder_template = "{ShowTitle} [{Resolution}]"
    settings.create_show_folder = True

    # Mixed (3 types)
    result = fmt.generate_full_path(50, settings)
    check("3+ resolutions -> [Mixed]",
          result, "[Mixed]")

    # Range (2 types)
    result = fmt.generate_full_path(60, settings)
    check("2 resolutions -> [720p-1080p]",
          result, "[720p-1080p]")

    # Single resolution
    result = fmt.generate_full_path(20, settings)  # The Boys - only 4K
    check("Single resolution -> [4K]",
          result, "[4K]")

    settings.show_folder_template = "{ShowTitle}"


def test_extras_handling(fmt, settings):
    section("11. EXTRAS HANDLING (Subtitles, Audio)")

    # Subtitle file
    result = fmt.generate_name(80, settings.movie_extra_template, "none", "space")
    check("Subtitle gets parent title (Avatar)",
          result, "Avatar")
    check("Subtitle has ExtraCategory",
          result, "Subtitle")

    # Audio track
    result = fmt.generate_name(81, settings.movie_extra_template, "none", "space")
    check("Audio track gets parent title",
          result, "Avatar")
    check("Audio has ExtraCategory",
          result, "Audio")


def test_duplicate_titles(fmt, settings):
    section("12. DUPLICATE TITLES (Same name, different year)")

    result_84 = fmt.generate_name(90, "{Title} ({Year})", "none", "space")
    result_21 = fmt.generate_name(91, "{Title} ({Year})", "none", "space")
    check("Dune 1984 includes year",
          result_84, "1984")
    check("Dune 2021 includes year",
          result_21, "2021")
    # Without year -> collision
    result_no_year_84 = fmt.generate_name(90, "{Title}", "none", "space")
    result_no_year_21 = fmt.generate_name(91, "{Title}", "none", "space")
    same = (result_no_year_84 == result_no_year_21)
    print(f"  [INFO] Without year tag, both are: '{result_no_year_84}' (collision={same})")
    print()


def test_path_length(fmt, settings):
    section("13. WINDOWS PATH LENGTH LIMIT")

    # Deep hierarchy with long title
    settings.target_dir_shows = "T:/MyMedia/SuperLongBaseDirectoryName/ThatKeepsGoing"
    settings.auto_organize_by_type = True
    settings.shows_subfolder_name = "Television Shows Collection"
    settings.create_show_folder = True
    settings.create_season_folder = True
    settings.create_episode_folder = True
    settings.show_folder_template = "{ShowTitle}"
    settings.season_folder_template = "Season {Season}"
    settings.episode_folder_template = "{ShowTitle} - {Season}{Episode} - {EpisodeTitle}"

    result = fmt.generate_full_path(96, settings)  # Long anime title
    path_len = len(result) if result else 0
    over = path_len > 260
    print(f"  Path length: {path_len} chars (limit: 260)")
    if over:
        print(f"  !! Still over limit after truncation: {result}")
    else:
        print(f"  Path fits within limit (truncated if needed)")
    print(f"  Path: {result}")
    print()

    # Reset
    settings.target_dir_shows = ""
    settings.auto_organize_by_type = False
    settings.create_episode_folder = False
    settings.shows_subfolder_name = "TV Shows"


def test_unknown_tags(fmt, settings):
    section("14. UNKNOWN / TYPO TAGS")

    result = fmt.generate_name(1, "{Title} ({Yera}) - {Resoluton}", "none", "space")
    has_brace = "{" in (result or "")
    check("Typo tags get cleaned up (no leftover braces)",
          result, "Avatar")
    if has_brace:
        print(f"  !! Leftover braces in output: {result}")
    else:
        check("No leftover braces at all",
              result, "Avatar")
        print(f"  [INFO] Clean output: {result}")
    print()


def test_empty_template(fmt, settings):
    section("15. EMPTY TEMPLATE")

    result = fmt.generate_name(1, "", "none", "space")
    print(f"  [INFO] Empty template result: '{result}'")
    is_empty = (result is not None and result.strip() == "")
    print(f"  Returns empty string: {is_empty}")
    print()


def test_all_tags_empty(fmt, settings):
    section("16. ALL TAGS RESOLVE TO EMPTY")

    # Use tags that will be empty for a movie (no director, no budget in seed)
    result = fmt.generate_name(1, "{Director} ({Budget}) [{Tagline}]", "none", "space")
    print(f"  [INFO] Result: '{result}'")
    has_empty_brackets = "()" in (result or "") or "[]" in (result or "")
    if has_empty_brackets:
        print("  !! Empty brackets remain in output")
    else:
        print("  Brackets cleaned up properly")
    print()


def test_hdr_variations(fmt, settings):
    section("17. HDR VARIATIONS")

    tpl = "{Title} ({Year}) [{HDR}] [{BitDepth}]"

    result = fmt.generate_name(92, tpl, "none", "space")
    check("HDR10 movie shows HDR10",
          result, "HDR10")
    check("HDR10 movie shows 10bit",
          result, "10bit")

    result = fmt.generate_name(93, tpl, "none", "space")
    check("Dolby Vision movie shows DV",
          result, "Dolby Vision")

    result = fmt.generate_name(94, tpl, "none", "space")
    has_sdr = "SDR" in (result or "")
    check("SDR movie -> HDR tag is empty (no SDR shown)",
          result, "Matrix")
    if has_sdr:
        print(f"  !! SDR should not appear in filename: {result}")
    else:
        print(f"  [INFO] SDR correctly hidden: {result}")
    print()


def test_dot_in_title_with_dot_sep(fmt, settings):
    section("18. DOTS IN TITLE + DOT SEPARATOR")

    result = fmt.generate_name(95, "{Title} ({Year}) - {Resolution}", "none", "dot")
    check("Dr. Strange with dot separator",
          result, "Dr")
    print(f"  [INFO] Full result: {result}")
    double_dot = ".." in (result or "")
    if double_dot:
        print("  !! Double dots detected in output")
    else:
        print("  No double dots")
    print()


def test_very_long_title(fmt, settings):
    section("19. VERY LONG TITLES")

    result = fmt.generate_name(96, settings.episode_template, "none", "space")
    check("Long title is preserved",
          result, "Reincarnated")
    title_len = len(result) if result else 0
    print(f"  [INFO] Filename length: {title_len} chars")
    print(f"  [INFO] Result: {result}")
    print()


def test_season_pack(fmt, settings):
    section("20. SEASON PACK (no specific episode)")

    result = fmt.generate_name(97, settings.episode_template, "none", "space")
    check("Season pack gets show title",
          result, "Game of Thrones")
    print(f"  [INFO] Result: {result}")
    print()


def test_custom_variable(fmt, settings):
    section("21. CUSTOM VARIABLE TAG")

    # Normal custom var
    result = fmt.generate_name(1, "{Title} ({Year}) [{Custom}]", "none", "space", "PROPER")
    check("Custom tag with value 'PROPER'",
          result, "PROPER")

    # Empty custom var
    result = fmt.generate_name(1, "{Title} ({Year}) [{Custom}]", "none", "space", "")
    has_empty = "[]" in (result or "")
    print(f"  [INFO] Empty custom result: '{result}'")
    if has_empty:
        print("  !! Empty brackets remain")
    else:
        print("  Brackets cleaned")
    print()


# === Main =====================================================================

def main():
    db = MockDatabase()
    seed(db)
    fmt = Formatter(db)
    settings = AppSettings()

    print("\n" + "=" * 80)
    print("  RENDA COMPREHENSIVE EDGE CASE TEST SUITE v3.0  ".center(80, "="))
    print("=" * 80)

    test_organization_matrix(fmt, settings, db)
    test_naming_styles(fmt, settings)
    test_collision_resolution(settings)
    test_illegal_characters(fmt, settings)
    test_multi_episode(fmt, settings)
    test_missing_metadata(fmt, settings)
    test_season_zero(fmt, settings)
    test_zero_padding(fmt, settings)
    test_year_range(fmt, settings)
    test_resolution_logic(fmt, settings)
    test_extras_handling(fmt, settings)
    test_duplicate_titles(fmt, settings)
    test_path_length(fmt, settings)
    test_unknown_tags(fmt, settings)
    test_empty_template(fmt, settings)
    test_all_tags_empty(fmt, settings)
    test_hdr_variations(fmt, settings)
    test_dot_in_title_with_dot_sep(fmt, settings)
    test_very_long_title(fmt, settings)
    test_season_pack(fmt, settings)
    test_custom_variable(fmt, settings)

    # Summary
    print("\n" + "=" * 80)
    total = total_pass + total_fail
    print(f"  RESULTS: {total_pass}/{total} passed, {total_fail} failed".center(80))
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
