"""
Music Module - 专业音乐播放器模块
"""
from .player import MusicPlayer, Song, Playlist, PlayMode

try:
    from .widget import MusicPlayerWidget
except ImportError:
    MusicPlayerWidget = None

try:
    from .lyrics import Lyrics, LyricLine, LyricsParser, LyricsManager, lyrics_manager
except ImportError:
    Lyrics = None
    LyricLine = None
    LyricsParser = None
    LyricsManager = None
    lyrics_manager = None

__all__ = [
    'MusicPlayer', 'Song', 'Playlist', 'PlayMode', 'MusicPlayerWidget',
    'Lyrics', 'LyricLine', 'LyricsParser', 'LyricsManager', 'lyrics_manager'
]
