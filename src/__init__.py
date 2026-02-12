"""
src/__init__.py

Makes the 'src' directory a Python package.

WHY THIS EXISTS:
----------------
Python needs an __init__.py file to recognize a directory as a package.
Without it, 'from src.config import settings' would fail with ImportError.

This file is intentionally kept empty — it just signals to Python:
"Hey, 'src' is a package, you can import modules from it."
"""
