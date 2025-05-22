from openai import OpenAI
from datetime import datetime


class DSAPI:
    def __init__(self, api_key):
        self.client = OpenAI(
            api_key=api_key,  #
            base_url="https://api.deepseek.com",
        )
        self.hira_prompt = r"""
            我接下来会发给你一些日语歌词，一行为一句，将每句分别转化为平假名, 去除每句首尾多余的字符，用换行符连接每一句后，返回结果
            只需要回答结果，不需要其他内容，务必保持句数一致
            例如："まるで予想外だ\nどこまで続いてるのかな\n" > "まるでよそうがいだ\nどこまでつづいてるのかな\n"
            """
        self.trans_prompt = r"""
            我接下来会发给你一些日语歌词，一行为一句，将每句分别转化为中文, 去除每句首尾多余的字符，用换行符连接每一句后，返回结果
            只需要回答结果，不需要其他内容，务必保持句数一致
            例如："予測できない\n信じられない\n" > "无法预测\n难以置信\n"
            """
        self.roma_prompt = r"""
            我接下来会发给你一些日语歌词，一行为一句，将每句分别转化为罗马音, 去除每句首尾多余的字符，用换行符连接每一句后，返回结果
            只需要回答结果，不需要其他内容，务必保持句数一致
            例如："予測できない\n信じられない\n" > "yo so ku de ki na i\nshi n ji ra re na i\n"
            """

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

    def get_dsres(self, _user_prompt, _system_prompt):
        messages = [{"role": "system", "content": _system_prompt},
                    {"role": "user", "content": _user_prompt}]

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages
        )
        res = response.choices[0].message.content
        output = response.model_dump()
        outpath = "output/"+datetime.now().strftime("%Y-%m-%d %H-%M-%S")+".txt"
        with open(outpath, 'a+', encoding='utf-8') as file:
            file.write(str(output))
        return res

    def get_hira(self, _input):
        if isinstance(_input, str):
            _user_prompt = _input
            out = self.get_dsres(_user_prompt, self.hira_prompt).strip("\n")
            return [self.align_strings(_input, out), out]
        elif isinstance(_input, list):
            _user_prompt = ""
            for _item in _input:
                _user_prompt += _item + "\n"
            out = self.get_dsres(_user_prompt, self.hira_prompt).replace("\n\n", "\n").strip("\n").split("\n")
            out_list = []
            for _o, _h in zip(_input, out):
                out_list += [self.align_strings(_o, _h.strip(" "))]
            return [out_list, out]
        else:
            raise ValueError("无效输入类型")

    def get_trans(self, _input):
        if isinstance(_input, str):
            return self.get_dsres(_input, self.trans_prompt).strip("\n")
        elif isinstance(_input, list):
            _user_prompt = ""
            for _item in _input:
                _user_prompt += _item + "\n"
            out_list = []
            out = self.get_dsres(_user_prompt, self.trans_prompt).replace("\n\n", "\n").strip("\n").split("\n")
            for _item in out:
                out_list += [_item]
            return out_list
        else:
            raise ValueError("无效输出类型")

    def get_roma(self, _input):
        if isinstance(_input, str):
            return self.get_dsres(_input, self.roma_prompt).strip("\n")
        elif isinstance(_input, list):
            _user_prompt = ""
            for _item in _input:
                _user_prompt += _item + "\n"
            out_list = []
            out = self.get_dsres(_user_prompt, self.trans_prompt).replace("\n\n", "\n").strip("\n").split("\n")
            for _item in out:
                out_list += [_item]
            return out_list
        else:
            raise ValueError("无效输出类型")


if __name__ == "__main__":

    ds = DSAPI("sk-c5b3f20a65724e869318fc4acc46981d")
    print(ds.get_hira("黄昏の様に深く"))
    print(ds.get_hira(["一人きりではとても", "超えられない夜には"]))
