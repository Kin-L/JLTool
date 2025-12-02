import re
import shutil
from os import path, makedirs
import pykakasi
import langid
import opencc
import MeCab
import unicodedata
pattern = r'\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]'
_pat1 = re.compile(r'\[[a-zA-Z]+:')
_pat2 = re.compile(r'[词詞曲歌手制作人原唱]\s*[:∶：]')  # r'词：|曲：|歌手：'
_pat3 = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')
_pat4 = re.compile(r'[\u4e00-\u9faf'
                   r'\u3400-\u4dbf'
                   r'\U00020000-\U0002a6df'
                   r'\U0002a700-\U0002b73f'
                   r'\U0002b740-\U0002b81f'
                   r'\U0002b820-\U0002ceaf]')
_pat5 = re.compile(r'\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]')


def spstring(text):
    punctuation_pattern = r'[，。！？；：“”‘’（）~【】＜＞「」、\.,!?;:"\'\(\)\[\]\{\}]'
    text = re.sub(punctuation_pattern, '', text)
    text = re.sub(r'\s+', '', text).strip()
    return katakana_to_hiragana(text).lower()

def katakana_to_hiragana(text):
    hiragana = []
    for char in text:
        code = ord(char)
        # 片假名范围: 0x30A0-0x30FF
        # 平假名范围: 0x3040-0x309F
        if 0x30A0 <= code <= 0x30FF:
            hiragana_char = chr(code - 0x60)  # 片假名和平假名的Unicode码相差96(0x60)
            hiragana.append(hiragana_char)
        else:
            hiragana.append(char)
    return ''.join(hiragana)

def checktrad(text):
    """判断字符串是否包含繁体字"""
    converter = opencc.OpenCC('t2s')  # 繁体转简体配置
    simplified = converter.convert(text)
    # print(simplified)
    return simplified != text  # 如果转换前后不同，说明包含繁体字




def katakana_to_hiragana(katakana):
    """将片假名转换为平假名"""
    hiragana = []
    for char in katakana:
        # 片假名和平假名的Unicode码相差96
        if 'ァ' <= char <= 'ヺ':
            hiragana.append(chr(ord(char) - 96))
        else:
            hiragana.append(char)
    return ''.join(hiragana)


def add_furigana(text, use_hiragana=True):
    """
    使用MeCab为日语文本添加平假名或片假名注音

    参数:
        text: 日语文本字符串
        use_hiragana: 若为True则使用平假名，否则使用片假名

    返回:
        带有注音的文本，格式为"汉字[注音]"
    """
    # 初始化MeCab分词器
    tagger = MeCab.Tagger()

    # 解析文本
    node = tagger.parseToNode(text)

    # 存储结果的列表
    result = []

    # 遍历解析结果
    while node:
        # 获取表面形式
        surface = node.surface
        # 获取特征信息（包含读音）
        feature = node.feature

        # 只有非空字符串才处理
        if surface:
            # 分割特征信息
            feature_parts = feature.split(',')

            # 读音通常在第7个位置（索引6）
            if len(feature_parts) > 7 and feature_parts[6] and feature_parts[6] != '*':
                reading = feature_parts[6]

                # 如果需要平假名，则进行转换
                if use_hiragana:
                    phonetic = katakana_to_hiragana(reading)
                else:
                    phonetic = reading

                # 当表面形式与读音不同时才添加注音
                if reading != surface:
                    result.append(phonetic)
                else:
                    result.append(surface)
            else:
                # 没有读音信息时直接添加表面形式
                result.append(surface)

        # 移动到下一个节点
        node = node.next

    return ''.join(result)


class LyrTrans:
    def __init__(self):
        # 输入日语，返回注音
        # "hira" 平假名
        # "kana" 片假名
        self.kks = pykakasi.kakasi()

    def trans(self, _text: str, _seq: str = "hira"):
        res = add_furigana(_text)
        
        if _seq == "hira":

            if res == _text:
                return _text
            else:
                return self.align_strings(_text, res)
        elif _seq == "roma":
            _line = ""
            for item in self.kks.convert(res):
                _line += item["hepburn"]
            return _line

    @staticmethod
    def align_strings(str1: str, str2: str):
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

def stringconv(text):
    punctuation_pattern = '\xa0\u3000'
    text = re.sub(punctuation_pattern, ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def lrc_split(lrc_lines: list) -> [list, list, list]:
    exclude = ["//"]
    _lis1 = []  # [al:朗朗]
    _lis2 = []
    _lis3 = []  # 这是一行没有时间戳的歌词
    nlist = []
    for line in lrc_lines:
        if not line:
            continue
        else:
            line = stringconv(line)

            if bool(re.search(_pat1, line)):
                if ":" in line and len(line) < 100:
                    if line.split(":")[1].strip("]"):
                        _lis1.append(line)
                continue
            matches = re.finditer(pattern, line)
            timestamps = []
            for match in matches:
                min_part = match.group(1)
                sec_part = match.group(2)
                ms_part = match.group(3) if match.group(3) else '000'  # 默认毫秒为000
                timestamps.append((min_part, sec_part, ms_part))
            if timestamps:
                # 将时间戳转换为统一格式 (分:秒.毫秒)
                formatted_timestamps = []
                for _min, sec, ms in timestamps:
                    # 补零处理
                    _min = _min.zfill(2)
                    sec = sec.zfill(2)
                    ms = ms.ljust(3, '0')[:3]  # 确保毫秒是3位
                    formatted = f"{_min}:{sec}.{ms}"
                    formatted_timestamps.append(formatted)

                # 提取歌词内容 (移除所有时间戳后的部分)
                content = re.sub(pattern, '', line).strip()
                contents = [content]
                if not content or content in exclude or " - " in content:
                    continue
                elif " / " in content:
                    contents = content.split(" / ")
                if bool(re.search(_pat2, content)):
                    for content in contents:
                        _lis2.append(f"[00:00.000]" + content)
                else:
                    for timestamp in formatted_timestamps:
                        for content in contents:
                            nlist.append((timestamp, content))
            else:
                _lis3.append(line)

    return _lis1+_lis2, lrc_sort(nlist) if nlist else nlist, _lis3


def check_jap(line_list):
    kana_num = 0
    for _i, (_, line) in enumerate(line_list):
        if bool(re.search(_pat3, line)):
            kana_num += 1
            if kana_num > 2:
                return True
        elif _i > 15:
            return False
    return False


# 歌词排序
def lrc_sort(lrc_list: list) -> list:
    times, _ = zip(*lrc_list)
    times = list(dict.fromkeys(times))
    nl = []
    for time in times:
        for t, l in lrc_list:
            if time == t and [t, l] not in nl:
                nl += [[t, l]]
    return nl


def listsort(lrc_list: list) -> list:
    times = list(zip(*lrc_list))[0]
    times = list(dict.fromkeys(times))
    nl = []
    for time in times:
        for item in lrc_list:
            if time == item[0]:
                nl.append(item)
    return nl


def choose_root(lrc_list: list) -> str:
    _lh, _lo, _lt = [], [], []
    for y in lrc_list:
        fk = bool(re.search(_pat4, y))
        if bool(re.search(_pat3, y)):
            if fk:
                return y
            else:
                _lh += [y]
        else:
            if fk and checktrad(y):
                _lt += [y]
            else:
                _lo += [y]
    lis = _lt + _lh + _lo
    for i in lis:
        if i:
            if len(i) == 1:
                return i[0]
            elif len(i) == 2:
                if spstring(i[0]) == spstring(i[1]):
                    return i[0]
            raise RuntimeError(lrc_list)
    return ""


# 提取歌词主干
def get_lrc_root(lrc_list: list, flag=False) -> list:
    nl: list = []
    px = ""
    pyl: list = []
    for n, (x, y) in enumerate(lrc_list):
        if px != x:
            num = len(pyl)
            if num > 2:
                if line := choose_root(pyl[1:]):
                    nl += [[pyl[0], line]]
                else:
                    print(f"跳过:", pyl)
            elif num == 2:
                nl += [pyl]
            pyl = [x]
        if y:
            pyl += [y]
        px, py = x, y
    else:
        num = len(pyl)
        if num > 2:
            if line := choose_root(pyl[1:]):
                nl += [[pyl[0], line]]
            else:
                print(f"跳过:", pyl)
        elif num == 2:
            nl += [pyl]
    return nl


def checktrans(_list: list):
    _list = list(_list)
    _list.reverse()
    time = ""
    linelist = []
    flag = False
    for t, l in _list:
        if l:
            if not bool(re.search(_pat3, l)) and not l.isascii():
                flag = True
        if time != t:
            if flag:
                break
            else:
                linelist = []
                linelist.append([t, l])
        else:
            linelist.append([t, l])
    for _, i in linelist:
        if bool(re.search(_pat3, i)):
            return False
    return True


def movefile(_path, dire):
    _dir, _name = path.split(_path)
    if not path.exists(path.join(_dir, dire)):
        try:
            makedirs(path.join(_dir, dire))
        except:
            ...
    shutil.move(_path, path.join(_dir, dire, _name))


def arrangelines(inlines):
    outitems = []
    for item in inlines:
        num = 0
        _lh, _lo, _lc, _lr, _lt = [], [], [], [], []
        line = [item[0]]
        for y in item[1:]:
            fk = bool(re.search(_pat4, y))
            if bool(re.search(_pat3, y)):
                if fk:
                    _lr += [y]
                else:
                    _lh += [y]
            else:
                if fk:
                    if checktrad(y):
                        _lt += [y]
                    else:
                        _lc += [y]
                else:
                    _lo += [y]
        flag = False
        if not _lr:

            if len(_lc) > 1:
                confidence, text = None, None
                for i in _lc:
                    lang, conf = langid.classify(i)
                    # print(lang, conf )
                    if lang == 'zh' and (confidence is None or conf > confidence):
                        confidence, text = conf, i
                if confidence is not None:
                    _lr = [text]
                    _lc.remove(text)
        # print("_lr:", _lr)
        if not _lr:
            lis = [_lt, _lh, _lo]
            for n, i in enumerate([_lt, _lh, _lo]):
                if i:
                    if len(i) == 1:
                        _lr = i
                        lis[n] = [""]
                        break
                    elif len(i) == 2:
                        r1, r2 = i
                        if spstring(r1) == spstring(r2):
                            if len(r1) > len(r2):
                                r = r2
                            else:
                                r = r1
                            _lr = [r]
                            num += 1
                            lis[n] = [""]
                            break
                    print("errortype1:", item)
                    # print("lis:", lis)
                    flag = True
                    break
                    # raise RuntimeError(item)
            else:
                _lr = [""]
            if flag:
                continue
            [_lt, _lh, _lo] = lis
        # print("22", [_lr, _lc, _lh, _lo])
        for i in [_lr, _lc, _lh, _lo]:
            if i:
                lenth = len(i)
                if lenth == 1:
                    line.append(i[0])
                elif lenth == 0:
                    line.append("")
                elif lenth == 2:
                    # print("11", spstring(i[0]), spstring(i[1]))
                    r1, r2 = i
                    if spstring(r1) == spstring(r2):
                        if len(r1) > len(r2):
                            r = r2
                        else:
                            r = r1
                        num += 1
                        line.append(r)
                else:
                    print("errortype2:", item)
                    flag = True
                    break
            else:
                line.append("")
        if flag:
            continue
        lis = list(line)
        while "" in lis:
            lis.remove("")
        # print(line, item)
        if len(lis) == len(item) - num:
            outitems.append(line)
    return outitems

if __name__ == "__main__":
    # print(spstring('Beautiful world...'))
    # print(checktrad("今百年戦争"))
    lis = [['[01:59.670]', '糟糕讨厌的话 啦啦噜',  'ヤバイヤダしならららる'],
           ['[00:12.460]', '想要使坏',  'イジワルしたい'],
           ['[00:22.664]', '必须加以控制',  'コントロールしなきゃ'], ]
    lis1 = [['[01:59.670]', '糟糕讨厌的话 啦啦噜', '[やばいやだ]しならららる', 'ヤバイヤダしならららる'],
           ['[00:12.460]', '想要使坏', '[いじわる]したい', 'イジワルしたい'],
           ['[00:22.664]', '必须加以控制', '[こんとろ]ー[る ]しなきゃ', 'コントロールしなきゃ'],
            ['[00:12.380]', 'Ready to fly（一！二！三！四！）', '[r]eady to fly（one！two! three! four!）', 'Ready to fly（one！two! three! four!）']]
    print(arrangelines(lis1))
