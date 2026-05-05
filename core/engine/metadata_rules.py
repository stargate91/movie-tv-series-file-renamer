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
            'movie': ['edition', 'parts'],
            'tv': ['season', 'episodes', 'parts'],
            'unknown': ['parts']
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

    # Allowed category transitions from an original category
    ALLOWED_TRANSITIONS = {
        'video': ["Video / Movie", "Extra / Bonus"],
        'extra': ["Extra / Bonus", "Video / Movie"],
        'audio': ["Audio"],
        'subtitle': ["Subtitle"],
        'image': ["Image"],
        'metadata': ["NFO / Meta"],
        'unknown': ["Video / Movie", "Extra / Bonus", "Subtitle", "Audio", "Image", "NFO / Meta"]
    }

    # Predefined lists and defaults
    SUB_TYPES = {
        'audio': {
            'items': ["Dub", "Commentary", "Music"],
            'default': "Dub"
        },
        'subtitle': {
            'items': ["Forced", "Full"],
            'default': "Forced"
        },
        'image': {
            'items': ["Poster", "Fanart", "Background", "Banner", "Thumb", "Logo", "Disc"],
            'default': None
        },
        'extra': {
            'items': ["Trailer", "Sample", "Behind the Scenes", "Deleted", "Interview", "Featurette", "Bonus"],
            'default': None
        },
        'default': {
            'items': ["Trailer", "Sample", "Behind the Scenes", "Deleted", "Interview", "Featurette", "Bonus",
                     "Poster", "Fanart", "Background", "Banner", "Thumb", "Logo", "Disc",
                     "Forced", "Full", "Dub", "Commentary", "Music"],
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
        """Returns labels of categories that a file can transition into."""
        return MetadataRules.ALLOWED_TRANSITIONS.get(original_category, MetadataRules.ALLOWED_TRANSITIONS['unknown'])

    @staticmethod
    def get_sub_type_config(category):
        """Returns items and default for sub-types."""
        return MetadataRules.SUB_TYPES.get(category, MetadataRules.SUB_TYPES['default'])

    @staticmethod
    def get_category_label(internal_name):
        """Maps internal category names to UI labels."""
        mapping = {
            "video": "Video / Movie",
            "extra": "Extra / Bonus",
            "subtitle": "Subtitle",
            "audio": "Audio",
            "image": "Image",
            "metadata": "NFO / Meta"
        }
        return mapping.get(internal_name, "Video / Movie")

    @staticmethod
    def get_internal_category(label):
        """Maps UI labels back to internal category names."""
        mapping = {
            "Video / Movie": "video",
            "Extra / Bonus": "extra",
            "Subtitle": "subtitle",
            "Audio": "audio",
            "Image": "image",
            "NFO / Meta": "metadata"
        }
        return mapping.get(label, "unknown")
