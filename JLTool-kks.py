import re
from os import path
from tools.main import UI
from tools.lrc import LyrTrans, lrc_split, check_jap, choose_root
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
                return 1
            lis1, lis2, lis3 = lrc_split(lrc)
            if lis3:
                print("\n".join([f"无效行:{in_path}"]+lis3))
            if check_jap(lis2):
                mle.lrc = lis1 + self.lrclines_trans(lis2)
                out_path = path.splitext(path.join(self.lrc_backup, path.split(in_path)[1]))[0] + ".lrc"
                with open(out_path, 'w+', encoding='utf-8') as f:
                    f.writelines(lrc)
                if mle.write_lyrics():
                    print(f"处理完成:{in_path}")
            else:
                print(f"不为日语歌词:{in_path}")
        else:
            print(f"error:读取异常:{in_path}")

    def lrclines_trans(self, _in_lines: list) -> list:
        times, _ = zip(*_in_lines)
        times = list(dict.fromkeys(times))
        out_list = []
        for time in times:
            nl: list = []
            for t, l in _in_lines:
                if time == t and [t, l] not in nl:
                    nl += [l]
            root_line = choose_root(nl)
            nl.remove(root_line)
            hira, roma, chin = "", "", ""
            for i in nl:
                if bool(re.search(_pat3, i)):
                    hira = i
                else:
                    if i.isascii():
                        roma = i
                    else:
                        chin = i
            time_str = f"[{time}]"
            for item in self.seq:
                if item == "kanji":
                    out_list += [time_str+root_line]
                elif item == "hira":
                    if not hira:
                        hira = self.kks.trans(root_line)
                    if hira != root_line:
                        out_list += [time_str+hira]
                elif item == "chin":
                    if chin:
                        out_list += [time_str+chin]

                elif item == "roma":
                    if not roma:
                        roma = self.kks.trans(root_line, "roma")
                    out_list += [time_str+roma]
        return out_list


if __name__ == "__main__":
    kks = KKSUI()
    kks.start()
