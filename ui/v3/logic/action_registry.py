from dataclasses import dataclass, field
from typing import List, Callable, Optional, Union
from core.i18n import T

@dataclass
class ActionDefinition:
    id: str
    label_key: str
    icon: str
    label_key_multi: Optional[str] = None
    style: str = 'neutral'
    
    # Requirements
    requires_video: bool = False
    requires_matched: bool = False
    
    # Library View (Pending / Conflict)
    row_primary: bool = False
    row_overflow: bool = False
    context_single: bool = False
    context_batch: bool = False
    batch_bar: bool = False
    
    # Trash View (Ignored)
    row_primary_trash: bool = False
    row_overflow_trash: bool = False
    context_single_trash: bool = False
    context_batch_trash: bool = False
    batch_bar_trash: bool = False

class ActionRegistry:
    """
    Central repository for all discovery actions.
    Ensures consistency between row buttons, context menus, and batch bars.
    """
    
    ACTIONS = {
        'restore': ActionDefinition(
            id='restore',
            label_key='discovery.actions.restore',
            label_key_multi='discovery.actions.restore_multi',
            icon='undo',
            style='success',
            requires_video=False,
            # Library: all False
            # Trash:
            row_primary_trash=True,
            context_single_trash=True,
            context_batch_trash=True,
            batch_bar_trash=True
        ),
        
        # Temporary definitions for others (we will refine these one by one)
        'fix': ActionDefinition(
            id='fix',
            label_key='discovery.actions.fix',
            label_key_multi='discovery.actions.batch_identify',
            icon='wand',
            style='identify',
            requires_video=True,
            row_primary=True,
            context_single=True,
            context_batch=True,
            batch_bar=True
        ),
        'edit': ActionDefinition(
            id='edit',
            label_key='discovery.actions.edit',
            label_key_multi='discovery.actions.batch_actions',
            icon='pencil',
            style='neutral',
            requires_video=False,
            row_primary=True,
            context_single=True,
            context_batch=True,
            batch_bar=True
        ),
        'ignore': ActionDefinition(
            id='ignore',
            label_key='discovery.actions.ignore',
            label_key_multi='discovery.actions.ignore_multi',
            icon='trash-2',
            style='danger',
            requires_video=False,
            row_overflow=True,
            context_single=True,
            context_batch=True,
            batch_bar=True
        ),
        'open_folder': ActionDefinition(
            id='open_folder',
            label_key='discovery.actions.open_folder',
            icon='folder',
            requires_video=False,
            row_overflow=True,
            context_single=True,
            row_primary_trash=True,
            context_single_trash=True
        ),
        'clear_match': ActionDefinition(
            id='clear_match',
            label_key='discovery.actions.clear_match',
            label_key_multi='discovery.actions.clear_match_multi',
            icon='refresh',
            requires_video=True,
            row_overflow=True,
            context_single=True,
            context_batch=True,
            batch_bar=True
        ),
        'fetch_language': ActionDefinition(
            id='fetch_language',
            label_key='discovery.batch.fetch_language',
            label_key_multi='discovery.actions.fetch_multi',
            icon='globe',
            requires_video=True,
            row_overflow=True,
            context_single=True,
            context_batch=True,
            batch_bar=True
        ),
        'organize': ActionDefinition(
            id='organize',
            label_key='discovery.actions.organize',
            label_key_multi='discovery.actions.organize_multi',
            icon='check-square',
            style='success',
            requires_video=True,
            requires_matched=True,
            row_overflow=True,
            context_single=True,
            context_batch=True,
            batch_bar=True
        )
    }

    @classmethod
    def get_action(cls, action_id: str) -> Optional[ActionDefinition]:
        return cls.ACTIONS.get(action_id)

    @classmethod
    def get_actions_for_surface(cls, surface: str, category: str, is_trash: bool, is_multi: bool, is_matched: bool = True) -> List[ActionDefinition]:
        """
        The new 'Smart' filtering logic.
        Returns actions that match the specific surface, tab, and selection mode.
        """
        results = []
        for action in cls.ACTIONS.values():
            # 1. Category check
            if action.requires_video and category != 'video':
                continue
                
            # 2. Tab & Surface check
            if surface == 'context':
                suffix = "_trash" if is_trash else ""
                field_name = f"context_{'batch' if is_multi else 'single'}{suffix}"
                visible = getattr(action, field_name, False)
            else:
                attr = f"{surface}_trash" if is_trash else surface
                visible = getattr(action, attr, False)
                
            if not visible:
                continue
                
            # 3. Match requirement check
            if action.requires_matched and not is_matched:
                continue

            # 4. Batch Bar specifically only shows if is_multi
            if surface == 'batch_bar' and not is_multi:
                continue

            results.append(action)
        return results
