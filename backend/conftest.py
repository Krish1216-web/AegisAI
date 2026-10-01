"""
Root conftest for AegisAI backend test discovery and path resolution.
"""

import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_root = Path(__file__).resolve().parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))
