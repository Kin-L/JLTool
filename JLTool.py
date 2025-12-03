from os import path, makedirs
from datetime import datetime
from tools.lrc import (listsort, LyrTrans, lrc_split, check_jap,
                       arrangelines, get_lrc_root, movefile)
from tools.file import MusicLrcEditor
from tools.dsapi import DSAPI


class JLToolMain:
    def __init__(self, seq, logging, ds_key=""):
        self.logging = logging
        self.seq = seq.split("-")  # 默认使用kks版本
        self.kks = LyrTrans()
        self.ds_key = ds_key
        self.lrc_backup = "lyrics/lrc" + datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        if not path.exists(self.lrc_backup):
            makedirs(self.lrc_backup)
        if self.ds_key:
            self.dsapi = DSAPI(ds_key)

    def start(self, in_path):
        """主处理函数，根据版本调用不同实现"""
        if self.ds_key:
            return self.ds_main(in_path)
        else:
            return self.kks_main(in_path)

    def kks_main(self, in_path):
        """KKS版本处理逻辑"""
        mle = MusicLrcEditor(in_path)
        if not mle.isreadlrc():
            self.logging.error(f"读取异常:{in_path}")
            return "error"
        else:
            lrc = mle.read_lyrics()
            if not lrc:
                movefile(in_path, "error")
                return "error"
            prefix, root, invalid = lrc_split(lrc)
            if not root:
                self.logging.info(f"非同步歌词:{in_path}")
                movefile(in_path, "other")
                return "other"
            if not check_jap(root):
                self.logging.info(f"不为日语歌词:{in_path}")
                movefile(in_path, "other")
                return "other"
            else:
                if invalid:
                    self.logging.info("\n".join([f"无效行:{in_path}"] + invalid))
                root, flag = self.lrclines_trans(root)
                mle.lrc = prefix + root
                out_path = path.join(self.lrc_backup, path.splitext(path.split(in_path)[1])[0]) + ".lrc"
                with open(out_path, 'w+', encoding='utf-8') as f:
                    f.writelines(lrc)
                if mle.write_lyrics():
                    if flag:
                        movefile(in_path, "defect")
                        return "defect"
                    else:
                        self.logging.info(f"处理完成:{in_path}")
                        movefile(in_path, "success")
                        return "success"

    def lrclines_trans(self, _in_lines: list):
        times, _ = zip(*_in_lines)
        times = list(dict.fromkeys(times))
        praline = []
        for time in times:
            line = [f"[{time}]"]
            for t, l in _in_lines:
                if time == t:
                    line.append(l)
            praline.append(line)
        res = arrangelines(praline)
        flag = False
        if len(res) != len(praline):
            flag = True
        if "chin" in self.seq:
            if ((not res[0][2]) and res[0][0]) and (res[-1][2] and (not res[-1][0])):
                l0, l1, l2, l3, l4 = [list(row) for row in zip(*res)]
                l0 = l0[:-1]
                l1 = l1[:-1]
                l2 = l2[1:]
                l3 = l3[:-1]
                l4 = l4[:-1]
                res = [list(row) for row in zip(*[l0, l1, l2, l3, l4])]
                self.logging.info("整理滞后翻译行")
        _list = []
        for item in res:
            time, root, chin, hira, roma = item
            for i in self.seq:
                if i == "kanji":
                    if root:
                        _list.append(time + root)
                elif i == "hira":
                    if not hira:
                        hira = self.kks.trans(root)
                    if hira != root:
                        _list.append(time + hira)
                elif i == "chin":
                    if chin:
                        _list.append(time + chin)
                elif i == "roma":
                    if not roma:
                        roma = self.kks.trans(root, "roma")
                    if roma != root:
                        _list.append(time + roma)
        return _list, flag

    def ds_main(self, in_path):
        """DS版本处理逻辑"""
        mle = MusicLrcEditor(in_path)
        if mle.isreadlrc():
            self.logging.error(f"读取异常:{in_path}")
            return "error"
        else:
            lrc = mle.read_lyrics()
            if not lrc:
                movefile(in_path, "error")
                return "error"
            prefix, root, invalid = lrc_split(lrc)
            if not root:
                self.logging.info(f"非同步歌词:{in_path}")
                movefile(in_path, "other")
                return "other"
            elif invalid:
                self.logging.info("\n".join([f"无效行:{in_path}"] + invalid))

            if not check_jap(root):
                self.logging.info(f"不为日语歌词:{in_path}")
                movefile(in_path, "other")
                return "other"
            else:
                times, texts = zip(*get_lrc_root(root))
                times, texts = list(times), list(map(
                    lambda line: line.replace("\u3000", " ").replace("　", " ").strip(), texts))
                flag = 0
                texts = [list(row) for row in zip(*[times, texts])]
                for item in self.seq:
                    if item == "hira":
                        inp = list(texts)
                        texts = self.dsapi.get_hira(texts, in_path)
                        if len(inp) != len(texts):
                            flag += 1
                    elif item == "kanji":
                        texts = [list(row) for row in zip(*texts)]
                        texts += [texts[1]]
                        texts = [list(row) for row in zip(*texts)]
                    elif item == "roma":
                        inp = list(texts)
                        texts = self.dsapi.get_roma(texts, in_path)
                        if len(inp) != len(texts):
                            flag += 1
                    elif item == "chin":
                        inp = list(texts)
                        texts = self.dsapi.get_trans(texts, in_path)
                        if len(inp) != len(texts):
                            flag += 1

                lrc_list = prefix
                texts = listsort(texts)
                for ls in texts:
                    tt = f"[{ls[0]}]"
                    for i in ls[2:]:
                        ti = tt + i
                        if ti not in lrc_list:
                            lrc_list.append(ti)
                mle.lrc = lrc_list
                out_path = path.splitext(path.join(self.lrc_backup, path.split(in_path)[1]))[0] + ".lrc"
                with open(out_path, 'w+', encoding='utf-8') as f:
                    f.writelines(lrc)
                if mle.write_lyrics():
                    if flag:
                        self.logging.info(f"处理异常:歌词主体结构多次变动({flag}) {in_path}")
                        dire = "defect"
                    else:
                        self.logging.info(f"处理完成:{in_path}")
                        dire = "success"
                    movefile(in_path, dire)
                    return dire


if __name__ == "__main__":
    ...
