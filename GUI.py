import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
from datetime import datetime
from JLTool import JLToolMain
import logging
import threading
import queue
import traceback

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


class TextHandler(logging.Handler):
    """自定义logging handler，将日志输出到tkinter文本框"""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.queue = queue.Queue()

    def emit(self, record):
        msg = self.format(record)
        self.queue.put(msg)

    def flush_queue(self):
        """处理队列中的所有消息"""
        while not self.queue.empty():
            try:
                msg = self.queue.get_nowait()
                self.text_widget.insert(tk.END, msg + '\n')
                self.text_widget.see(tk.END)
            except queue.Empty:
                break


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
        self.other_count = 0
        self.error_count = 0

        # 日志相关
        self.log_queue = queue.Queue()
        self.logging_initialized = False
        self.log_file_handler = None
        self.current_log_file = None

        self.jlmain = None
        self.jlmain: JLToolMain
        self.create_widgets()
        self.load_config_to_gui()
        self.setup_logging()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # 启动日志队列处理
        self.after(100, self.process_log_queue)

    def setup_logging(self):
        """设置日志系统"""
        if not self.logging_initialized:
            # 创建logs目录
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # 创建日志文件名（带时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_log_file = os.path.join(log_dir, f"{timestamp}.log")

            # 配置root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)

            # 移除所有现有handler
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)

            # 创建文本处理器（用于GUI显示）
            self.text_handler = TextHandler(self.log_text)
            self.text_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s',
                                                datefmt='%H:%M:%S'))
            root_logger.addHandler(self.text_handler)

            # 创建文件处理器（用于保存到文件）
            self.log_file_handler = logging.FileHandler(self.current_log_file, encoding='utf-8')
            self.log_file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            root_logger.addHandler(self.log_file_handler)

            self.logging_initialized = True

            # 记录启动日志
            logging.info("=" * 50)
            logging.info("日语音乐歌词注音工具启动")
            logging.info(f"日志文件: {self.current_log_file}")
            logging.info("=" * 50)

    def process_log_queue(self):
        """处理日志队列中的消息"""
        if hasattr(self, 'text_handler'):
            self.text_handler.flush_queue()
        self.after(100, self.process_log_queue)

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
            logging.error(f"加载配置文件失败: {e}")
        return default_config

    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logging.info("配置文件已保存")
        except Exception as e:
            logging.error(f"保存配置文件失败: {e}")

    def create_widgets(self):
        """创建GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 左侧配置面板
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side="left", fill="both", expand=True)

        # 1. 序列选择区域
        seq_frame = ttk.LabelFrame(left_panel, text="序列配置")
        seq_frame.pack(fill="x", padx=5, pady=5)

        self.seq_combos = []
        for i in range(4):
            combo = ttk.Combobox(seq_frame, values=SEQ_OPTIONS, state="readonly", width=15)
            combo.grid(row=0, column=i, padx=5, pady=5)
            self.seq_combos.append(combo)

        # 2. Deepseek配置区域
        ds_frame = ttk.LabelFrame(left_panel, text="Deepseek翻译配置")
        ds_frame.pack(fill="x", padx=5, pady=5)

        self.ds_check = ttk.Checkbutton(ds_frame, text="启用Deepseek翻译")
        self.ds_check.grid(row=0, column=0, padx=5, pady=5)
        self.ds_check.bind("<ButtonRelease-1>", self.toggle_ds_key)

        ttk.Label(ds_frame, text="API密钥:").grid(row=0, column=1, padx=5, pady=5)
        self.ds_key_entry = ttk.Entry(ds_frame, width=40)
        self.ds_key_entry.grid(row=0, column=2, padx=5, pady=5, columnspan=2)

        # 3. 路径管理区域
        path_frame = ttk.LabelFrame(left_panel, text="文件/文件夹路径")
        path_frame.pack(fill="both", expand=True, padx=5, pady=5)

        path_buttons = ttk.Frame(path_frame)
        path_buttons.pack(fill="x", padx=5, pady=5)

        ttk.Button(path_buttons, text="添加文件", command=self.add_files).pack(side="left", padx=5)
        ttk.Button(path_buttons, text="添加文件夹", command=self.add_folders).pack(side="left", padx=5)
        ttk.Button(path_buttons, text="清空路径", command=self.clear_paths).pack(side="left", padx=5)
        ttk.Button(path_buttons, text="打开日志目录", command=self.open_log_dir).pack(side="right", padx=5)

        self.path_text = scrolledtext.ScrolledText(path_frame, height=8)
        self.path_text.pack(fill="both", expand=True, padx=5, pady=5)

        # 4. 统计信息区域
        stats_frame = ttk.LabelFrame(left_panel, text="处理统计")
        stats_frame.pack(fill="x", padx=5, pady=5)

        self.stats_labels = {}
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(padx=5, pady=5)

        stats_data = [
            ("总文件数:", "total", "0"),
            ("已处理:", "processed", "0"),
            ("成功:", "success", "0"),
            ("缺陷:", "defect", "0"),
            ("其他:", "other", "0"),
            ("错误:", "error", "0"),
            ("成功率:", "rate", "0%")
        ]

        for i, (label, key, default) in enumerate(stats_data):
            row = i // 2
            col = (i % 2) * 2

            ttk.Label(stats_grid, text=label).grid(row=row, column=col, padx=5, pady=2, sticky="w")
            value_label = ttk.Label(stats_grid, text=default, font=("Arial", 10, "bold"))
            value_label.grid(row=row, column=col + 1, padx=5, pady=2, sticky="w")
            self.stats_labels[key] = value_label

        # 5. 控制区域
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill="x", padx=5, pady=5)

        self.start_btn = ttk.Button(control_frame, text="开始处理", command=self.start_process)
        self.start_btn.pack(side="left", padx=5)

        self.clear_log_btn = ttk.Button(control_frame, text="清空日志", command=self.clear_log)
        self.clear_log_btn.pack(side="left", padx=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame, variable=self.progress_var, length=200)
        self.progress_bar.pack(side="left", padx=5, fill="x", expand=True)

        self.progress_label = ttk.Label(control_frame, text="0/0 文件")
        self.progress_label.pack(side="left", padx=5)

        # 右侧日志面板
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side="right", fill="both", expand=True)

        # 日志控制区域
        log_control_frame = ttk.Frame(right_panel)
        log_control_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(log_control_frame, text="日志级别:").pack(side="left", padx=5)
        self.log_level_combo = ttk.Combobox(log_control_frame,
                                            values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                            state="readonly", width=10)
        self.log_level_combo.pack(side="left", padx=5)
        self.log_level_combo.set("INFO")
        self.log_level_combo.bind("<<ComboboxSelected>>", self.change_log_level)

        # 日志区域
        log_frame = ttk.LabelFrame(right_panel, text="处理日志")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=25, width=60)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # 状态栏
        self.status_bar = ttk.Label(self, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

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
            self.ds_check.invoke()
        else:
            self.ds_check.state([])
            self.ds_key_entry.config(state="disabled")
            self.ds_check.invoke()
            self.ds_check.invoke()

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
                logging.info(f"添加了 {len(new_paths)} 个文件")

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
                logging.info(f"添加文件夹: {folder}")

    def clear_paths(self):
        """清空路径文本框"""
        self.path_text.delete("1.0", tk.END)
        logging.info("已清空文件路径列表")

    def clear_log(self):
        """清空日志文本框"""
        self.log_text.delete("1.0", tk.END)
        logging.info("已清空日志显示")

    def open_log_dir(self):
        """打开日志目录"""
        log_dir = "logs"
        if os.path.exists(log_dir):
            os.startfile(log_dir)
        else:
            logging.warning("日志目录不存在")

    def change_log_level(self, event=None):
        """更改日志级别"""
        level = self.log_level_combo.get()
        logging.getLogger().setLevel(getattr(logging, level))
        logging.info(f"日志级别已更改为: {level}")

    def update_stats(self):
        """更新统计信息"""
        self.stats_labels["total"].config(text=str(self.total_files))
        self.stats_labels["processed"].config(text=str(self.processed_files))
        self.stats_labels["success"].config(text=str(self.success_count))
        self.stats_labels["defect"].config(text=str(self.fail_count))
        self.stats_labels["other"].config(text=str(self.other_count))
        self.stats_labels["error"].config(text=str(self.error_count))

        # 计算成功率
        if self.processed_files > 0:
            success_rate = (self.success_count / self.processed_files) * 100
            self.stats_labels["rate"].config(text=f"{success_rate:.1f}%")
        else:
            self.stats_labels["rate"].config(text="0%")

        # 更新进度条
        if self.total_files > 0:
            progress = (self.processed_files / self.total_files) * 100
            self.progress_var.set(progress)
            self.progress_label.config(text=f"{self.processed_files}/{self.total_files} 文件")

            # 更新状态栏
            if self.processed_files < self.total_files:
                self.status_bar.config(text=f"处理中... {self.processed_files}/{self.total_files}")
            else:
                self.status_bar.config(
                    text=f"处理完成！成功: {self.success_count}, 缺陷: {self.fail_count}, 错误: {self.error_count}")

    def collect_all_files(self, paths):
        """从路径列表中收集所有有效文件"""
        valid_files = []
        for path_str in paths:
            path_str = path_str.strip()
            if not path_str:
                continue
            if not os.path.exists(path_str):
                logging.warning(f"路径不存在: {path_str}")
                continue
            if os.path.isfile(path_str):
                if path_str.lower().endswith((".mp3", ".flac", ".opus", ".txt", ".lrc")):
                    valid_files.append(path_str)
                else:
                    logging.warning(f"不支持的文件格式: {path_str}")
            elif os.path.isdir(path_str):
                for root, _, files in os.walk(path_str):
                    for file in files:
                        if file.lower().endswith((".mp3", ".flac", ".opus", ".txt", ".lrc")):
                            valid_files.append(os.path.join(root, file))
        return valid_files

    def process_single_file(self, file_path, index):
        """处理单个文件"""
        try:
            logging.info(f"开始处理文件 [{index + 1}/{self.total_files}]: {os.path.basename(file_path)}")
            result = self.jlmain.start(file_path)

            if result == "success":
                self.success_count += 1
            elif result == "defect":
                self.fail_count += 1
            elif result == "other":
                self.other_count += 1
            else:
                self.error_count += 1

        except Exception as e:
            errinfo = str(e) + "\n" + traceback.format_exc()

            self.error_count += 1
            logging.error(f"处理异常: {os.path.basename(file_path)} - {errinfo}")

        self.processed_files += 1
        self.update_stats()

    def start_process(self):
        """开始处理任务"""
        self.start_btn.config(state="disabled")
        self.clear_log_btn.config(state="disabled")

        # 保存当前配置
        self.save_current_config()

        # 获取并验证路径
        paths = self.path_text.get("1.0", tk.END).splitlines()
        if not paths or all(not p.strip() for p in paths):
            messagebox.showwarning("警告", "请添加文件/文件夹路径")
            self.start_btn.config(state="normal")
            self.clear_log_btn.config(state="normal")
            return

        # 收集有效文件
        valid_files = self.collect_all_files(paths)
        if not valid_files:
            messagebox.showwarning("警告", "没有找到有效文件")
            self.start_btn.config(state="normal")
            self.clear_log_btn.config(state="normal")
            return

        ds_key = ""
        # 验证Deepseek配置
        if "selected" in self.ds_check.state():
            ds_key = self.ds_key_entry.get().strip()
            if not ds_key:
                messagebox.showwarning("警告", "请填写Deepseek API密钥")
                self.start_btn.config(state="normal")
                self.clear_log_btn.config(state="normal")
                return

        # 初始化工具
        self.jlmain = JLToolMain(self.config["seq"], logging, ds_key)

        # 初始化任务状态
        self.total_files = len(valid_files)
        self.processed_files = 0
        self.success_count = 0
        self.fail_count = 0
        self.other_count = 0
        self.error_count = 0

        self.update_stats()
        logging.info("=" * 50)
        logging.info(f"开始批量处理 {self.total_files} 个文件")
        logging.info(f"序列配置: {self.config['seq']}")
        if ds_key:
            logging.info("使用Deepseek翻译")
        logging.info("=" * 50)

        # 使用线程处理文件
        def process_in_thread():
            for i, file_path in enumerate(valid_files):
                self.process_single_file(file_path, i)

            # 处理完成
            logging.info("=" * 50)
            logging.info(f"批量处理完成!")
            logging.info(f"总计: {self.total_files} 个文件")
            logging.info(
                f"成功: {self.success_count}, 缺陷: {self.fail_count}, 其他: {self.other_count}, 错误: {self.error_count}")

            # 在主线程中更新UI
            self.after(0, self.on_process_complete)

        # 启动处理线程
        thread = threading.Thread(target=process_in_thread, daemon=True)
        thread.start()

    def on_process_complete(self):
        """处理完成后的回调"""
        self.start_btn.config(state="normal")
        self.clear_log_btn.config(state="normal")

        # 显示完成消息
        messagebox.showinfo("处理完成",
                            f"处理完成!\n\n"
                            f"总计: {self.total_files} 个文件\n"
                            f"成功: {self.success_count}\n"
                            f"缺陷: {self.fail_count}\n"
                            f"其他: {self.other_count}\n"
                            f"错误: {self.error_count}")

        # 记录到日志文件
        logging.info(f"处理统计已保存到日志文件: {self.current_log_file}")

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

        logging.info("配置已保存")

    def on_close(self):
        """关闭窗口时保存配置"""
        self.save_current_config()
        self.save_config()
        logging.info("应用程序关闭")
        self.destroy()


if __name__ == "__main__":
    app = ConfigEditor()
    app.geometry("1110x700")
    app.mainloop()