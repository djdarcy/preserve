"""
Help subsystem for preserve.py.

This package provides help text, examples, and recipes for the preserve CLI tool.
"""

from .examples import (
    get_operation_examples,
    get_all_examples,
    get_help_topic
)

__all__ = [
    'get_operation_examples',
    'get_all_examples',
    'get_help_topic'
]
