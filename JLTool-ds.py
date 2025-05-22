from tools.main import UI
from tools.lrc import lrc_sort, lrc_split, get_lrc_root, check_jap
from tools.file import MusicLrcEditor
from os import path, makedirs, cpu_count
from tools.dsapi import DSAPI
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor


class DSUI(UI):
    def __init__(self):
        UI.__init__(self, "日语音乐歌词注音工具-ds")
        self.key = ""
        if not path.exists("output"):
            makedirs("output")
        if self.key:
            self.dsapi = DSAPI(self.key)
        else:
            raise ValueError("ds_key 不能为空")

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
                lis4 = lrc_sort(lis2)
                lis5 = get_lrc_root(lis4)
                # print(lis5)
                times, texts = zip(*lis5)
                times, texts = list(times), list(texts)
                lennum = len(times)
                lis = []
                # print(times, texts)
                for item in self.seq:
                    if item == "hira":
                        res = self.dsapi.get_hira(texts)[0]
                        if lennum != len(res):
                            print(f"处理异常， hira 句数不匹配:{in_path}")
                            return
                        lis += [res]
                    elif item == "kanji":
                        lis += [texts]
                    elif item == "roma":
                        res = self.dsapi.get_roma(texts)
                        if lennum != len(res):
                            print(f"处理异常， roma 句数不匹配:{in_path}")
                            return
                        lis += [res]
                    elif item == "chin":
                        res = self.dsapi.get_trans(texts)
                        if lennum != len(res):
                            print(f"处理异常，chin 句数不匹配:{in_path}")
                        lis += [res]
                # print(lis)
                lrc_list = lis1
                for n, ls in enumerate(zip(*lis)):
                    tt = f"[{times[n]}]"
                    for i in ls:
                        ti = tt+i
                        if ti not in lrc_list:
                            lrc_list += [ti]
                # print(lrc_list)
                mle.lrc = lrc_list
                out_path = path.splitext(path.join(self.lrc_backup, path.split(in_path)[1]))[0] + ".lrc"
                with open(out_path, 'w+', encoding='utf-8') as f:
                    f.writelines(lrc)
                if mle.write_lyrics():
                    print(f"处理完成:{in_path}")
            else:
                print(f"不为日语歌词:{in_path}")
        else:
            print(f"error:读取异常:{in_path}")

    def process_file(self, file_path, i):
        try:
            print(f"开始处理[{i}]：" + file_path)
            self.main(file_path)
        except Exception as e:
            print(f"处理错误：{file_path}\n{e}")

    def process(self, _file_list):
        self.lrc_backup = "lyrics/lrc" + datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        if not path.exists(self.lrc_backup):
            makedirs(self.lrc_backup)

        # 设置线程池大小（推荐 CPU 核心数 * 2~4）
        max_workers = min(32, (cpu_count() or 1) * 4)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务到线程池，并传入索引 i
            futures = [
                executor.submit(self.process_file, file_path, i)
                for i, file_path in enumerate(_file_list)
            ]

            # 可选：等待所有任务完成（with 语句会自动等待）
            for future in futures:
                future.result()  # 检查是否有异常
        print("===========================================")


if __name__ == "__main__":
    ds = DSUI()
    ds.start()
