from os import path
from time import sleep

from openai import OpenAI
from datetime import datetime
import difflib
import re


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


def norstring(text):
    punctuation_pattern = r'[，。！？；：“”‘’（）【】＜＞「」、\.,!?;:"\'\(\)\[\]\{\}]'
    text = re.sub(punctuation_pattern, ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return katakana_to_hiragana(text).lower()


def spstring(text):
    punctuation_pattern = r'[，。！？；：“”‘’（）【】＜＞「」、\.,!?;:"\'\(\)\[\]\{\}]'
    text = re.sub(punctuation_pattern, '', text)
    text = re.sub(r'\s+', '', text).strip()
    return katakana_to_hiragana(text).lower()


def stringsim(str1, str2):
    str1_norm = norstring(str1)
    str2_norm = norstring(str2)
    if str1_norm == str2_norm:
        return True
    else:
        if re.sub(r'[(\[{（].*?[）)\]}]', '', str1) == str2:
            return True
        return False


class DSAPI:
    def __init__(self, api_key):
        self.client = OpenAI(
            api_key=api_key,  #
            base_url="https://api.deepseek.com",
        )
        self.hira_prompt = r"""接下来给出一些歌词，将输入歌词中
            1、舍去中文句子
            2、舍去元信息句子
            3、输入句不能合并，不能拆分。
            4、进行转化：将句子中的日语转化为全平假名注音，保留原标点和英文
            5、输出句的格式为：输入句//转化句
            输出 结果不需要多余的解释。
            示例格式：
            输入：
            君の名前は何ですか
            なれないから
            歩き出そう dreaming way
            dreaming way
            输出：
            君の名前は何ですか//きみのなまえはなんですか
            なれないから//なれないから
            歩き出そう dreaming way//あるきだそう dreaming way
            dreaming way//dreaming way"""
        self.trans_prompt = r"""接下来给出一些歌词，将输入歌词中
            1、舍去中文句子
            2、舍去元信息句子
            3、输入句不能合并，不能拆分。
            4、进行转化：将句子中的日语和英语翻译为中文，保留原标点
            5、输出句的格式为：输入句//转化句
            输出 结果不需要多余的解释。
            示例格式：
            输入：
            始まったばかりの夢から射す光
            トキめくよ dreaming light
            始まったばかりの夢から射す光
            トキめくよ dreaming light
            dreaming light
            输出：
            始まったばかりの夢から射す光//从刚启程的梦中透出的光
            トキめくよ dreaming light//令人心动啊 逐梦之光
            始まったばかりの夢から射す光//从刚启程的梦中透出的光
            トキめくよ dreaming light//令人心动啊 逐梦之光
            dreaming light//逐梦之光"""
        self.roma_prompt = r"""接下来给出一些歌词，将输入歌词中
            1、舍去中文句子
            2、舍去元信息句子
            3、输入句不能合并，不能拆分。
            4、进行转化：将句子中的日语转化为全罗马音注音，保留原标点和英文
            5、输出句的格式为：输入句//转化句
            输出 结果不需要多余的解释。
            示例格式：
            输入：
            君の名前は何ですか
            なれないから
            歩き出そう dreaming way
            dreaming way
            输出：
            君の名前は何ですか//ki mi no na ma e wa na n de su ka
            なれないから//na re na i ka ra
            歩き出そう dreaming way//a ru ki da so u dreaming way
            dreaming way//dreaming way"""

    @staticmethod
    def align_strings(str1, str2):
        _str = str(str1)
        str1 = katakana_to_hiragana(str1)
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
        strin = ''.join(reversed(align1))
        if strin == str1:
            return _str
        else:
            return strin

    def get_dsres(self, _user_prompt, inpath, _system_prompt):
        messages = [{"role": "system", "content": _system_prompt},
                    {"role": "user", "content": _user_prompt}]

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages
        )
        res = response.choices[0].message.content
        output = response.model_dump()
        output["input"] = _user_prompt
        name = path.splitext(path.split(inpath)[1])[0]
        outpath = "output/"+datetime.now().strftime("%Y-%m-%d %H-%M-%S")+f"{name}.txt"
        with open(outpath, 'a+', encoding='utf-8') as file:
            file.write(str(output))
        return res, outpath

    def get_hira(self, _input, inpath):
        if isinstance(_input, str):
            res, outpath = self.get_dsres(_input, inpath, self.hira_prompt)
            return self.align_strings(_input.strip(), res.strip())
        elif isinstance(_input, list):
            lis1, output = list(_input), []
            for nn in range(3):
                if lis1:
                    dedu = []
                    in1 = [list(row) for row in zip(*lis1)][1]
                    res, outpath = self.get_dsres("\n".join(in1), inpath, self.hira_prompt)
                    res = list(map(lambda line: line.replace("\u3000", " ").strip(), res.split("\n")))
                    res = [line for line in res if "//" in line]
                    lis = []
                    for item in res:
                        i, o = item.split("//")
                        lis.append([i.strip(), o.strip()])
                    for item in lis1:
                        for i, o in lis:
                            if stringsim(item[1], i):
                                if i == o:
                                    output.append(item + [i])
                                else:
                                    output.append(item + [self.align_strings(i, o)])
                                break
                        else:
                            string = ""
                            numlist = []
                            tem = spstring(item[1])
                            for n, (i, o) in enumerate(lis):
                                s1 = spstring(i)
                                if s1 in tem:
                                    numlist.append(n)
                                    string += s1
                            if string == tem:
                                s1, s2 = "", ""
                                for n in numlist:
                                    s1 += lis[n][0]
                                    s2 += lis[n][1]
                                s1, s2 = norstring(s1), norstring(s2)
                                if s1 == s2:
                                    output.append(item + [s1])
                                else:
                                    output.append(item + [self.align_strings(s1, s2)])
                            else:
                                dedu.append(item)
                    if lis1 == dedu:
                        break
                    lis1 = list(dedu)
                    if nn < 2:
                        sleep(1)
                else:
                    break
            if lis1:
                strin = "\n".join([f"[{line[0]}]"+line[1] for line in lis1])
                print(f"处理异常:hira句子结构变动{inpath}\n{strin}")
            return output
        else:
            raise ValueError("无效输入类型")

    def get_trans(self, _input, inpath):
        if isinstance(_input, str):
            res, outpath = self.get_dsres(_input, inpath, self.trans_prompt)
            return res.strip()
        elif isinstance(_input, list):
            lis1, output = list(_input), []
            for nn in range(3):
                if lis1:
                    dedu = []
                    in1 = [list(row) for row in zip(*lis1)][1]
                    res, outpath = self.get_dsres("\n".join(in1), inpath, self.trans_prompt)
                    res = list(map(lambda line: line.replace("\u3000", " ").strip(), res.split("\n")))
                    res = [line for line in res if "//" in line]
                    lis = []
                    for item in res:
                        i, o = item.split("//")
                        lis.append([i.strip(), o.strip()])
                    for item in lis1:
                        for i, o in lis:
                            if stringsim(item[1], i):
                                output.append(item + [o])
                                break
                        else:
                            string = ""
                            numlist = []
                            tem = spstring(item[1])
                            for n, (i, o) in enumerate(lis):
                                s1 = spstring(i)
                                if s1 in tem:
                                    numlist.append(n)
                                    string += s1
                            if string == tem:
                                s = ""
                                for n in numlist:
                                    s += lis[n][1]
                                output.append(item + [s])
                            else:
                                dedu.append(item)
                    if lis1 == dedu:
                        break
                    lis1 = list(dedu)
                    if nn < 2:
                        sleep(1)
                else:
                    break
            if lis1:
                strin = "\n".join([f"[{line[0]}]"+line[1] for line in lis1])
                print(f"处理异常:chin句子结构变动{inpath}\n{strin}")
            return output
        else:
            raise ValueError("无效输出类型")

    def get_roma(self, _input, inpath):
        if isinstance(_input, str):
            res, outpath = self.get_dsres(_input, inpath, self.roma_prompt)
            return res.strip()
        elif isinstance(_input, list):
            lis1, output = list(_input), []
            for nn in range(3):
                if lis1:
                    dedu = []
                    in1 = [list(row) for row in zip(*lis1)][1]
                    res, outpath = self.get_dsres("\n".join(in1), inpath, self.roma_prompt)
                    res = list(map(lambda line: line.replace("\u3000", " ").strip(), res.split("\n")))
                    res = [line for line in res if "//" in line]
                    lis = []
                    for item in res:
                        i, o = item.split("//")
                        lis.append([i.strip(), o.strip()])
                    for item in lis1:
                        for i, o in lis:
                            if stringsim(item[1], i):
                                output.append(item + [o])
                                break
                        else:
                            string = ""
                            numlist = []
                            tem = spstring(item[1])
                            for n, (i, o) in enumerate(lis):
                                s1 = spstring(i)
                                if s1 in tem:
                                    numlist.append(n)
                                    string += s1
                            if string == tem:
                                s = ""
                                for n in numlist:
                                    s += lis[n][1]
                                output.append(item + [s])
                            else:
                                dedu.append(item)
                    if lis1 == dedu:
                        break
                    lis1 = list(dedu)
                    if nn < 2:
                        sleep(1)
                else:
                    break
            if lis1:
                strin = "\n".join([f"[{line[0]}]"+line[1] for line in lis1])
                print(f"处理异常:roma句子结构变动{inpath}\n{strin}")
            return output
        else:
            raise ValueError("无效输出类型")


if __name__ == "__main__":
    ...
