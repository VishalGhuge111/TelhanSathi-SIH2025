"""
Static translation utilities - English only (no active translation)
Translation dictionaries kept for reference but not used in UI
"""

# Empty translation dictionary - English only
TRANSLATIONS = {}


def get_translation(text, language='en'):
    """
    Get translation for text - returns English unchanged
    
    Args:
        text (str): Original text (English)
        language (str): Target language (ignored - always returns English)
    
    Returns:
        str: Original text unchanged
    """
    return text


def get_all_translations():
    """Return translation dictionaries (empty - no translations)"""
    return TRANSLATIONS
