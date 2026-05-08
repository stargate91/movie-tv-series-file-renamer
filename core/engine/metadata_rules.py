import logging

logger = logging.getLogger(__name__)

class MetadataRules:
    """
    Centralized logic for metadata field relevance and category transitions.
    Decouples UI display logic from core media classification rules.
    """
    
    # Define which sections are relevant for each category/media_type combination
    FIELD_VISIBILITY = {
        'video': {
            'movie': ['edition', 'parts', 'target_lang'],
            'tv': ['season', 'episodes', 'parts', 'target_lang'],
            'unknown': ['parts', 'target_lang']
        },
        'audio': {
            'any': ['sub_type', 'language', 'linking']
        },
        'subtitle': {
            'any': ['sub_type', 'language', 'linking']
        },
        'image': {
            'any': ['sub_type', 'linking']
        },
        'metadata': {
            'any': ['linking']
        },
        'extra': {
            'any': ['sub_type', 'linking']
        }
    }

    # Allowed category transitions from an original category (using internal keys)
    ALLOWED_TRANSITIONS = {
        'video': ["video", "extra"],
        'extra': ["extra", "video"],
        'audio': ["audio"],
        'subtitle': ["subtitle"],
        'image': ["image"],
        'metadata': ["metadata"],
        'unknown': ["video", "extra", "subtitle", "audio", "image", "metadata"]
    }

    # Predefined lists and defaults
    SUB_TYPES = {
        'audio': {
            'items': ["dub", "commentary", "music"],
            'default': "dub"
        },
        'subtitle': {
            'items': ["forced", "full"],
            'default': "forced"
        },
        'image': {
            'items': ["poster", "fanart", "background", "banner", "thumb", "logo", "disc"],
            'default': None
        },
        'extra': {
            'items': ["trailer", "sample", "behind the scenes", "deleted", "interview", "featurette", "bonus"],
            'default': None
        },
        'default': {
            'items': ["trailer", "sample", "behind the scenes", "deleted", "interview", "featurette", "bonus",
                     "poster", "fanart", "background", "banner", "thumb", "logo", "disc",
                     "forced", "full", "dub", "commentary", "music"],
            'default': None
        }
    }

    @staticmethod
    def get_visible_fields(category, media_type=None):
        """Returns a list of visible field identifiers."""
        cat_rules = MetadataRules.FIELD_VISIBILITY.get(category, {})
        if not cat_rules:
            return []
        
        if 'any' in cat_rules:
            return cat_rules['any']
            
        return cat_rules.get(media_type, cat_rules.get('unknown', []))

    @staticmethod
    def get_allowed_categories(original_category):
        """Returns internal keys of categories that a file can transition into."""
        return MetadataRules.ALLOWED_TRANSITIONS.get(original_category, MetadataRules.ALLOWED_TRANSITIONS['unknown'])

    @staticmethod
    def get_sub_type_config(category):
        """Returns items and default for sub-types."""
        return MetadataRules.SUB_TYPES.get(category, MetadataRules.SUB_TYPES['default'])

