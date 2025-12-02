import shutil

from tools.main import UI
from tools.lrc import lrc_sort, lrc_split, get_lrc_root, check_jap, movefile, listsort
from tools.file import MusicLrcEditor
from os import path, makedirs, cpu_count
from tools.dsapi import DSAPI
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor


class DSUI(UI):
    def __init__(self):
        UI.__init__(self, "日语音乐歌词注音工具-ds")
        if not path.exists("output"):
            makedirs("output")
        if self.ds_key:
            self.dsapi = DSAPI(self.ds_key)
        else:
            self.save_last_folder("")
            input("ds_key 不能为空")
            raise ValueError("ds_key 不能为空")

    def main(self, in_path):
        mle = MusicLrcEditor(in_path)
        if mle.isreadlrc():
            lrc = mle.read_lyrics()
            if not lrc:
                movefile(in_path, "error")
                return
            lis1, lis2, lis3 = lrc_split(lrc)
            if lis2:
                if lis3:
                    print("\n".join([f"无效行:{in_path}"]+lis3))
            else:
                print(f"非同步歌词:{in_path}")
                movefile(in_path, "other")
                return
            if check_jap(lis2):
                times, texts = zip(*get_lrc_root(lis2))
                times, texts = list(times), list(map(
                    lambda line: line.replace("\u3000", " ").replace("　", " ").strip(), texts))
                flag = 0
                texts = [list(row) for row in zip(*[times, texts])]
                # print(times, texts)
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
                # print(lis)

                lrc_list = lis1
                texts = listsort(texts)
                for ls in texts:
                    tt = f"[{ls[0]}]"
                    for i in ls[2:]:
                        ti = tt+i
                        if ti not in lrc_list:
                            lrc_list.append(ti)
                # print(lrc_list)
                mle.lrc = lrc_list
                out_path = path.splitext(path.join(self.lrc_backup, path.split(in_path)[1]))[0] + ".lrc"
                with open(out_path, 'w+', encoding='utf-8') as f:
                    f.writelines(lrc)
                if mle.write_lyrics():
                    if flag:
                        print(f"处理异常:歌词主体结构多次变动({flag}) {in_path}")
                        dire = "defect"
                    else:
                        print(f"处理完成:{in_path}")
                        dire = "success"
                    movefile(in_path, dire)
            else:
                print(f"不为日语歌词:{in_path}")
                movefile(in_path, "other")
        else:
            print(f"error:读取异常:{in_path}")

    def process_file(self, file_path, i):
        try:
            print(f"开始处理[{i}]：" + file_path)
            self.main(file_path)
        except:
            print(f"处理错误：{file_path}\n{traceback.format_exc()}")

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
