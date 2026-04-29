"""pytest configuration — ensure project root on sys.path."""
import sys
from pathlib import Path

# Project root (parent of tests/)
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Also make sure the editable install is reachable
import site
user_packages = site.getusersitepackages()
if user_packages not in sys.path:
    sys.path.insert(0, user_packages)