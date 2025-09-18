"""User-defined prompt management for memory synthesis"""

from .manager import PromptManager
from .templates import DefaultPromptTemplates
from .context import ContextDetector

__all__ = ['PromptManager', 'DefaultPromptTemplates', 'ContextDetector']