# -*- coding: utf-8 -*-
from mutagen.flac import FLAC
from mutagen.id3 import ID3, USLT, SYLT, Encoding
from mutagen.oggopus import OggOpus
from os import path
from mutagen.mp3 import MP3


def convert_lrc_to_synced_lyrics(lrc_lines):
    synced_lyrics = []
    lrc_lines = lrc_lines.split("\n")
    for line in lrc_lines:
        # 分割时间标签和歌词
        if ']' not in line:
            continue
        time_part, lyric = line.split(']', 1)
        time_str = time_part[1:]  # 去掉开头的'['
        # 处理双语歌词行（中日文在同一时间点）
        if '\n' in lyric:
            lyric_lines = lyric.split('\n')
            for l in lyric_lines:
                if l.strip():  # 跳过空行
                    # 转换时间格式 [分:秒.毫秒] 为毫秒
                    minutes, seconds = time_str.split(':')
                    seconds, milliseconds = seconds.split('.')
                    total_ms = int(minutes) * 60000 + int(seconds) * 1000 + int(milliseconds) * 10

                    synced_lyrics.append((total_ms, l.strip()))
        else:
            if lyric.strip():
                # 转换时间格式
                minutes, seconds = time_str.split(':')
                seconds, milliseconds = seconds.split('.')
                total_ms = int(minutes) * 60000 + int(seconds) * 1000 + int(milliseconds) * 10

                synced_lyrics.append((total_ms, lyric.strip()))
    # 按时间排序
    synced_lyrics.sort(key=lambda x: x[0])
    return synced_lyrics


class MusicLrcEditor:
    def __init__(self, _path):
        self.path = _path
        self.lrc = None
        if path.exists(self.path):
            """自动检测文件类型并读取歌词"""
            ext = path.splitext(self.path)[1].lower()
            if ext in ['.flac', '.mp3', '.opus', ".lrc", ".txt"]:
                self.ext = ext
            else:
                print(f"不支持的文件格式: {ext}:{self.path}")
                self.ext = None
        else:
            print(f"无效路径: {self.path}")
            self.ext = None

    def isreadlrc(self):
        if self.ext is not None:
            return True
        else:
            return False

    def read_lyrics(self) -> list:
        try:
            if self.ext == '.flac':
                self.ext = '.flac'
                self.lrc = self.get_flac_lyrics(self.path)
            elif self.ext == '.mp3':
                self.ext = '.mp3'
                self.lrc = self.get_mp3_lyrics(self.path)
            elif self.ext == '.opus':
                self.ext = '.opus'
                self.lrc = self.get_opus_lyrics(self.path)
            elif self.ext in [".lrc", ".txt"]:
                with open(self.path, 'r', encoding='utf-8') as f:
                    self.lrc = f.readlines()
            if isinstance(self.lrc, str):
                # print()
                self.lrc = self.lrc.replace("\r\n", "\n").split("\n")
            elif isinstance(self.lrc, list):
                _lines = []
                for _i in self.lrc:
                    _lines += [_i.replace("\r", "").replace("\n", "")]
                self.lrc = _lines
            elif self.lrc is None:
                print(f"self.lrc 读取错误(None):{self.path}")
                return []
            else:
                print(f"self.lrc 无效格式[{type(self.lrc)}]:{self.path}")
                return []
            return self.lrc
        except Exception as e:
            print(f"读取{self.ext}歌词失败: :{self.path}\n{e}")
            return []

    def write_lyrics(self, wt_path: str = "") -> bool:
        # print(wt_path)
        if wt_path:
            if not path.exists(wt_path):
                print(f"不存在的路径: {wt_path}")
                return False
            ext = path.splitext(wt_path)[1].lower()
        else:
            wt_path = self.path
            ext = self.ext
        # print(self.lrc)
        if isinstance(self.lrc, list):
            _lines = "\n".join(self.lrc)
        else:
            print(f"self.lrc 无效格式[{type(self.lrc)}]:{self.path}")
            return False
        try:
            if ext == '.flac':
                self.write_flac_lyrics(wt_path, _lines)
            elif ext == '.mp3':
                self.write_mp3_lyrics_mutagen(wt_path, _lines)
            elif ext == '.opus':
                self.write_opus_lyrics(wt_path, _lines)
            elif ext in [".lrc", ".txt"]:
                with open(wt_path, 'w+', encoding='utf-8') as f:
                    f.write(_lines)

        except Exception as e:
            print(f"写入歌词失败: {wt_path}\n{e}")
            return False
        else:
            return True

    @staticmethod
    def get_flac_lyrics(file_path):
        """读取FLAC文件的歌词"""
        audio = FLAC(file_path)

        # 检查是否有歌词
        if 'lyrics' in audio.tags:
            return audio['lyrics'][0]
        elif 'LYRICS' in audio.tags:
            return audio['LYRICS'][0]
        else:
            # 尝试查找其他可能的歌词标签
            for key in audio.tags:
                if 'lyric' in key.lower():
                    return audio[key][0]
            return None

    @staticmethod
    def get_mp3_lyrics(file_path):
        """读取MP3文件的歌词"""
        try:
            audio = ID3(file_path)
            # 查找USLT帧（非同步
            for frame in audio.values():
                if isinstance(frame, USLT):
                    return frame.text
            # 查找SYLT帧（同步歌词）
            for frame in audio.values():
                if isinstance(frame, SYLT):
                    if isinstance(frame.text[0][0], str):
                        return "\n".join([text for (text, _) in frame.text])
                    else:
                        return "\n".join([text for (_, text) in frame.text])
            return None
        except Exception as e:
            print(f"读取MP3歌词时出错:{file_path}\n{e}")
            return None

    @staticmethod
    def get_opus_lyrics(file_path):
        audio = OggOpus(file_path)

        # 检查常见歌词标签
        lyrics_tags = ['lyrics', 'LYRICS', 'UNSYNCEDLYRICS', 'SYNCEDLYRICS']

        for tag in lyrics_tags:
            if tag in audio.tags:
                return audio.tags[tag][0]

        # 检查其他可能包含歌词的标签
        for tag in audio.tags:
            if 'lyric' in tag.lower():
                return audio.tags[tag][0]

        return None

    @staticmethod
    def write_flac_lyrics(file_path, lyrics_text):
        """向FLAC文件写入歌词"""
        audio = FLAC(file_path)
        audio["lyrics"] = lyrics_text
        audio.save()

    @staticmethod
    def write_mp3_lyrics_mutagen(file_path, lyrics_text):
        audio = MP3(file_path, ID3=ID3)
        lyrics1 = convert_lrc_to_synced_lyrics(lyrics_text)
        lyrics = []
        for timestamp, text in lyrics1:
            lyrics.append((text, int(timestamp)))
        # print(lyrics)
        sylt = SYLT(
            encoding=Encoding.UTF8,
            lang='eng',
            format=2,  # 毫秒
            type=1,  # 歌词
            desc='Synced Lyrics',
            text=lyrics
        )
        uslt = USLT(
            encoding=Encoding.UTF8,
            lang='eng',
            desc="Lyrics",
            text=lyrics_text
        )
        audio.tags.delall('SYLT')
        audio.tags.delall('USLT')
        # 添加同步歌词帧到ID3标签
        audio.tags.add(sylt)
        audio.tags.add(uslt)
        # 保存修改
        audio.save(file_path)

    @staticmethod
    def write_opus_lyrics(file_path, lyrics_text):
        """向Opus文件写入歌词"""
        audio = OggOpus(file_path)
        audio["lyrics"] = lyrics_text
        audio.save()


if __name__ == "__main__":
    ...
