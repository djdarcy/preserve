"""
Operation handlers for preserve commands.

This module contains the implementation of various preserve operations,
organized to keep the main preserve.py file manageable.
"""

from .verify import handle_verify_operation

__all__ = ['handle_verify_operation']