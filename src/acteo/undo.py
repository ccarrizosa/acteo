"""Undo/redo action stack for Acteo.

This module provides an Action record and UndoStack to track and undo
file operations and classifications. Each action stores source/destination
paths and operation type for reversibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional


class ActionType(str, Enum):
    """Types of actions that can be undone."""

    MOVE = "move"
    COPY = "copy"
    DISCARD = "discard"
    CLASSIFY = "classify"


@dataclass
class Action:
    """A single undoable action.

    Attributes:
        action_type: Type of operation (move, copy, discard, classify).
        src_paths: List of source file paths.
        dst_paths: List of destination file paths (empty for discard/classify).
        sequence_id: Identifier of the affected sequence.
        category: Category assigned (for classify actions).
        timestamp: When the action was performed.
        operator: Name of operator who performed action.
    """

    action_type: ActionType
    src_paths: List[str]
    dst_paths: List[str]
    sequence_id: str
    category: Optional[str] = None
    timestamp: datetime = None  # type: ignore
    operator: Optional[str] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def can_undo(self) -> bool:
        """Check if this action can be undone."""
        undoable = (ActionType.MOVE, ActionType.COPY, ActionType.DISCARD)
        return self.action_type in undoable


class UndoStack:
    """Manages a stack of undoable actions.

    Example:
        stack = UndoStack(max_size=100)
        stack.push(action)
        if stack.can_undo():
            stack.undo()
    """

    def __init__(self, max_size: int = 100) -> None:
        """Initialize the undo stack.

        Args:
            max_size: Maximum number of actions to keep (oldest are discarded).
        """
        self._stack: List[Action] = []
        self._max_size = max_size

    def push(self, action: Action) -> None:
        """Add an action to the stack."""
        self._stack.append(action)
        if len(self._stack) > self._max_size:
            self._stack.pop(0)

    def pop(self) -> Optional[Action]:
        """Remove and return the most recent action, or None if stack is empty."""
        return self._stack.pop() if self._stack else None

    def peek(self) -> Optional[Action]:
        """Return the most recent action without removing it."""
        return self._stack[-1] if self._stack else None

    def clear(self) -> None:
        """Clear all actions from the stack."""
        self._stack.clear()

    def can_undo(self) -> bool:
        """Check if there is an action to undo."""
        return bool(self._stack)

    def size(self) -> int:
        """Return the number of actions in the stack."""
        return len(self._stack)

    def reverse_action(self, action: Action) -> None:
        """Perform the reverse of an action (move dst back to src, etc).

        This method is called by the UI to physically undo file operations.
        """
        if action.action_type == ActionType.MOVE:
            # Reverse: move files from dst back to src
            from .storage import safe_move

            for src, dst in zip(
                action.dst_paths, action.src_paths, strict=True
            ):
                try:
                    safe_move(src, dst)
                except Exception:
                    pass  # log or report error to user

        elif action.action_type == ActionType.COPY:
            # Reverse: delete the copied files
            for dst in action.dst_paths:
                try:
                    Path(dst).unlink()
                except Exception:
                    pass

        elif action.action_type == ActionType.DISCARD:
            # Reverse: move from discard folder back to original location
            from .storage import safe_move

            for src, dst in zip(
                action.dst_paths, action.src_paths, strict=True
            ):
                try:
                    safe_move(src, dst)
                except Exception:
                    pass
