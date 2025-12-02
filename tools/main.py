from os import path, walk, makedirs
import json
import tkinter as tk
from tkinter import filedialog
import sys
from datetime import datetime


class UI:
    def __init__(self, title):
        # 保存配置文件路径
        self.config_file = 'config.json'
        self.title = title
        self.lrc_backup = ""
        self.initial_dir, self.seq_line, self.ds_key = self.load_last_folder()
        if self.initial_dir and not path.exists(self.initial_dir):
            self.initial_dir = "C:\\"
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
            try:
                self.main(file_path)
            except RuntimeError as e:
                print(str(e), file_path)
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
