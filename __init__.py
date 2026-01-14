"""
Alpha Prophet CLI
AI-powered warehouse optimization assistant
"""

from .tools import TOOLS, execute_tool

__version__ = "1.0.0"
__all__ = ["TOOLS", "execute_tool"]

# AlphaProphetCLI requires anthropic package, import separately if needed
# from .prophet import AlphaProphetCLI
