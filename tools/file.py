from mutagen.flac import FLAC
from mutagen.id3 import ID3, USLT, SYLT, Encoding
from mutagen.oggopus import OggOpus
from os import path


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
            _lines = ""
            for _i in self.lrc:
                # print(_i)
                _lines += _i+"\n"
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
    def write_mp3_lyrics_mutagen(file_path, lyrics_text, is_synced=False):
        """向MP3文件写入歌词"""
        audio = ID3(file_path)
        if is_synced:
            # 创建同步歌词帧(SYLT)
            # 需要将歌词文本和时间标签解析为SYLT格式
            # 这里简化处理，实际使用时需要解析时间标签
            sylt_frame = SYLT(
                encoding=Encoding.UTF8,
                lang='eng',
                format=2,  # 毫秒
                type=1,  # 歌词
                text=[(0, "歌词示例")]
            )
            audio.add(sylt_frame)
        else:
            # 创建非同步歌词帧(USLT)
            uslt_frame = USLT(
                encoding=Encoding.UTF8,
                lang='eng',
                desc='Lyrics',
                text=lyrics_text
            )
            audio.add(uslt_frame)

        audio.save()

    @staticmethod
    def write_opus_lyrics(file_path, lyrics_text):
        """向Opus文件写入歌词"""
        audio = OggOpus(file_path)
        audio["lyrics"] = lyrics_text
        audio.save()
