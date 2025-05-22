from os import path, walk, makedirs
import json
import tkinter as tk
from tkinter import filedialog
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor


class UI:
    def __init__(self, title):
        # 保存配置文件路径
        self.config_file = 'config.json'
        self.title = title
        self.lrc_backup = ""
        self.initial_dir, self.seq_line = self.load_last_folder()
        if self.initial_dir and not path.exists(self.initial_dir):
            raise ValueError("last_folder 路径不存在")
        if self.seq_line:
            _list = self.seq_line.split("-")
            for item in _list:
                if item not in ["hira", "kanji", "roma", "chin"]:
                    raise ValueError("seq 值不规范")
            self.seq = _list
        else:
            self.seq = ["chin", "hira", "kanji"]

    def main(self, _path: str):
        pass

    def start(self):
        print(f"============欢迎使用{self.title}============")
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
            file_list = []
            for cm in sys.argv[1:]:
                if path.isdir(cm):
                    file_list += self.dir_to_files(cm)
                else:
                    file_list += [cm]
            self.process(file_list)
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
        root.title(self.title)  # "日语音乐歌词注音工具"

        # 设置窗口大小并锁定
        root.geometry("150x100")
        root.resizable(False, False)  # 锁定窗口大小
        self.center_window(root)  # 居中窗口

        # 标签和合并按钮
        label = tk.Label(root, text="使用前请做好数据备份，本工具不能替代人工检查")
        label.pack(pady=8)

        # 合并按钮
        btn_process = tk.Button(root, text="选择文件夹",
                                command=self.from_folder)
        btn_process.pack(pady=8)
        btn_process2 = tk.Button(root, text="选择文件(可复选)",
                                 command=self.from_file)
        btn_process2.pack(pady=8)

        # 启动GUI主循环
        root.mainloop()

    def load_last_folder(self):
        if path.exists(self.config_file):
            with open(self.config_file, 'r') as file:
                config = json.load(file)
                return config.get('last_folder', ''), config.get('seq', '')
        return '', self.seq

    # 保存当前选择的文件夹路径
    def save_last_folder(self, folder_path):
        config = {'last_folder': folder_path, "seq": self.seq_line}
        with open(self.config_file, 'w', encoding='utf-8') as file:
            json.dump(config, file)

    @staticmethod
    # GUI窗口居中显示
    def center_window(_root, width=300, height=150):
        screen_width = _root.winfo_screenwidth()
        screen_height = _root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        _root.geometry(f'{width}x{height}+{x}+{y}')

    def process_file(self, file_path, i):
        print("-------------------------------------------")
        print(f"开始处理[{i}]：" + file_path)
        self.main(file_path)

    def process(self, _file_list):
        self.lrc_backup = "lyrics/lrc" + datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        if not path.exists(self.lrc_backup):
            makedirs(self.lrc_backup)

        for _i, file_path in enumerate(_file_list):
            print("-------------------------------------------")
            print(f"开始处理[{_i}]：" + file_path)
            self.main(file_path)
        print("===========================================")

    def from_file(self):
        file_paths = filedialog.askopenfilenames(initialdir=self.initial_dir)
        self.save_last_folder(path.split(file_paths[0])[0])

        file_list = []
        for _path in file_paths:
            if path.isdir(_path):
                file_list += self.dir_to_files(_path)
            else:
                file_list += [_path]
        self.process(file_list)

    def from_folder(self):
        folder_path = filedialog.askdirectory(initialdir=self.initial_dir)
        self.save_last_folder(folder_path)
        self.process(self.dir_to_files(folder_path))

    @staticmethod
    def dir_to_files(_dir):
        file_path = []
        for _root, _ds, _fs in walk(_dir):
            for _f in _fs:
                file_path += [path.join(_root, _f)]
        return file_path
