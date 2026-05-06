"""Finds T() keys used in code but missing from en.json."""
import re, json, os

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALE = os.path.join(PROJECT, "resources", "locales", "en.json")
UI_DIR = os.path.join(PROJECT, "ui", "v3")

# Load locale
with open(LOCALE, "r", encoding="utf-8") as f:
    locale_data = json.load(f)

def key_exists(data, dotted_key):
    keys = dotted_key.split(".")
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return False
    return val is not None

# Find all T("...") calls
pattern = re.compile(r'T\(\s*["\']([a-zA-Z0-9_.]+)["\']')
used_keys = set()

for root, dirs, files in os.walk(UI_DIR):
    for fname in files:
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        for match in pattern.finditer(content):
            key = match.group(1)
            # Skip dynamic keys like f"common.types.{m_type}"
            if "{" in key:
                continue
            used_keys.add(key)

# Also check core files
CORE_DIR = os.path.join(PROJECT, "core")
for root, dirs, files in os.walk(CORE_DIR):
    for fname in files:
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        for match in pattern.finditer(content):
            key = match.group(1)
            if "{" not in key:
                used_keys.add(key)

missing = []
for key in sorted(used_keys):
    if not key_exists(locale_data, key):
        missing.append(key)

print(f"\n=== MISSING KEYS ({len(missing)}) ===")
for k in missing:
    print(f"  MISSING: {k}")

print(f"\n=== TOTAL KEYS USED: {len(used_keys)} ===")
print(f"=== KEYS FOUND: {len(used_keys) - len(missing)} ===")
