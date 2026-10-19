"""
Flask decorators for authentication.
"""

from functools import wraps

from flask import redirect, request, session, url_for


def login_required(f):
    """
    Decorator to protect routes that require a logged-in user.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            # Redirect to the login page, saving the original URL
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function
