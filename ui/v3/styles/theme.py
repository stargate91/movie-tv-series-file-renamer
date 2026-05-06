from .palette import Palette
from .common import CommonStyles
from .navigation import NavigationStyles
from .inspector import InspectorStyles
from .misc import MiscStyles
from .components.buttons import ButtonStyles
from .components.inputs import InputStyles
from .components.tables import TableStyles
from .components.dialogs import DialogStyles
from .components.lists import ListStyles
from .components.progress import ProgressStyles

class Theme(
    Palette, 
    CommonStyles, 
    NavigationStyles, 
    InspectorStyles, 
    MiscStyles, 
    ButtonStyles, 
    InputStyles, 
    TableStyles, 
    DialogStyles, 
    ListStyles, 
    ProgressStyles
):
    """
    Unified Theme engine for Renda V3.
    This class aggregates all modular style definitions into a single namespace
    to maintain backward compatibility across the codebase.
    """
    pass
