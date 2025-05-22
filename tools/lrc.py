import re
import pykakasi
from difflib import SequenceMatcher
import langid
_pat1 = re.compile(r'\[[a-zA-Z]+:')
_pat2 = re.compile(r'[词詞曲歌手]\s*[:：]')  # r'词：|曲：|歌手：'
_pat3 = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')
_pat4 = re.compile(r'[\u4e00-\u9faf'
                   r'\u3400-\u4dbf'
                   r'\U00020000-\U0002a6df'
                   r'\U0002a700-\U0002b73f'
                   r'\U0002b740-\U0002b81f'
                   r'\U0002b820-\U0002ceaf]')


class LyrTrans:
    def __init__(self):
        # 输入日语，返回注音
        # "hira" 平假名
        # "kana" 片假名
        self.kks = pykakasi.kakasi()

    def trans(self, _text: str, _seq: str = "hira"):
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


def lrc_split(lrc_lines: list) -> [list, list, list]:
    pattern = r'\[(\d{1,}):(\d{2})(?:[.:](\d{1,3}))?\]'
    # 存储结果的列表
    result = []  # [00:01.000] 这是简式时间戳的歌词
    _lis1 = []  # [al:朗朗]
    _lis2 = []
    _lis3 = []  # 这是一行没有时间戳的歌词
    # 按行处理歌词
    lnum = 0
    nlist = []
    for num, line in enumerate(lrc_lines):
        if not line:
            continue
        else:
            if bool(re.search(_pat1, line)):
                _lis1.append(line)
            else:
                nlist += [line]
    lrc_lines = nlist
    for num, line in enumerate(lrc_lines):
        if bool(re.search(_pat2, line)) and num < lnum+5:
            lnum = num
    _lis2 = lrc_lines[:lnum+1]
    if lnum == len(lrc_lines):
        return [], [], []
    for line in lrc_lines[lnum+1:]:
        line = line.strip()
        if not line:
            continue
        # 查找所有时间戳
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
            if bool(re.search(_pat2, content)):
                for timestamp in formatted_timestamps:
                    _lis2.append(f"[00:00.000]" + content)
            else:
                for timestamp in formatted_timestamps:
                    result.append((timestamp, content))
        else:
            # 没有时间戳的行作为普通歌词
            if line:
                _lis3.append(line)
    return _lis1+_lis2, result, _lis3


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


def choose_root(lrc_list: list) -> str:
    _time = lrc_list[0][0]
    _lh, _lk, _lo = [], [], []
    for n, y in enumerate(lrc_list):
        fh = bool(re.search(_pat3, y))
        fk = bool(re.search(_pat4, y))
        if fh:
            if fk:
                return y
            else:
                _lh += [n]
        else:
            if fk:
                _lk += [n]
            else:
                _lo += [n]
    lenh, lenk = len(_lh), len(_lk)
    # print(_lh, _lk)
    # print(lrc_list)
    if lenh and not lenk:
        return lrc_list[_lh[0]]
    elif lenh and lenk in [1, 2]:
        for _num in _lk:
            _strh, _strk = lrc_list[_lh[0]], lrc_list[_num]
            if SequenceMatcher(None, _strh, LyrTrans().trans(_strk)).ratio() >= 0.7:
                return lrc_list[_lk[0]]
        if lenk == 1:
            return lrc_list[_lh[0]]
    elif lenk > 1:
        _lis = [-500, ""]
        for num in _lk:
            _lan = langid.classify(lrc_list[num])
            if _lan[0] == 'zh' and _lan[1] > _lis[0]:
                _lis = [_lan[1], lrc_list[num]]
        if _lis[1]:
            return _lis[1]
    if len(_lo) == 1:
        pass
    elif len(_lo) == 2:
        _str1, _str2 = lrc_list[_lo[0]], lrc_list[_lo[1]]
        if SequenceMatcher(None, _str1, _str2).ratio() >= 0.7:
            return lrc_list[_lo[0]]
        else:
            raise RuntimeError(lrc_list)
    else:
        raise RuntimeError(lrc_list)
    return lrc_list[_lo[0]]


# 提取歌词主干
def get_lrc_root(lrc_list: list) -> list:
    nl: list = []
    px = ""
    pyl: list = []
    for n, (x, y) in enumerate(lrc_list):
        if px != x:
            num = len(pyl)
            if num > 2:
                nl += [pyl[0], choose_root(pyl[1:])]
            elif num == 2:
                nl += [pyl]
            pyl = [x]
        if y:
            pyl += [y]
        px, py = x, y
    else:
        num = len(pyl)
        if num > 2:
            nl += [pyl[0], choose_root(pyl[1:])]
        elif num == 2:
            nl += [pyl]
    return nl


if __name__ == "__main__":
    txt = """[00:00.0]弦编曲：兼松衆
    弦编曲：兼松衆
    [al:朗朗]
[00:02.340]Tiny Stars - 伊達さゆり/Liyuu
[00:03.190]駆け抜けるシューティングスター
[00:03.920]追いかけて星になる
[00:07.430]煌めけ
[00:13.360]小星星
[00:22.390]何も見えない夜空
[00:24.750]ひとすじの流れ星
[00:28.110]キラキラまぶしい姿に
[00:31.570]勇気をもらったよ
[00:36.100]いつかあんな風に
[00:38.490]なれる日がくるかもしれない
[00:41.840]希望が運んできたんだ
[00:45.330]新しい季節のにおい
[00:49.0]Hello （Hello） my dream
[00:51.360]ハジメテを始めよう（不安でも）
[00:55.590]行ける（平気）いつも（そうさ）
[00:59.20]絆がここにある
[01:02.60]駆け抜けるシューティングスター
[01:05.450]追いかけて星になる
[01:09.120]止まらない 止まれないよ
[01:12.330]まだちいさくても
[01:15.720]ひとりじゃないから
[01:19.210]諦めないで進めるんだ
[01:23.690]立ちあがった数だけ光るTiny Stars
[01:29.900]煌めけ
[01:37.770]なにげない言葉が
[01:40.240]いつの間にか力に変わる
[01:43.590]だから全部ぶつけ合うの
[01:47.30]よろこびもかなしみも
[01:50.660]I know （I know） the stars
[01:53.0]ひかりを知った目には
[01:55.780]（映ってるの）
[01:57.320]息を（切らし）未来（つかむ）
[02:00.690]奇跡のものがたり
[02:03.720]願い乗せシューティングスター
[02:07.200]遠い空でまたたく
[02:10.820]届かない 届きたいよ
[02:14.90]もっとスピードあげて
[02:17.430]向かい風にまた
[02:20.880]心ごとさらわれそうでも
[02:25.280]ささやき合う
[02:27.130]そっと芽を出した想い 守ろう
[02:46.300]信じてる （それだけじゃ）
[02:49.820]叶うわけないよ
[02:52.420]叶うまで （走るしかない）
[02:55.510]暗闇つきぬけて
[03:00.350]輝きのシューティングスター
[03:03.740]追いかけて星になる
[03:07.420]止まらない 止まれないよ
[03:10.660]まだちいさくても
[03:14.60]いつまでも一緒に
[03:17.480]同じ夢見続けたいから
[03:22.230]かたく手と手つないで行こう Tiny Stars
[03:28.190]煌めけ
[03:35.230]煌めけ

[00:03.190](香音)追逐夜空中飞掠的流星
[00:03.920](可可)直到成为最闪亮的自己！
[00:07.430](可香)闪耀吧！
[00:22.390](香音)一望无际的漆黑夜空里
[00:24.750]唯有缤纷如雨的流星
[00:28.110]是那熠熠生辉的光影
[00:31.570]给了我不断前行的勇气
[00:36.100](可可)期盼有朝一日也可以
[00:38.490]成为那样一个闪耀的自己
[00:41.840]怀抱热切希望
[00:45.330]迎接崭新季节的降临
[00:49.0](香 可)你好（你好）
[00:51.360]我的梦想 就从此刻开始吧!(就算心有不安)
[00:55.590]也没问题 别担心 不论何时 没错
[00:59.20](可香)我们的羁绊就在这里
[01:02.60]追逐夜空中飞掠的流星
[01:05.450]直到成为最闪亮的自己！
[01:09.120](香 可)不会止步 还不能止步
[01:12.330]即使如此渺小
[01:15.720]只因并不孤单
[01:19.210]才能不放弃 努力地往前走
[01:23.690]每当站起身就会闪耀的小星星
[01:29.900]闪耀吧！
[01:37.770](可可)不经意间的话语
[01:40.240]不知不觉中变成了力量
[01:43.590](香音)所以我们将这一切交织相倾诉
[01:47.30](可香)不论喜悦或是悲伤
[01:50.660](可 香)我知道（我很明白）
[01:53.0]这颗新星在认知光芒的眼眸中倒映出来
[01:57.320]哪怕气喘不止 也要抓住未来
[02:00.690](可香)属于奇迹的故事
[02:03.720]满载心愿飞掠的流星
[02:07.200]在遥远的夜空下闪烁
[02:10.820](可 香)还无法传到 想要赶快传到
[02:14.90]还要更快一点啊
[02:17.430]迎着逆风前进也无妨
[02:20.880]就算我的心快要被摘去
[02:25.280]也要将细声细语悄然间萌生的感情
[02:27.130]紧紧地守护
[02:46.300](可 香)仅仅如此相信着
[02:49.820](可香)梦想是实现不了的
[02:52.420](香 可)在梦想实现前 只有不断前进
[02:55.510](可香)穿过黑暗吧
[03:00.350](可可)追逐夜空中飞掠的流星
[03:03.740]直到成为最闪亮的自己！
[03:07.420](香音)不会止步 还不能止步
[03:10.660]即使如此渺小
[03:14.60](可香)只因想一直和你一起
[03:17.480]继续追寻同一个梦想
[03:22.230]紧紧牵起彼此的手 一同前行的小星星
[03:28.190]闪耀吧！
[03:35.230]闪耀吧！


[00:03.920]o i ka ke te ho shi ni na ru
[00:24.750]hi to su ji no na ga re bo shi
[00:36.100]i tsu ka a n na fu u ni
[01:05.450]o i ka ke te ho shi ni na ru
[01:15.720]hi to ri ja na i ka ra
[01:29.900]ki ra me ke
[01:50.660]I know I know ) the stars
[02:10.820]to do ka na i to do ki ta i yo
[02:17.430]mu ka i ka ze ni ma ta
[02:49.820]ka na u wa ke na i yo
[03:00.350]ka ga ya ki no shuu te i n gu su taa
[03:03.740]o i ka ke te ho shi ni na ru
[03:28.190]ki ra me ke"""
    lis1, lis2, lis3 = lrc_split(txt)
    # print("lis:", lis)
    # lis1, lis2, lis3 = lrc_split2(lis)
    # print("lis1:", lis1)
    # print("lis2:", lis2)
    # print("lis3:", lis3)
    lis6 = lrc_sort(lis2)
    print(get_lrc_root(lis6))

    # print("lis6:", "\n".join([f'[{i}]'+text for i,text in lis6]))
