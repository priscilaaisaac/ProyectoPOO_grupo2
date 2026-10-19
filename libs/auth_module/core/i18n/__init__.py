"""
Internationalization Package.
"""

from .manager import I18nManager
from .translations import BACKEND_TRANSLATIONS, FRONTEND_TRANSLATIONS

__all__ = ['BACKEND_TRANSLATIONS', 'FRONTEND_TRANSLATIONS', 'I18nManager']
