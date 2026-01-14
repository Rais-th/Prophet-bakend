"""
🔮 Alpha Prophet CLI
AI-powered warehouse optimization assistant
"""

from .tools import TOOLS, execute_tool
from .prophet import AlphaProphetCLI

__version__ = "1.0.0"
__all__ = ["TOOLS", "execute_tool", "AlphaProphetCLI"]
