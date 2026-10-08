"""
AegisAI Enterprise — Database Migration Status CLI Tool
Provides non-destructive introspection of the active database migration state,
schema versions, and table ownership without exposing passwords or credentials.
"""

import sys
import json
from app.database.migration_manager import get_migration_status


def main():
    try:
        status = get_migration_status()
        print(json.dumps(status, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
