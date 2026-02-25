"""
Lyrics Parser - 歌词解析器
支持LRC格式歌词解析和同步
"""
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class LyricLine:
    """单行歌词"""
    time: float  # 时间（秒）
    text: str    # 歌词文本
    
    def __lt__(self, other):
        return self.time < other.time
    
    def __eq__(self, other):
        if isinstance(other, LyricLine):
            return abs(self.time - other.time) < 0.01
        return False


@dataclass
class Lyrics:
    """歌词数据"""
    lines: List[LyricLine] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    
    def get_line_at_time(self, time: float) -> Tuple[Optional[LyricLine], int]:
        """
        获取指定时间点的歌词行
        
        Args:
            time: 当前播放时间（秒）
            
        Returns:
            (当前歌词行, 行索引)
        """
        if not self.lines:
            return None, -1
        
        for i in range(len(self.lines) - 1, -1, -1):
            if self.lines[i].time <= time:
                return self.lines[i], i
        
        return self.lines[0], 0
    
    def get_next_lines(self, current_index: int, count: int = 5) -> List[LyricLine]:
        """获取接下来的几行歌词"""
        if current_index < 0:
            return self.lines[:count]
        return self.lines[current_index + 1:current_index + 1 + count]
    
    def get_prev_lines(self, current_index: int, count: int = 3) -> List[LyricLine]:
        """获取之前的几行歌词"""
        if current_index <= 0:
            return []
        start = max(0, current_index - count)
        return self.lines[start:current_index]
    
    def get_context_lines(self, current_index: int, before: int = 2, after: int = 3) -> List[Tuple[LyricLine, bool]]:
        """
        获取上下文歌词（用于显示）
        
        Returns:
            List of (LyricLine, is_current)
        """
        result = []
        
        if not self.lines or current_index < 0:
            return result
        
        start = max(0, current_index - before)
        end = min(len(self.lines), current_index + after + 1)
        
        for i in range(start, end):
            result.append((self.lines[i], i == current_index))
        
        return result
    
    def to_lrc(self) -> str:
        """转换为LRC格式"""
        lines = []
        
        for key, value in self.metadata.items():
            lines.append(f"[{key}:{value}]")
        
        for line in self.lines:
            minutes = int(line.time // 60)
            seconds = line.time % 60
            time_str = f"[{minutes:02d}:{seconds:05.2f}]"
            lines.append(f"{time_str}{line.text}")
        
        return "\n".join(lines)


class LyricsParser:
    """歌词解析器"""
    
    METADATA_TAGS = ['ti', 'ar', 'al', 'by', 'offset', 're', 've']
    
    TIME_PATTERN = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\]')
    METADATA_PATTERN = re.compile(r'\[([a-zA-Z]+):(.+)\]')
    
    @classmethod
    def parse(cls, content: str) -> Lyrics:
        """
        解析LRC格式歌词
        
        Args:
            content: LRC歌词内容
            
        Returns:
            Lyrics对象
        """
        lyrics = Lyrics()
        
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            meta_match = cls.METADATA_PATTERN.match(line)
            if meta_match:
                tag = meta_match.group(1).lower()
                value = meta_match.group(2).strip()
                
                if tag in cls.METADATA_TAGS:
                    lyrics.metadata[tag] = value
                    continue
            
            time_match = cls.TIME_PATTERN.findall(line)
            if time_match:
                text = cls.TIME_PATTERN.sub('', line).strip()
                
                for time_tuple in time_match:
                    minutes = int(time_tuple[0])
                    seconds = int(time_tuple[1])
                    milliseconds = int(time_tuple[2])
                    
                    if len(time_tuple[2]) == 2:
                        milliseconds *= 10
                    
                    time_seconds = minutes * 60 + seconds + milliseconds / 1000.0
                    
                    lyrics.lines.append(LyricLine(time=time_seconds, text=text))
        
        lyrics.lines.sort()
        
        offset = float(lyrics.metadata.get('offset', 0)) / 1000.0
        if offset != 0:
            for line in lyrics.lines:
                line.time += offset
        
        logger.debug(f"解析歌词: {len(lyrics.lines)} 行")
        return lyrics
    
    @classmethod
    def parse_file(cls, file_path: str) -> Optional[Lyrics]:
        """
        解析歌词文件
        
        Args:
            file_path: 歌词文件路径
            
        Returns:
            Lyrics对象或None
        """
        path = Path(file_path)
        
        if not path.exists():
            logger.debug(f"歌词文件不存在: {file_path}")
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return cls.parse(content)
        except UnicodeDecodeError:
            try:
                with open(path, 'r', encoding='gbk') as f:
                    content = f.read()
                return cls.parse(content)
            except Exception as e:
                logger.error(f"解析歌词文件失败: {e}")
                return None
        except Exception as e:
            logger.error(f"解析歌词文件失败: {e}")
            return None
    
    @classmethod
    def find_lyrics_file(cls, audio_path: str) -> Optional[str]:
        """
        查找音频文件对应的歌词文件
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            歌词文件路径或None
        """
        audio_path = Path(audio_path)
        audio_dir = audio_path.parent
        audio_stem = audio_path.stem
        
        lyrics_extensions = ['.lrc', '.LRC', '.lrcx', '.LRCX']
        
        for ext in lyrics_extensions:
            lyrics_path = audio_dir / f"{audio_stem}{ext}"
            if lyrics_path.exists():
                return str(lyrics_path)
        
        lyrics_dir = audio_dir / "lyrics"
        if lyrics_dir.exists():
            for ext in lyrics_extensions:
                lyrics_path = lyrics_dir / f"{audio_stem}{ext}"
                if lyrics_path.exists():
                    return str(lyrics_path)
        
        return None
    
    @classmethod
    def create_empty_lyrics(cls, title: str = "未知歌曲") -> Lyrics:
        """创建空歌词"""
        return Lyrics(
            lines=[LyricLine(time=0, text="♪ 暂无歌词 ♪")],
            metadata={'ti': title}
        )


class LyricsManager:
    """歌词管理器"""
    
    def __init__(self):
        self._cache: Dict[str, Lyrics] = {}
    
    def get_lyrics(self, audio_path: str) -> Lyrics:
        """
        获取歌词
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            Lyrics对象
        """
        if audio_path in self._cache:
            return self._cache[audio_path]
        
        lyrics_file = LyricsParser.find_lyrics_file(audio_path)
        
        if lyrics_file:
            lyrics = LyricsParser.parse_file(lyrics_file)
            if lyrics:
                self._cache[audio_path] = lyrics
                return lyrics
        
        title = Path(audio_path).stem
        empty_lyrics = LyricsParser.create_empty_lyrics(title)
        self._cache[audio_path] = empty_lyrics
        return empty_lyrics
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()


lyrics_manager = LyricsManager()
