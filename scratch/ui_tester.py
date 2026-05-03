"""
RENDA UI Test Suite v1.0
=========================
Tests for the Settings Page user interface:
  1.  Sidebar Navigation (tab switching, tree items)
  2.  General Tab (controls, defaults)
  3.  Naming Styles Tab (combos, checkboxes)
  4.  Folder Organization Tab (toggles, input states)
  5.  Movie Folders Tab (advanced toggle, chip tags)
  6.  TV Show Folders Tab (advanced toggle, episode folder section)
  7.  Save Button functionality
  8.  Dynamic State Management (checkbox -> input enable/disable)
"""

import os
import sys
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PySide6.QtWidgets import QApplication, QCheckBox, QPushButton, QLineEdit, QComboBox, QSpinBox, QTreeWidgetItem
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

from core.config.manager import AppSettings, ConfigManager
from ui.v3.views.settings_page import SettingsPage

# --- Helpers ---
PASS = "[PASS]"
FAIL = "[FAIL]"
total_pass = 0
total_fail = 0

def check(label, condition, detail=""):
    global total_pass, total_fail
    if condition:
        total_pass += 1
        print(f"  {PASS} {label}")
    else:
        total_fail += 1
        print(f"  {FAIL} {label}")
    if detail:
        print(f"       {detail}")

def section(title):
    print("\n" + "-" * 80)
    print(f"  {title}")
    print("-" * 80 + "\n")


# --- Mock Engine ---
class MockDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
    def _get_connection(self):
        return self.conn
    def clear_all(self):
        pass

class MockEngine:
    def __init__(self):
        self.config = MockConfig()
        self.db = MockDB()

class MockConfig:
    def __init__(self):
        self.settings = AppSettings()
    def save(self):
        pass


# --- Test Functions ---

def test_sidebar_navigation(page):
    section("1. SIDEBAR NAVIGATION")

    # Tree should exist
    check("Tree widget exists", page.tabs_tree is not None)
    check("Tree has header hidden", page.tabs_tree.isHeaderHidden())

    # Check top-level items count
    top_count = page.tabs_tree.topLevelItemCount()
    check(f"Top-level items = {top_count}", top_count >= 5,
          f"Expected >= 5 (General, Naming Styles, File Naming, Folders, API Keys, Advanced)")

    # Test clicking on different items switches the stack
    page.tabs_tree.setCurrentItem(page.general_item)
    check("General tab -> stack index 0",
          page.stack.currentIndex() == 0)

    page.tabs_tree.setCurrentItem(page.styles_item)
    check("Naming Styles tab -> stack index 1",
          page.stack.currentIndex() == 1)

    page.tabs_tree.setCurrentItem(page.naming_item)
    check("File Naming tab -> stack index 2",
          page.stack.currentIndex() == 2)

    page.tabs_tree.setCurrentItem(page.folders_org)
    check("Organization sub-tab -> stack index 3",
          page.stack.currentIndex() == 3)

    page.tabs_tree.setCurrentItem(page.folders_movies)
    check("Movie Folders sub-tab -> stack index 4",
          page.stack.currentIndex() == 4)

    page.tabs_tree.setCurrentItem(page.folders_tv)
    check("TV Folders sub-tab -> stack index 5",
          page.stack.currentIndex() == 5)

    page.tabs_tree.setCurrentItem(page.api_item)
    check("API Keys tab -> stack index 6",
          page.stack.currentIndex() == 6)

    page.tabs_tree.setCurrentItem(page.adv_item)
    check("Advanced tab -> stack index 7",
          page.stack.currentIndex() == 7)

    # Folders root should redirect to first child
    page.tabs_tree.setCurrentItem(page.folders_root)
    QApplication.processEvents()
    check("Clicking Folders root -> redirects to Organization",
          page.stack.currentIndex() == 3)


def test_general_tab(page):
    section("2. GENERAL TAB")

    # Path input exists and is readonly
    check("Path input exists", page.path_input is not None)
    check("Path input is read-only", page.path_input.isReadOnly())

    # Size spinner
    check("Min video size spinner exists", page.size_spin is not None)
    check("Size spinner range 0-10000",
          page.size_spin.minimum() == 0 and page.size_spin.maximum() == 10000)
    check("Size spinner default = 500",
          page.size_spin.value() == 500)

    # Language combos
    check("Language combo exists", page.lang_combo is not None)
    check("Language combo has items", page.lang_combo.count() >= 4)

    check("Fallback combo exists", page.fallback_combo is not None)
    check("Fallback combo has 'None' option",
          page.fallback_combo.itemData(0) == "")

    # Save button
    check("Save button exists", page.save_btn is not None)
    check("Save button text is 'Save All Changes'",
          page.save_btn.text() == "Save All Changes")


def test_naming_styles(page):
    section("3. NAMING STYLES TAB")

    page.tabs_tree.setCurrentItem(page.styles_item)
    QApplication.processEvents()

    # Check combo boxes exist
    check("Case combo exists", hasattr(page, 'casing_combo') and page.casing_combo is not None)
    check("Separator combo exists", hasattr(page, 'sep_combo') and page.sep_combo is not None)

    if hasattr(page, 'casing_combo'):
        check("Case combo has options", page.casing_combo.count() >= 3)

    if hasattr(page, 'sep_combo'):
        check("Separator combo has options", page.sep_combo.count() >= 3)


def test_folder_organization(page):
    section("4. FOLDER ORGANIZATION TAB")

    page.tabs_tree.setCurrentItem(page.folders_org)
    QApplication.processEvents()

    # Move files checkbox
    check("Move files checkbox exists", hasattr(page, 'move_files_cb'))

    if hasattr(page, 'move_files_cb'):
        # Initially unchecked (default setting)
        check("Move files initially unchecked",
              not page.move_files_cb.isChecked())

    # Auto-organize checkbox
    check("Auto-organize checkbox exists", hasattr(page, 'auto_org_cb'))

    # Subfolder name inputs
    check("Movies subfolder input exists", hasattr(page, 'movie_sub_name'))
    check("Shows subfolder input exists", hasattr(page, 'show_sub_name'))

    if hasattr(page, 'movie_sub_name'):
        check("Movies subfolder default = 'Movies'",
              page.movie_sub_name['edit'].text() == "Movies")

    if hasattr(page, 'show_sub_name'):
        check("Shows subfolder default = 'TV Shows'",
              page.show_sub_name['edit'].text() == "TV Shows")


def test_movie_folders(page):
    section("5. MOVIE FOLDERS TAB")

    page.tabs_tree.setCurrentItem(page.folders_movies)
    QApplication.processEvents()

    # Movie folder checkbox
    check("Movie folder checkbox exists", page.movie_folder_cb is not None)
    check("Movie folder initially checked",
          page.movie_folder_cb.isChecked())

    # Template input
    check("Movie folder template input exists",
          page.movie_folder_tpl['edit'] is not None)
    check("Template matches setting",
          page.movie_folder_tpl['edit'].text() == "{Title} ({Year})")

    # Advanced toggle container
    check("Advanced movie folder container exists",
          page.adv_movie_folder_container is not None)
    check("Advanced container initially hidden",
          not page.adv_movie_folder_container.isVisible())

    # Test checkbox -> input enable/disable
    page.movie_folder_cb.setChecked(False)
    QApplication.processEvents()
    check("Unchecking movie folder -> disables template input",
          not page.movie_folder_tpl['edit'].isEnabled())

    page.movie_folder_cb.setChecked(True)
    QApplication.processEvents()
    check("Re-checking movie folder -> enables template input",
          page.movie_folder_tpl['edit'].isEnabled())


def test_tv_folders(page):
    section("6. TV SHOW FOLDERS TAB")

    page.tabs_tree.setCurrentItem(page.folders_tv)
    QApplication.processEvents()

    # Show folder checkbox
    check("Show folder checkbox exists", page.show_folder_cb is not None)
    check("Show folder initially checked",
          page.show_folder_cb.isChecked())

    # Season folder checkbox
    check("Season folder checkbox exists", page.season_folder_cb is not None)
    check("Season folder initially checked",
          page.season_folder_cb.isChecked())

    # Episode folder checkbox
    check("Episode folder checkbox exists", page.episode_folder_cb is not None)
    check("Episode folder initially unchecked",
          not page.episode_folder_cb.isChecked())

    # Advanced containers
    check("Advanced show folder container exists",
          page.adv_show_folder_container is not None)
    check("Advanced show container initially hidden",
          not page.adv_show_folder_container.isVisible())

    check("Advanced season container exists",
          page.adv_season_container is not None)
    check("Season advanced initially hidden",
          not page.adv_season_container.isVisible())

    check("Advanced episode folder container exists",
          page.adv_episode_folder_container is not None)
    check("Episode advanced initially hidden",
          not page.adv_episode_folder_container.isVisible())

    # Episode folder template disabled by default (checkbox unchecked)
    check("Episode folder template initially disabled",
          not page.episode_folder_tpl['edit'].isEnabled())

    # Toggle episode folder ON
    page.episode_folder_cb.setChecked(True)
    QApplication.processEvents()
    check("Checking episode folder -> enables template input",
          page.episode_folder_tpl['edit'].isEnabled())

    # Toggle back OFF
    page.episode_folder_cb.setChecked(False)
    QApplication.processEvents()
    check("Unchecking episode folder -> disables template input",
          not page.episode_folder_tpl['edit'].isEnabled())

    # Season folder enable/disable
    page.season_folder_cb.setChecked(False)
    QApplication.processEvents()
    check("Unchecking season folder -> disables season template",
          not page.season_folder_tpl['edit'].isEnabled())

    page.season_folder_cb.setChecked(True)
    QApplication.processEvents()
    check("Re-checking season folder -> enables season template",
          page.season_folder_tpl['edit'].isEnabled())


def test_dynamic_states(page):
    section("7. DYNAMIC STATE MANAGEMENT")

    page.tabs_tree.setCurrentItem(page.folders_movies)
    QApplication.processEvents()

    # Test: Typing in template input
    edit = page.movie_folder_tpl['edit']
    original_text = edit.text()
    
    edit.clear()
    QTest.keyClicks(edit, "{Title} - {Year}")
    QApplication.processEvents()
    
    check("Can type in template input",
          edit.text() == "{Title} - {Year}")

    # Restore
    edit.clear()
    QTest.keyClicks(edit, original_text)

    # Test: Disable and try to type
    page.movie_folder_cb.setChecked(False)
    QApplication.processEvents()
    
    check("Disabled input rejects focus",
          not edit.isEnabled())

    page.movie_folder_cb.setChecked(True)
    QApplication.processEvents()


def test_advanced_tab(page):
    section("8. ADVANCED TAB")

    page.tabs_tree.setCurrentItem(page.adv_item)
    QApplication.processEvents()

    # Cleanup checkbox
    check("Cleanup empty folders checkbox exists",
          page.cleanup_cb is not None)
    check("Cleanup initially checked",
          page.cleanup_cb.isChecked())

    # Wipe button
    check("Wipe button exists", page.wipe_btn is not None)
    check("Wipe button text correct",
          "Wipe" in page.wipe_btn.text())


def test_stack_widget_count(page):
    section("9. STACK WIDGET INTEGRITY")

    count = page.stack.count()
    check(f"Stack has 8 pages (got {count})", count == 8)

    # Verify each page is a QWidget
    for i in range(count):
        w = page.stack.widget(i)
        check(f"Page {i} is valid widget", w is not None)


# --- Main ---
def main():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    engine = MockEngine()
    page = SettingsPage(engine)
    page.show()
    QApplication.processEvents()

    print("\n" + "=" * 80)
    print("  RENDA UI TEST SUITE v1.0  ".center(80, "="))
    print("=" * 80)

    test_sidebar_navigation(page)
    test_general_tab(page)
    test_naming_styles(page)
    test_folder_organization(page)
    test_movie_folders(page)
    test_tv_folders(page)
    test_dynamic_states(page)
    test_advanced_tab(page)
    test_stack_widget_count(page)

    # Summary
    print("\n" + "=" * 80)
    total = total_pass + total_fail
    print(f"  RESULTS: {total_pass}/{total} passed, {total_fail} failed".center(80))
    print("=" * 80 + "\n")

    page.close()
    return total_fail


if __name__ == "__main__":
    failures = main()
    sys.exit(failures)
