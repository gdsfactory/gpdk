"""Pytest configuration for the models package.

``active.py`` is a circulax model module, not a test module; exclude it from
pytest collection.
"""

collect_ignore = ["active.py"]
