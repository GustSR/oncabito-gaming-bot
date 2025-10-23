#!/usr/bin/env python3
"""
Health check script to verify database connectivity and basic data retrieval.
"""
import asyncio
import sys
from pathlib import Path

# Add root dir to path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "src"))

from sentinela.infrastructure.config.container import get_container, shutdown_container

async def perform_check():
    """
    Connects to the database via the new architecture and counts active users.
    """
    container = None
    try:
        container = await get_container()
        user_repo = container.get("user_repository")
        active_users = await user_repo.find_active_users()
        print(len(active_users))
        return 0
    except Exception as e:
        print(f"Health check failed: {e}", file=sys.stderr)
        return 1
    finally:
        if container:
            await shutdown_container()

if __name__ == "__main__":
    # Ensures that the script returns a proper exit code
    # asyncio.run() returns the value from the coroutine
    result_code = asyncio.run(perform_check())
    sys.exit(result_code)
