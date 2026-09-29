"""
Auth module models (re-exports from app.models).

User, Role, Permission models are defined in app.models to ensure
consistency across the application and avoid circular imports.
"""

# These models are imported from app.models, not defined here
# This is the proper way to structure modular auth without circular imports

__all__ = []  # Models are imported from app.models directly
