import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
from pathlib import Path
import threading
import queue
from datetime import datetime
import traceback
from JLTool import JLToolMain

# 配置项映射关系
SEQ_OPTIONS = [
    "禁用",
    "中文翻译",
    "日语/原文",
    "假名注音",
    "罗马音注音"
]
SEQ_MAP = {
    "中文翻译": "chin",
    "日语/原文": "kanji",
    "假名注音": "hira",
    "罗马音注音": "roma",
    "禁用": ""
}


class ConfigEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("日语音乐歌词注音工具")
        self.config_path = "config.json"
        self.config = self.load_config()
        self.total_files = 0
        self.processed_files = 0
        self.success_count = 0
        self.fail_count = 0
        self.error_count = 0

        self.jlmain: JLToolMain = None
        self.create_widgets()
        self.load_config_to_gui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_config(self):
        """加载配置文件"""
        default_config = {
            "seq": "chin-hira-kanji",
            "ds_key": "",
            "last_folder": ""
        }
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return {**default_config, **json.load(f)}
        except Exception as e:
            self.log(f"配置文件加载失败: {str(e)}")
        return default_config

    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"配置文件保存失败: {str(e)}")

    def create_widgets(self):
        """创建GUI组件"""
        # 1. 序列选择区域
        seq_frame = ttk.LabelFrame(self, text="序列配置(seq)")
        seq_frame.pack(fill="x", padx=10, pady=5)

        self.seq_combos = []
        for i in range(4):
            combo = ttk.Combobox(seq_frame, values=SEQ_OPTIONS, state="readonly", width=15)
            combo.grid(row=0, column=i, padx=5, pady=5)
            self.seq_combos.append(combo)

        # 2. Deepseek配置区域
        ds_frame = ttk.LabelFrame(self, text="Deepseek翻译配置")
        ds_frame.pack(fill="x", padx=10, pady=5)

        self.ds_check = ttk.Checkbutton(ds_frame, text="启用Deepseek翻译")
        self.ds_check.grid(row=0, column=0, padx=5, pady=5)
        self.ds_check.bind("<ButtonRelease-1>", self.toggle_ds_key)

        ttk.Label(ds_frame, text="API密钥:").grid(row=0, column=1, padx=5, pady=5)
        self.ds_key_entry = ttk.Entry(ds_frame, width=50)
        self.ds_key_entry.grid(row=0, column=2, padx=5, pady=5)


        # 3. 路径管理区域
        path_frame = ttk.LabelFrame(self, text="文件/文件夹路径")
        path_frame.pack(fill="both", expand=True, padx=10, pady=5)

        path_buttons = ttk.Frame(path_frame)
        path_buttons.pack(fill="x", padx=5, pady=5)

        ttk.Button(path_buttons, text="添加文件", command=self.add_files).pack(side="left", padx=5)
        ttk.Button(path_buttons, text="添加文件夹", command=self.add_folders).pack(side="left", padx=5)
        ttk.Button(path_buttons, text="清空路径", command=self.clear_paths).pack(side="left", padx=5)

        self.path_text = scrolledtext.ScrolledText(path_frame, height=6)
        self.path_text.pack(fill="both", expand=True, padx=5, pady=5)

        # 4. 控制区域
        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", padx=10, pady=5)

        self.start_btn = ttk.Button(control_frame, text="开始处理", command=self.start_process)
        self.start_btn.pack(side="left", padx=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame, variable=self.progress_var, length=300)
        self.progress_bar.pack(side="left", padx=5, fill="x", expand=True)

        self.progress_label = ttk.Label(control_frame, text="0/0 文件")
        self.progress_label.pack(side="left", padx=5)

        # 5. 日志区域
        log_frame = ttk.LabelFrame(self, text="处理日志")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    def load_config_to_gui(self):
        """将配置加载到GUI组件"""
        # 加载序列配置
        seq_parts = self.config["seq"].split("-") if self.config["seq"] else []
        for i, combo in enumerate(self.seq_combos):
            if i < len(seq_parts):
                reverse_map = {v: k for k, v in SEQ_MAP.items()}
                combo.set(reverse_map.get(seq_parts[i], "禁用"))
            else:
                combo.set("禁用")

        # 加载Deepseek配置
        if self.config.get("ds_key"):
            self.ds_check.state(['selected'])
            self.ds_key_entry.insert(0, self.config.get("ds_key", ""))
        else:
            self.ds_check.state([])
            self.ds_key_entry.config(state="disabled")

    def toggle_ds_key(self, event=None):
        """根据复选框状态切换API密钥输入框状态"""
        if "selected" in self.ds_check.state():
            self.ds_key_entry.config(state="disabled")
        else:
            self.ds_key_entry.config(state="normal")

    def add_files(self):
        """添加文件路径"""
        initial_dir = self.config.get("last_folder") or os.path.expanduser("~")
        files = filedialog.askopenfilenames(
            initialdir=initial_dir,
            filetypes=[("支持的文件", "*.mp3 *.flac *.opus *.txt *.lrc"), ("所有文件", "*.*")]
        )
        if files:
            self.config["last_folder"] = os.path.dirname(files[0])
            current_text = self.path_text.get("1.0", tk.END).strip()
            new_paths = [os.path.abspath(f) for f in files if f not in current_text]
            if new_paths:
                self.path_text.insert(tk.END, "\n".join(new_paths) + "\n")

    def add_folders(self):
        """添加文件夹路径"""
        initial_dir = self.config.get("last_folder") or os.path.expanduser("~")
        folder = filedialog.askdirectory(initialdir=initial_dir)
        if folder:
            self.config["last_folder"] = folder
            folder = os.path.abspath(folder)
            current_text = self.path_text.get("1.0", tk.END)
            if folder not in current_text:
                self.path_text.insert(tk.END, folder + "\n")

    def clear_paths(self):
        """清空路径文本框"""
        self.path_text.delete("1.0", tk.END)

    def log(self, message):
        # return
        """添加日志信息"""
        # self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        # self.log_text.config(state="disabled")

    def collect_all_files(self, paths):
        """从路径列表中收集所有有效文件"""
        valid_files = []
        for path_str in paths:
            path_str = path_str.strip()
            if not path_str:
                continue
            if not os.path.exists(path_str):
                self.log(f"路径无效: {path_str}")
                continue
            if os.path.isfile(path_str):
                if path_str.lower().endswith((".mp3", ".flac", ".opus", ".txt", ".lrc")):
                    valid_files.append(path_str)
                else:
                    self.log(f"不支持的文件类型: {path_str}")
            elif os.path.isdir(path_str):
                for root, _, files in os.walk(path_str):
                    for file in files:
                        if file.lower().endswith((".mp3", ".flac", ".opus", ".txt", ".lrc")):
                            valid_files.append(os.path.join(root, file))
        return valid_files

    def update_progress(self):
        """更新进度条"""
        if self.total_files > 0:
            progress = (self.processed_files / self.total_files) * 100
            self.progress_var.set(progress)
            self.progress_label.config(text=f"{self.processed_files}/{self.total_files} 文件")
        if self.processed_files == self.total_files:
            self.log(f"\n处理完成 - 成功: {self.success_count}, 缺陷: {self.fail_count}, 错误: {self.error_count}")
            self.start_btn.config(state="normal")

    def process_file(self, file_path):
        """处理单个文件（实际处理逻辑需替换为原有核心代码）"""
        try:
            # 这里只是示例，实际应替换为原有main()方法中的处理逻辑
            self.log(f"处理文件: {file_path}")
            self.jlmain.start(file_path)
            return "success"
        except Exception as e:
            self.log(f"处理错误 {file_path}: {str(e)}")
            return "error"

    def process_worker(self, file_path):
        result = self.process_file(file_path)

        if result == "success":
            self.success_count += 1
        elif result == "defect":
            self.fail_count += 1
        else:
            self.error_count += 1

        self.processed_files += 1
        self.update_progress()

    def start_process(self):
        print("开始处理任务")
        """开始处理任务"""
        # 保存当前配置
        self.save_current_config()

        # 获取并验证路径
        paths = self.path_text.get("1.0", tk.END).splitlines()
        if not paths or all(not p.strip() for p in paths):
            messagebox.showwarning("警告", "请添加文件/文件夹路径")
            return

        # 收集有效文件
        self.log("开始收集有效文件...")
        valid_files = self.collect_all_files(paths)
        if not valid_files:
            messagebox.showwarning("警告", "没有找到有效文件")
            return
        ds_key = ""
        # 验证Deepseek配置
        if "selected" in self.ds_check.state():
            ds_key = self.ds_key_entry.get().strip()
            if not ds_key:
                messagebox.showwarning("警告", "请填写Deepseek API密钥")
                return
        self.jlmain = JLToolMain(self.config["seq"], ds_key)
        # 初始化任务状态
        self.total_files = len(valid_files)
        self.processed_files = 0
        self.success_count = 0
        self.fail_count = 0
        self.error_count = 0
        self.progress_var.set(0)
        self.progress_label.config(text=f"0/{self.total_files} 文件")
        self.start_btn.config(state="disabled")

        # 启动工作线程（使用原有代码中的线程池逻辑）
        self.log(f"开始处理 {self.total_files} 个文件...")
        from concurrent.futures import ThreadPoolExecutor
        from os import cpu_count

        max_workers = min(32, (cpu_count() or 1) * 4)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:

            # 提交所有任务到线程池，并传入索引 i
            futures = [
                executor.submit(self.process_worker, file_path)
                for file_path in valid_files
            ]

            # 可选：等待所有任务完成（with 语句会自动等待）
            for future in futures:
                future.result()  # 检查是否有异常

        # 等待所有任务完成
        self.update_progress()

    def save_current_config(self):
        """保存当前GUI中的配置到内存"""
        # 保存序列配置
        seq_parts = []
        for combo in self.seq_combos:
            val = SEQ_MAP.get(combo.get(), "")
            if val:
                seq_parts.append(val)
        self.config["seq"] = "-".join(seq_parts)

        # 保存Deepseek配置
        self.config["ds_key"] = self.ds_key_entry.get().strip() if "selected" in self.ds_check.state() else ""

    def on_close(self):
        """关闭窗口时保存配置"""
        self.save_current_config()
        self.save_config()
        self.destroy()


if __name__ == "__main__":
    app = ConfigEditor()
    app.geometry("800x600")
    app.mainloop()