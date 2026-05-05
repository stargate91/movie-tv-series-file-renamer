import sys
import os

# Add the project root to sys.path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine.matching_engine import MatchingEngine
from core.engine.template_engine import TemplateEngine
from unittest.mock import MagicMock

class MockSettings:
    def __init__(self):
        self.filename_case = "Title"
        self.separator = "space"
        self.metadata_language = "hu-HU"
        self.fallback_language = "en-US"
        self.omdb_key = "test"
        self.tmdb_key = "test"
        self.tmdb_bearer_token = "test"

def run_tests():
    print("Starting Extreme Edge Case Tests...\n")
    
    settings = MockSettings()
    db_mock = MagicMock()
    
    matcher = MatchingEngine(db_mock, settings)
    tpl_engine = TemplateEngine()
    
    # --- 1. MatchingEngine Normalization Tests ---
    print("Testing Normalization...")
    norm_cases = [
        ("Léon: The Professional", "leon the professional"),
        ("Sárkányölő (1981)!!", "sarkanyolo 1981"),
        ("   Space   Check   ", "space check"),
        ("C.I.A. Agent", "cia agent"),
        ("M.A.S.H.", "mash"),
        ("The 5th Element", "the 5th element"),
        ("Németül: Das Boot", "nemetul das boot")
    ]
    
    for input_text, expected in norm_cases:
        actual = matcher._normalize(input_text)
        assert actual == expected, f"Failed Normalization: {input_text} -> Got: '{actual}', Expected: '{expected}'"
    print("PASSED: Normalization")

    # --- 2. MatchingEngine Confidence Tests ---
    print("\nTesting Confidence Logic...")
    res = {'title': 'The Matrix', 'year': 1999}
    
    # Exact Match
    assert matcher.confidence_check(res, "The Matrix", 1999) == True, "Failed Exact Match"
    # Year +- 1
    assert matcher.confidence_check(res, "The Matrix", 1998) == True, "Failed Year-1 Match"
    assert matcher.confidence_check(res, "The Matrix", 2000) == True, "Failed Year+1 Match"
    # Title substring
    assert matcher.confidence_check(res, "Matrix", 1999) == True, "Failed Subtitle Match"
    # Fail: Wrong year
    assert matcher.confidence_check(res, "The Matrix", 1990) == False, "Should have failed on wrong year"
    # Fail: Wrong title
    assert matcher.confidence_check(res, "Batman", 1999) == False, "Should have failed on wrong title"
    print("PASSED: Confidence Logic")

    # --- 3. TemplateEngine Cleanup Tests ---
    print("\nTesting Template Cleanup (No more dangling artifacts)...")
    context = {"Title": "Movie", "Year": "", "Resolution": ""}
    
    # Case: Empty brackets and trailing dashes
    template = "{Title} ({Year}) - [{Resolution}]"
    result = tpl_engine.process(template, context, settings)
    assert result == "Movie", f"Failed Cleanup: Got '{result}'"
    
    # Case: Multiple hyphens
    context = {"Title": "Batman", "Year": "", "Resolution": ""}
    template = "{Title} - {Year} - {Resolution}"
    result = tpl_engine.process(template, context, settings)
    assert result == "Batman", f"Failed Hyphen Collapse: Got '{result}'"
    
    # Case: Title with trailing dash before extension
    context = {"Title": "Inception", "Year": ""}
    template = "{Title} - {Year}"
    result = tpl_engine.process(template, context, settings)
    assert result == "Inception", f"Failed Trailing Dash: Got '{result}'"
    print("PASSED: Template Cleanup")

    # --- 4. TemplateEngine Sanitization Tests ---
    print("\nTesting Filename Sanitization (Windows Safety)...")
    illegal_titles = [
        ("Star Wars: Episode IV", "Star Wars Episode IV"),
        ("What? Where|When*", "What Where When"),
        ("Double  Space", "Double Space"),
        ("Pipe | Test", "Pipe Test")
    ]
    
    for input_title, expected in illegal_titles:
        context = {"Title": input_title}
        result = tpl_engine.process("{Title}", context, settings)
        assert result == expected, f"Failed Sanitization: {input_title} -> Got: '{result}'"
    print("PASSED: Sanitization")

    # --- 5. TemplateEngine Casing & Separators ---
    print("\nTesting Casing & Separators...")
    context = {"Title": "the dark knight", "Year": "2008"}
    
    # Title Case
    settings.filename_case = "Title"
    result = tpl_engine.process("{Title}", context, settings)
    assert result == "The Dark Knight", f"Failed Title Case: Got '{result}'"
    
    # Dot Separator
    settings.separator = "dot"
    result = tpl_engine.process("{Title} {Year}", context, settings)
    assert result == "The.Dark.Knight.2008", f"Failed Dot Separator: Got '{result}'"
    
    # Underscore
    settings.separator = "underscore"
    result = tpl_engine.process("{Title} {Year}", context, settings)
    assert result == "The_Dark_Knight_2008", f"Failed Underscore: Got '{result}'"
    print("PASSED: Casing & Separators")

    print("\n" + "="*40)
    print("ALL EXTREME EDGE CASE TESTS PASSED!")
    print("="*40)

if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}")

        import traceback
        traceback.print_exc()
        sys.exit(1)
