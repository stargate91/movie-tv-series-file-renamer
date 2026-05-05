import logging

logger = logging.getLogger(__name__)

class ExecutionPlanner:
    """
    Handles the logical planning phase of file operations.
    Determines actions (rename, skip, delete) and resolves path collisions.
    """
    def __init__(self, db, formatter, collision_resolver):
        self.db = db
        self.formatter = formatter
        self.resolver = collision_resolver

    def create_plan(self, file_ids, settings):
        """Creates a proposed execution plan for a list of file IDs."""
        plan = []
        for fid in file_ids:
            file_data = self.db.files.get_file_by_id(fid)
            if not file_data: continue
                
            cat = file_data.get('category')
            is_extra = cat != 'video'
            
            # Determine Action
            action = self._determine_action(file_data, settings)
            media_type = file_data.get('fn_media_type') or file_data.get('fd_media_type') or 'unknown'

            if action == 'skip':
                plan.append(self._create_plan_item(fid, file_data['current_path'], file_data['current_path'], 'skip', 'safe', cat, media_type))
                continue
                
            if action == 'delete':
                plan.append(self._create_plan_item(fid, file_data['current_path'], None, 'delete', 'safe', cat, media_type))
                continue
                
            # Action is rename
            proposed_path = self.formatter.generate_full_path(fid, settings)
            if not proposed_path:
                plan.append(self._create_plan_item(fid, file_data['current_path'], None, 'error', 'missing_data', cat, media_type))
                continue
                
            # If path hasn't changed, skip
            if proposed_path.lower() == file_data['current_path'].lower():
                plan.append(self._create_plan_item(fid, file_data['current_path'], proposed_path, 'skip', 'safe', cat, media_type))
                continue
                
            plan.append(self._create_plan_item(fid, file_data['current_path'], proposed_path, 'rename', 'pending', cat, media_type))
            
        # Resolve collisions
        self._resolve_collisions(plan)
        return plan

    def _determine_action(self, file_data, settings):
        cat = file_data.get('category')
        if cat == 'video': return 'rename'
        
        action_map = {
            'extra': settings.action_extra_video,
            'subtitle': settings.action_extra_subtitle,
            'audio': settings.action_extra_audio,
            'image': settings.action_extra_image,
            'metadata': settings.action_extra_metadata
        }
        return action_map.get(cat, 'rename')

    def _create_plan_item(self, fid, orig, proposed, action, status, cat, mtype):
        return {
            'file_id': fid,
            'original_path': orig,
            'proposed_path': proposed,
            'action': action,
            'status': status,
            'category': cat,
            'media_type': mtype
        }

    def _resolve_collisions(self, plan):
        """Runs the collision detection and auto-resolution logic."""
        rename_items = [p for p in plan if p['action'] == 'rename']
        if not rename_items: return

        safe, collisions = self.resolver.detect_collisions(rename_items)
        for p in safe: p['status'] = 'safe'
            
        for exact_path, group in collisions.items():
            resolved = self.resolver.auto_resolve_group(group)
            if resolved:
                for p in resolved: p['status'] = 'safe'
            else:
                for p in group: p['status'] = 'collision'
