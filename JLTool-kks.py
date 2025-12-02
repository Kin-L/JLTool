import re
import shutil
from os import path, makedirs
from tools.main import UI
from tools.lrc import LyrTrans, lrc_split, check_jap, choose_root, arrangelines, checktrans, movefile
from tools.file import MusicLrcEditor
_pat3 = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')


class KKSUI(UI):
    def __init__(self):
        UI.__init__(self, "日语音乐歌词注音工具-kks")
        self.kks = LyrTrans()

    def main(self, in_path):
        mle = MusicLrcEditor(in_path)
        if mle.isreadlrc():
            lrc = mle.read_lyrics()
            if not lrc:
                movefile(in_path, "error")
                return
            lis1, lis2, lis3 = lrc_split(lrc)
            if not lis2:

                print(f"非同步歌词:{in_path}")
                movefile(in_path, "other")
                return
            if check_jap(lis2):
                if lis3:
                    print("\n".join([f"无效行:{in_path}"] + lis3))
                lis2, flag = self.lrclines_trans(lis2)
                mle.lrc = lis1 + lis2
                out_path = path.splitext(path.join(self.lrc_backup, path.split(in_path)[1]))[0] + ".lrc"
                with open(out_path, 'w+', encoding='utf-8') as f:
                    f.writelines(lrc)
                if mle.write_lyrics():
                    if flag:
                        movefile(in_path, "defect")
                    else:
                        print(f"处理完成:{in_path}")
                        movefile(in_path, "success")
            else:
                print(f"不为日语歌词:{in_path}")
                movefile(in_path, "other")
        else:
            print(f"error:读取异常:{in_path}")

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
        # print(praline)
        res = arrangelines(praline)
        flag = False
        if len(res) != len(praline):
            flag = True
        if "chin" in self.seq:
            # print(res)
            # print()
            if ((not res[0][2]) and res[0][0]) and (res[-1][2] and (not res[-1][0])):
                l0, l1, l2, l3, l4 = [list(row) for row in zip(*res)]
                l0 = l0[:-1]
                l1 = l1[:-1]
                l2 = l2[1:]
                l3 = l3[:-1]
                l4 = l4[:-1]
                res = [list(row) for row in zip(*[l0, l1, l2, l3, l4])]
                print("整理滞后翻译行")
        _list = []
        for item in res:
            time, root, chin, hira, roma = item
            for i in self.seq:
                if i == "kanji":
                    if root:
                        _list.append(time+root)
                elif i == "hira":
                    if not hira:
                        hira = self.kks.trans(root)
                    if hira != root:
                        _list.append(time+hira)
                elif i == "chin":
                    if chin:
                        _list.append(time+chin)
                elif i == "roma":
                    if not roma:
                        roma = self.kks.trans(root, "roma")
                    if roma != root:
                        _list.append(time+roma)
        return _list, flag


if __name__ == "__main__":
    kks = KKSUI()
    kks.start()
