import os
import pykakasi
import re
from mutagen.flac import FLAC
from mutagen.id3 import ID3, USLT, SYLT, Encoding
from mutagen.oggopus import OggOpus
from os import path, listdir
import sys
import tkinter as tk
from tkinter import filedialog
import json


# 保存配置文件路径
config_file = 'config.json'
seq = "chin-hira-kanji"
selected_folder = ''  # 全局变量存储选择的文件夹路径


# 读取上次保存的文件夹路径
def load_last_folder():
    if path.exists(config_file):
        with open(config_file, 'r') as file:
            config = json.load(file)
            return config.get('last_folder', ''), config.get('seq', '')
    return '', seq


# 保存当前选择的文件夹路径
def save_last_folder(folder_path, _seq):
    config = {'last_folder': folder_path, "seq": _seq}
    with open(config_file, 'w', encoding='utf-8') as file:
        json.dump(config, file)


# GUI窗口居中显示
def center_window(_root, width=300, height=150):
    screen_width = _root.winfo_screenwidth()
    screen_height = _root.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    _root.geometry(f'{width}x{height}+{x}+{y}')


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
                print(f"             不支持的文件格式: {ext}")
                self.ext = None
        else:
            print(f"             无效路径: {self.path}")
            self.ext = None

    def isreadlrc(self):
        if self.ext is not None:
            return True
        else:
            return False

    def read_lyrics(self):
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
            else:
                print(f"             self.lrc 无效格式[{type(self.lrc)}]")
                return False
            return self.lrc
        except Exception as e:
            print(f"             读取{self.ext}歌词失败: {e}")
            return False

    def write_lyrics(self, wt_path: str = ""):
        # print(wt_path)
        if wt_path:
            if not path.exists(wt_path):
                print(f"             不存在的路径: {wt_path}")
                return False
            ext = path.splitext(wt_path)[1].lower()
        else:
            wt_path = self.path
            ext = self.ext
        if isinstance(self.lrc, list):
            _lines = ""
            for _i in self.lrc:
                _lines += _i+"\n"
            self.lrc = _lines
        else:
            print(f"             self.lrc 无效格式[{type(self.lrc)}]")
            return False
        try:
            if ext == '.flac':
                self.write_flac_lyrics(wt_path, self.lrc)
            elif ext == '.mp3':
                self.write_mp3_lyrics_mutagen(wt_path, self.lrc)
            elif ext == '.opus':
                self.write_opus_lyrics(wt_path, self.lrc)
            elif ext in [".lrc", ".txt"]:
                with open(wt_path, 'w+', encoding='utf-8') as f:
                    f.write(self.lrc)
            return True
        except Exception as e:
            print(f"             写入歌词失败: {wt_path}\n{e}")
            return False

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

            # 查找USLT帧（非同步歌词）
            for frame in audio.values():
                if isinstance(frame, USLT):
                    return frame.text

            # 查找SYLT帧（同步歌词）
            for frame in audio.values():
                if isinstance(frame, SYLT):
                    return "\n".join([text for (_, text) in frame.text])

            return None
        except Exception as e:
            print(f"             读取MP3歌词时出错: {e}")
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


class LyrTrans:
    def __init__(self):
        # 输入日语，返回注音
        # "hira" 平假名
        # "kana" 片假名
        self.kks = pykakasi.kakasi()

    def trans(self, _text, _seq="hira"):
        result = self.kks.convert(_text)
        _line = ""
        if _seq == "hira":
            for item in result:
                if item["orig"] in [item["hira"], item["kana"]]:
                    _line += item["orig"]
                else:
                    _line += self.align_strings(item["orig"], item["hira"])
        elif _seq == "roma":
            for item in result:
                _line += item["hepburn"]
        return _line

    @staticmethod
    def align_strings(str1, str2):
        # 初始化矩阵
        _m = len(str1)
        _n = len(str2)
        dp = [[0] * (_n + 1) for _ in range(_m + 1)]

        # 填充矩阵
        for _i in range(_m + 1):
            for _j in range(_n + 1):
                if _i == 0 or _j == 0:
                    dp[_i][_j] = _i + _j
                elif str1[_i - 1] == str2[_j - 1]:
                    dp[_i][_j] = dp[_i - 1][_j - 1]
                else:
                    dp[_i][_j] = 1 + min(dp[_i - 1][_j], dp[_i][_j - 1])

        # 回溯找出对齐方式
        _i, _j = _m, _n
        align1 = []
        _kanji = False
        while _i > 0 or _j > 0:
            if _i > 0 and _j > 0 and str1[_i - 1] == str2[_j - 1]:
                align1.append(str1[_i - 1])
                _i -= 1
                _j -= 1
            elif _i > 0 and (_j == 0 or dp[_i - 1][_j] < dp[_i][_j - 1]):
                if _kanji:
                    align1.append("[")
                    _kanji = False
                _i -= 1
            else:
                if _kanji:
                    align1.append(str2[_j - 1])
                else:
                    _kanji = True
                    align1.append(str2[_j - 1] + "]")
                _j -= 1

        return ''.join(reversed(align1))


def check_str_regex(_text):
    pattern1 = r'\[\d+:\d+\.\d+\]'  # ^表示开头，\d{2}表示两位数字
    if _match := re.match(pattern1, _text):
        if _match is not None:
            return _match.group(0), _text.strip(_match.group(0))
    pattern2 = r'\[\d+:\d+\]'
    if _match := re.match(pattern2, _text):
        if _match is not None:
            return _match.group(0), _text.strip(_match.group(0))
    return None, None


def reconsitution(_in_lines):
    # 初始化时间码和索引变量
    newline = []
    time_processed = []
    # 遍历每一行
    is_mached = False
    for _i, line in enumerate(_in_lines):
        # 使用正则表达式查找时间码
        pattern1 = r'\[\d+:\d+\.\d+\]'
        time_match = re.search(pattern1, line)  # 从第一次找到时间码开始
        if time_match:
            for j in range(_i + 1, len(_in_lines)):             # 之后找到重复的一个时间码，也就是找到对应的歌词翻译
                is_mached = False                          # 此处判断此for循环有没有找到对应歌词，如果找到了那么循环结束后不需要给newline加上原句
                if _in_lines[j].find(time_match.group(0)) != -1:
                    is_mached = True
                    current_time = time_match.group(0)
                    time_processed += [current_time]         # 将处理过的时间存入变量中，防止后面重复写入
                    newline += [_in_lines[j].rstrip("\n") + "\n"]
                    newline += [line.rstrip("\n")+"\n"]
            if not is_mached and (time_match.group() not in time_processed):
                newline += [line]
        else:
            newline += [line]
    return newline


def lrclines_trans(_in_lines):
    _pat1 = re.compile(r'\[[a-zA-Z]+:')
    _lrc_line1 = []
    _pat2 = re.compile(r'词：|曲：|歌手：')
    _pat3 = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')
    _pat4 = re.compile(r'[\u4e00-\u9faf'
                       r'\u3400-\u4dbf'
                       r'\U00020000-\U0002a6df'
                       r'\U0002a700-\U0002b73f'
                       r'\U0002b740-\U0002b81f'
                       r'\U0002b820-\U0002ceaf]')
    _lrc_line2 = []
    space_flag = False
    start_flag = False
    count = 0
    start_num = None
    _lrc_line3 = []
    _lines = _in_lines
    # 读取所有行到列表中
    for _i, line in enumerate(_lines):
        if not line:
            pass
        elif line[0] != "[":
            print(f"             无效行[{_i}]：", line.rstrip("\n"))
        elif bool(re.search(_pat1, line)):
            _lrc_line1 += [line]
        elif (mat := check_str_regex(line)) != (None, None):
            # print(mat)
            if not mat[1]:  # 空行
                if start_flag and not space_flag:
                    space_flag = True
            elif bool(re.search(_pat2, line)):  # 歌曲信息行
                space_flag = False
                _lrc_line2 += [line]
                count = 0
            else:
                # print(line)
                space_flag = False
                if not count:
                    start_num = _i
                    count += 1
                elif 4 > count > 0:
                    count += 1
                else:
                    break
        else:
            print(f"             无效行[{_i}]：", line.rstrip("\n"))
    # print(lines[start_num:])
    # print("")
    ph_flag = False

    for _i, line in enumerate(_lines[start_num:]):
        if _i in [3, 4, 5]:
            time_match = check_str_regex(line)[0]
            for j, _line in enumerate(_lines[start_num + 1 + _i:]):
                if time_match in _line:
                    ph_flag = True
    if ph_flag:
        _lines = _lines[:start_num] + reconsitution(_lines[start_num:])
    # print(lines[start_num:])
    kana_flag = False
    for _i, line in enumerate(_lines[start_num:]):
        if bool(re.search(_pat3, line)):
            kana_flag = True
            break
        elif _i > 15:
            break
    if not kana_flag:
        return False
    nt = ""
    kl, hl, el, cl = "", "", "", ""
    lt = LyrTrans()
    for _i, line in enumerate(_lines[start_num:]):
        line = line.replace("\n", "").replace("\r", "")
        pt = nt
        nt, nl = check_str_regex(line)
        if nt is not None:
            pass
        elif not line:
            continue
        elif bool(re.match(_pat1, line)):
            _lrc_line1 += [line]
            continue
        else:
            print(f"             无效行[{start_num + _i}]：", line.rstrip("\n"))
            continue
        if nt != pt:
            #  执行
            _list = seq.split("-")
            for item in _list:
                if item == "hira":
                    if not hl:
                        hl = lt.trans(kl)
                        if hl:
                            _lrc_line3 += [hl]
                    else:
                        _lrc_line3 += [hl]
                elif item == "kanji" and kl:
                    _lrc_line3 += [kl]
                elif item == "roma" and el:
                    if not el:
                        el = lt.trans(kl, "roma")
                        if el:
                            _lrc_line3 += [el]
                    else:
                        _lrc_line3 += [el]
                elif item == "chin" and cl:
                    _lrc_line3 += [cl]
                elif item not in ["hira", "kanji", "roma", "chin"]:
                    raise ValueError("seq 值不规范")
            if not hl and el and "roma" not in seq:
                _lrc_line3 += [el]
            kl, hl, el, cl = "", "", "", ""

        fh = bool(re.search(_pat3, line))
        fk = bool(re.search(_pat4, line))
        if fh:
            if fk:
                kl = line
            else:
                hl = line
        else:
            if fk:
                cl = line
            else:
                el = line
    _out_lines = []
    for _i in (_lrc_line1+_lrc_line2+_lrc_line3):
        _out_lines += [_i]
    return _out_lines


def main(in_path):
    mle = MusicLrcEditor(in_path)
    if mle.isreadlrc():
        lrc = mle.read_lyrics()
        if out_lines := lrclines_trans(lrc):
            mle.lrc = out_lines
            out_path = path.splitext(path.join(r"E:\Kin-Desktop\lrc", path.split(in_path)[1]))[0] + ".lrc"
            if not path.exists(out_path):
                with open(out_path, 'w+', encoding='utf-8') as f:
                    f.write("")
            mle.write_lyrics()  # out_path
            print("             处理完成")
        else:
            print("             不为日语歌词")
    else:
        print("             error:读取异常")


def dir_to_files(_dir):
    file_path = []
    for _root, _ds, _fs in enumerate(os.walk(_dir)):
        for _f in _fs:
            file_path = [path.join(_root, _f)]
    return file_path


def proc(_file_list):
    for _i, file_path in enumerate(_file_list):
        print("-------------------------------------------")
        print(f"开始处理[{_i}]："+file_path)
        main(file_path)
    print("===========================================")


def from_file():
    global seq
    initial_dir, seq = load_last_folder()
    file_paths = filedialog.askopenfilenames(initialdir=initial_dir)
    save_last_folder(path.split(file_paths[0])[0], seq)

    file_list = []
    for _path in file_paths:
        if os.path.isdir(_path):
            file_list += dir_to_files(_path)
        else:
            file_list += [_path]
    proc(file_list)


def from_folder():
    global seq
    initial_dir, seq = load_last_folder()
    folder_path = filedialog.askdirectory(initialdir=initial_dir)
    save_last_folder(folder_path, seq)
    proc(dir_to_files(folder_path))


if __name__ == "__main__":
    print("============欢迎使用日语音乐歌词注音工具============")
    print("======使用前请做好数据备份，本工具不能替代人工检查=====")
    print("作者B站： 绘星痕")
    print("项目地址：\nhttps://github.com/Kin-L/JLTool\nhttps://gitee.com/huixinghen/JLTool")
    if len(sys.argv) > 1:
        print("Tips:默认设置歌词顺序为 中文-假名-日语 \n"
              "如需更改请在config.json文件中修改\n"
              "对应关系如下，中间用“-”分隔：\n"
              "chin  | 中文\n"
              "hira  | 假名注音\n"
              "kanji | 日语\n"
              "roma  | 罗马音")  # "chin-hira-kanji"
        seq = load_last_folder()[1]
        file_list = []
        for cm in sys.argv[1:]:
            if os.path.isdir(cm):
                file_list += dir_to_files(cm)
            else:
                file_list += [cm]
        proc(file_list)
        input("敲击回车结束并关闭窗口")
    else:
        print("============本窗口显示处理信息，请勿关闭============")
        print("Tips:默认设置歌词顺序为 中文-假名-日语 \n"
              "如需更改请在config.json文件中修改\n"
              "对应关系如下，中间用“-”分隔：\n"
              "chin  | 中文\n"
              "hira  | 假名注音\n"
              "kanji | 日语\n"
              "roma  | 罗马音")  # "chin-hira-kanji"
        # 主程序入口
        root = tk.Tk()
        root.title("日语音乐歌词注音工具")

        # 设置窗口大小并锁定
        root.geometry("150x100")
        root.resizable(False, False)  # 锁定窗口大小
        center_window(root)  # 居中窗口

        # 标签和合并按钮
        label = tk.Label(root, text="使用前请做好数据备份，本工具不能替代人工检查")
        label.pack(pady=8)

        # 合并按钮
        btn_process = tk.Button(root, text="选择文件夹",
                                command=from_folder)
        btn_process.pack(pady=8)
        btn_process2 = tk.Button(root, text="选择文件(可复选)",
                                 command=from_file)
        btn_process2.pack(pady=8)

        # 启动GUI主循环
        root.mainloop()
