"""
Streaming package for multi-screen display system.
Contains multi-stream and split-screen streaming functionality.
"""

from .multi_stream import multi_stream_bp
from .split_stream import split_stream_bp

__all__ = ['multi_stream_bp', 'split_stream_bp']
