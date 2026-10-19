"""
Flask Extension
===============

This package contains the optional Flask integration for auth-module,
including blueprints, routes, templates, and view controllers.
"""

from .decorators import login_required
from .extension import FlaskExtension

__all__ = ['FlaskExtension', 'login_required']
