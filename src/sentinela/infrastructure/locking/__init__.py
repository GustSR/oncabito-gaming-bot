"""
Módulo de locking para prevenção de race conditions.
"""

from .distributed_lock import (
    InMemoryLockManager,
    get_lock_manager,
    distributed_lock
)

__all__ = [
    "InMemoryLockManager",
    "get_lock_manager",
    "distributed_lock"
]
