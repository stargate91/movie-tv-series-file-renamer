"""
v3.1 Formatter: Orchestrates filename generation and path construction.
"""

import os
import re
import logging
from core.engine.tag_builder import TagBuilder
from core.engine.template_engine import TemplateEngine

logger = logging.getLogger(__name__)

class Formatter:
    """
    Orchestrator for file naming and organization.
    Uses TagBuilder to gather metadata and TemplateEngine to process string formats.
    """

    def __init__(self, db):
        self.db = db
        self.tags = TagBuilder(db)
        self.engine = TemplateEngine()

    def generate_name(self, file_id, settings, prefetched_data=None, _depth=0):
        """Generates the final formatted file name for a given file_id."""
        if _depth > 10: return None # Recursion Guard
        
        file_data = None
        if prefetched_data and file_id in prefetched_data:
            file_data = prefetched_data[file_id]
        else:
            row = self.db.files.get_file_by_id(file_id)
            if not row: return None
            file_data = dict(row)
            
        target_file_id = file_data.get('parent_file_id') or file_id
        
        # Optimization: Use prefetched links/media if available in the data object
        # Our get_files_with_metadata query adds media_item_type, media_title etc.
        links = None
        m_item = None
        
        if prefetched_data and file_id in prefetched_data and file_data.get('media_item_type'):
             # We have enough to mock the media item for preview
             m_item = {
                 'media_type': file_data.get('media_item_type'),
                 'title': file_data.get('media_title')
             }
             # We still need links for the TagBuilder context (S/E/etc)
             links = self.db.media.get_links_for_file(target_file_id)
        else:
             links = self.db.media.get_links_for_file(target_file_id)
             
        category = file_data.get('category')
        if not links:
            # Fallback for unidentified or orphaned files
            orig_name = os.path.splitext(file_data.get('file_name', ''))[0]
            if category == 'video':
                return orig_name
            
            # If it has a parent, use the parent's name as a prefix even if unidentified
            parent_id = file_data.get('parent_file_id')
            if parent_id:
                parent_name = self.generate_name(parent_id, settings, prefetched_data, _depth + 1)
                return f"{parent_name} - {orig_name}"
            else:
                return f"[ORPHAN] {category.capitalize()} - {orig_name}"

        if not m_item:
            m_item = self.db.media.get_media_item_by_id(links[0]['media_item_id'])
            
        if not m_item:
            # Fallback if media item is missing but link exists
            return os.path.splitext(file_data.get('file_name', ''))[0]
            
        media_type = m_item['media_type']

        # Determine template
        if category != 'video':
            templates = {
                'extra': settings.template_extra_video,
                'subtitle': settings.template_extra_subtitle,
                'audio': settings.template_extra_audio,
                'image': settings.template_extra_image,
                'metadata': settings.template_extra_metadata
            }
            template = templates.get(category, "{ParentName} - {ExtraCategory}")
        else:
            template = settings.movie_template if media_type == 'movie' else settings.episode_template

        # Build context
        lang = file_data.get('target_language') or settings.metadata_language
        context = self.tags.build_context(file_data, links, settings.custom_variable, lang)
        
        if file_data.get('parent_file_id'):
            parent_name = self.generate_name(file_data['parent_file_id'], settings, prefetched_data, _depth + 1)
            context['ParentName'] = parent_name if parent_name else ""
        else:
            context['ParentName'] = ""
            
        return self.engine.process(template, context, settings)

    def generate_full_path(self, file_id, settings, _depth=0):
        """Generates absolute target path (Folder + File Name)."""
        if _depth > 10: return None # Recursion Guard
        
        row = self.db.files.get_file_by_id(file_id)
        if not row: return None
        file_data = dict(row)
            
        is_extra = file_data.get('category') != 'video'
        target_file_id = file_data.get('parent_file_id') or file_id
        links = self.db.media.get_links_for_file(target_file_id)
        media_item = None
        if links:
            media_item = self.db.media.get_media_item_by_id(links[0]['media_item_id'])

        if not media_item and links:
            media_item = self.db.media.get_media_item_by_id(links[0]['media_item_id'])
            
        media_type = media_item['media_type'] if media_item else 'unknown'
        
        file_name = self.generate_name(file_id, settings, _depth=_depth)
        if not file_name:
            file_name = os.path.splitext(file_data.get('file_name', ''))[0]
            
        ext = file_data.get('extension', '')
        
        # Build Directory
        if is_extra and file_data.get('parent_file_id') and media_item:
            parent_full_path = self.generate_full_path(file_data['parent_file_id'], settings, _depth=_depth+1)
            if not parent_full_path: return None
            base_dir = os.path.dirname(parent_full_path)
            folders = []
            lang = file_data.get('target_language') or settings.metadata_language
            context = self.tags.build_context(file_data, links, settings.custom_variable, lang)
            if settings.extras_folder_mode == "single":
                folders.append(settings.extras_folder_name)
            elif settings.extras_folder_mode == "categorized":
                folders.append(context.get("ExtraCategory", "Extras"))
        else:
            if settings.move_files and settings.base_target_path:
                base_dir = settings.base_target_path
                if settings.enable_folders and settings.auto_organize_by_type:
                    sub = settings.movies_subfolder_name if media_type == 'movie' else settings.shows_subfolder_name
                    if sub: base_dir = os.path.join(base_dir, sub)
            else:
                base_dir = os.path.dirname(file_data['current_path'])
                
            lang = file_data.get('target_language') or settings.metadata_language
            context = self.tags.build_context(file_data, links, settings.custom_variable, lang)
            folders = []
            
            if settings.enable_folders:
                if media_type == 'movie':
                    if settings.create_collection_folder and context.get('Collection'):
                        tpl_coll = self._apply_template(settings.collection_folder_template, context)
                        folders.extend([f.strip() for f in re.split(r'[\\/]', tpl_coll) if f.strip()])
                    
                    if settings.create_movie_folder:
                        tpl_res = self._apply_template(settings.movie_folder_template, context)
                        folders.extend([f.strip() for f in re.split(r'[\\/]', tpl_res) if f.strip()])
                elif media_type == 'tv':
                    if settings.create_show_folder:
                        tpl_res = self._apply_template(settings.show_folder_template, context)
                        folders.extend([f.strip() for f in re.split(r'[\\/]', tpl_res) if f.strip()])
                    if settings.create_season_folder:
                        tpl_res = self._apply_template(settings.season_folder_template, context)
                        folders.extend([f.strip() for f in re.split(r'[\\/]', tpl_res) if f.strip()])
                    if settings.create_episode_folder:
                        tpl_res = self._apply_template(settings.episode_folder_template, context)
                        folders.extend([f.strip() for f in re.split(r'[\\/]', tpl_res) if f.strip()])
        
        folders = [self.engine.sanitize_filename(f) for f in folders]
        target_dir = os.path.join(base_dir, *folders) if folders else base_dir
        full_path = os.path.join(target_dir, f"{file_name}{ext}")
        
        # Windows MAX_PATH safety (260)
        return self._ensure_safe_path_length(full_path, target_dir, file_name, ext, folders, base_dir)

    def _apply_template(self, template, context):
        """Simple replacement for folder names."""
        for tag, val in context.items():
            template = template.replace(f"{{{tag}}}", str(val) if val is not None else "")
        return self.engine.cleanup_empty_tags(template)

    def _ensure_safe_path_length(self, full_path, target_dir, file_name, ext, folders, base_dir):
        # Only relevant for Windows
        if os.name != 'nt': return full_path
        
        MAX_PATH = 250 # Safe buffer
        
        # If it's already an absolute path, we can use the extended-length prefix
        # but many Windows apps still struggle with it, so truncation is a safer fallback.
        if len(full_path) <= MAX_PATH: return full_path
        
        # Try truncating filename first, but keep at least 30 chars
        overhead = len(target_dir) + len(ext) + 2
        max_name_len = MAX_PATH - overhead
        
        if max_name_len >= 30:
            file_name = file_name[:max_name_len].rstrip('. ')
            return os.path.join(target_dir, f"{file_name}{ext}")
            
        # If filename truncation isn't enough, we must truncate folder names too
        current_base = base_dir
        new_folders = []
        for f in folders:
            # Limit each folder to 50 chars if we are in trouble
            new_f = f[:50].rstrip('. ') if len(f) > 50 else f
            new_folders.append(new_f)
            
        new_target_dir = os.path.join(base_dir, *new_folders)
        new_overhead = len(new_target_dir) + len(ext) + 2
        new_max_name = MAX_PATH - new_overhead
        
        if new_max_name < 20: new_max_name = 20 # Absolute minimum
        file_name = file_name[:new_max_name].rstrip('. ')
        
        return os.path.join(new_target_dir, f"{file_name}{ext}")
