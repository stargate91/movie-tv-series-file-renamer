"""
v3.1 Formatter: Orchestrates filename generation and path construction.
"""

import os
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

    def generate_name(self, file_id, settings):
        """Generates the final formatted file name for a given file_id."""
        row = self.db.get_file_by_id(file_id)
        if not row: return None
        file_data = dict(row)
            
        target_file_id = file_data.get('parent_file_id') or file_id
        links = self.db.get_links_for_file(target_file_id)
        if not links: return None
            
        m_item = self.db.media.get_media_item_by_id(links[0]['media_item_id'])
        if not m_item: return None
        media_type = m_item['media_type']

        # Determine template
        category = file_data.get('category')
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
        context = self.tags.build_context(file_data, links, settings.custom_variable)
        
        if file_data.get('parent_file_id'):
            parent_name = self.generate_name(file_data['parent_file_id'], settings)
            context['ParentName'] = parent_name if parent_name else ""
        else:
            context['ParentName'] = ""
            
        return self.engine.process(template, context, settings)

    def generate_full_path(self, file_id, settings):
        """Generates absolute target path (Folder + File Name)."""
        row = self.db.get_file_by_id(file_id)
        if not row: return None
        file_data = dict(row)
            
        is_extra = file_data.get('category') != 'video'
        target_file_id = file_data.get('parent_file_id') or file_id
        links = self.db.get_links_for_file(target_file_id)
        if not links: return None

        media_item = self.db.media.get_media_item_by_id(links[0]['media_item_id'])
        if not media_item: return None
        media_type = media_item['media_type']
        
        file_name = self.generate_name(file_id, settings)
        if not file_name: return None
        ext = file_data.get('extension', '')
        
        # Build Directory
        if is_extra and file_data.get('parent_file_id'):
            parent_full_path = self.generate_full_path(file_data['parent_file_id'], settings)
            if not parent_full_path: return None
            base_dir = os.path.dirname(parent_full_path)
            folders = []
            context = self.tags.build_context(file_data, links, settings.custom_variable)
            if settings.extras_folder_mode == "single":
                folders.append(settings.extras_folder_name)
            elif settings.extras_folder_mode == "categorized":
                folders.append(context.get("ExtraCategory", "Extras"))
        else:
            if settings.move_files and settings.base_target_path:
                base_dir = settings.base_target_path
                if settings.auto_organize_by_type:
                    sub = settings.movies_subfolder_name if media_type == 'movie' else settings.shows_subfolder_name
                    if sub: base_dir = os.path.join(base_dir, sub)
            else:
                base_dir = os.path.dirname(file_data['current_path'])
                
            context = self.tags.build_context(file_data, links, settings.custom_variable)
            folders = []
            
            if media_type == 'movie' and settings.create_movie_folder:
                folders.append(self._apply_template(settings.movie_folder_template, context))
            elif media_type == 'tv':
                if settings.create_show_folder:
                    folders.append(self._apply_template(settings.show_folder_template, context))
                if settings.create_season_folder:
                    folders.append(self._apply_template(settings.season_folder_template, context))
                if settings.create_episode_folder:
                    folders.append(self._apply_template(settings.episode_folder_template, context))
        
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
        MAX_PATH = 260
        if len(full_path) <= MAX_PATH: return full_path
        
        overhead = len(target_dir) + len(ext) + 2
        max_name_len = MAX_PATH - overhead
        if max_name_len > 20:
            file_name = file_name[:max_name_len].rstrip('. ')
            full_path = os.path.join(target_dir, f"{file_name}{ext}")
        
        if len(full_path) > MAX_PATH and folders:
            truncated_folders = [f[:60].rstrip('. ') if len(f) > 60 else f for f in folders]
            target_dir = os.path.join(base_dir, *truncated_folders)
            overhead = len(target_dir) + len(ext) + 2
            max_name_len = MAX_PATH - overhead
            if max_name_len > 20:
                file_name = file_name[:max_name_len].rstrip('. ')
            full_path = os.path.join(target_dir, f"{file_name}{ext}")
        return full_path
