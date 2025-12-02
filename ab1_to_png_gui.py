#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

# 导入核心处理函数
from ab1_to_png import parse_ab1_traces, plot_chromatogram, process_single_file

class Ab1ToPngGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ab1 转 PNG 批量工具")
        self.root.geometry("700x600")
        
        # 变量
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar(value="png_output")
        self.dpi = tk.IntVar(value=200)
        self.is_processing = False
        
        self.setup_ui()
        
    def setup_ui(self):
        # 主框架 - 使用 pack 布局更可靠
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="ab1 转 PNG 批量转换工具", 
                               font=("Arial", 18, "bold"))
        title_label.pack(pady=(0, 25))
        
        # 输入文件/目录选择框架
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=8)
        ttk.Label(input_frame, text="输入文件/目录:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))
        input_entry = ttk.Entry(input_frame, textvariable=self.input_path)
        input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(input_frame, text="浏览...", command=self.select_input).pack(side=tk.LEFT, padx=5)
        
        # 输出目录选择框架
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=8)
        ttk.Label(output_frame, text="输出目录:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))
        output_entry = ttk.Entry(output_frame, textvariable=self.output_path)
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(output_frame, text="浏览...", command=self.select_output).pack(side=tk.LEFT, padx=5)
        
        # DPI 设置框架
        dpi_frame = ttk.Frame(main_frame)
        dpi_frame.pack(fill=tk.X, pady=10)
        ttk.Label(dpi_frame, text="DPI 分辨率:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 5))
        dpi_spinbox = ttk.Spinbox(dpi_frame, from_=100, to=600, textvariable=self.dpi, width=12)
        dpi_spinbox.pack(side=tk.LEFT, padx=5)
        ttk.Label(dpi_frame, text="(推荐: 200-300)", foreground="gray").pack(side=tk.LEFT, padx=5)
        
        # 分隔线
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        
        # 开始转换按钮
        self.convert_button = ttk.Button(main_frame, text="开始转换", 
                                        command=self.start_conversion)
        self.convert_button.pack(pady=15)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', length=300)
        self.progress.pack(fill=tk.X, pady=8, padx=20)
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="就绪", foreground="green", font=("Arial", 10))
        self.status_label.pack(pady=5)
        
        # 日志输出区域
        log_frame = ttk.LabelFrame(main_frame, text="转换日志", padding="8")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_text = ScrolledText(log_frame, height=12, wrap=tk.WORD, font=("Monaco", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 添加欢迎信息
        self.log("欢迎使用 ab1 转 PNG 批量转换工具！")
        self.log("请选择输入文件或目录，然后点击「开始转换」按钮。")
        
    def log(self, message):
        """在日志区域添加消息"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
        
    def select_input(self):
        """选择输入文件或目录"""
        # 先尝试选择目录
        path = filedialog.askdirectory(title="选择包含 ab1 文件的目录")
        if not path:
            # 如果取消，尝试选择单个文件
            path = filedialog.askopenfilename(
                title="选择 ab1 文件",
                filetypes=[("AB1 files", "*.ab1 *.abi"), ("All files", "*.*")]
            )
        
        if path:
            self.input_path.set(path)
            self.log(f"已选择输入: {path}")
    
    def select_output(self):
        """选择输出目录"""
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_path.set(path)
            self.log(f"已选择输出目录: {path}")
    
    def start_conversion(self):
        """开始转换（在新线程中运行）"""
        if self.is_processing:
            messagebox.showwarning("警告", "转换正在进行中，请稍候...")
            return
        
        input_path = self.input_path.get().strip()
        output_path = self.output_path.get().strip()
        
        if not input_path:
            messagebox.showerror("错误", "请选择输入文件或目录！")
            return
        
        if not os.path.exists(input_path):
            messagebox.showerror("错误", f"输入路径不存在: {input_path}")
            return
        
        if not output_path:
            messagebox.showerror("错误", "请指定输出目录！")
            return
        
        # 在新线程中运行转换，避免界面冻结
        thread = threading.Thread(target=self.convert_files, args=(input_path, output_path))
        thread.daemon = True
        thread.start()
    
    def convert_files(self, input_path, output_path):
        """执行转换"""
        self.is_processing = True
        self.convert_button.config(state=tk.DISABLED)
        self.progress.start()
        self.status_label.config(text="转换中...", foreground="blue")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        try:
            input_path_obj = Path(input_path)
            dpi = self.dpi.get()
            
            if input_path_obj.is_file():
                # 单个文件
                self.log(f"开始转换单个文件: {input_path}")
                success = process_single_file(input_path, output_path, dpi=dpi, log_callback=self.log)
                if success:
                    self.log(f"✓ 转换成功！")
                    self.status_label.config(text="转换完成！", foreground="green")
                else:
                    self.log(f"✗ 转换失败")
                    self.status_label.config(text="转换失败", foreground="red")
                    
            elif input_path_obj.is_dir():
                # 批量转换
                ab1_files = []
                for root, dirs, files in os.walk(input_path):
                    for name in files:
                        if name.lower().endswith((".ab1", ".abi")):
                            fpath = Path(root) / name
                            ab1_files.append(fpath)
                
                if not ab1_files:
                    self.log(f"在 {input_path} 中未找到 .ab1 或 .abi 文件")
                    self.status_label.config(text="未找到文件", foreground="orange")
                else:
                    self.log(f"找到 {len(ab1_files)} 个 ab1 文件，开始批量转换...")
                    self.log("-" * 50)
                    
                    success_count = 0
                    for i, fpath in enumerate(ab1_files, 1):
                        self.log(f"[{i}/{len(ab1_files)}] 处理: {fpath.name}")
                        if process_single_file(fpath, output_path, dpi=dpi, log_callback=self.log):
                            success_count += 1
                        else:
                            self.log(f"  ✗ 失败")
                    
                    self.log("-" * 50)
                    self.log(f"转换完成！成功: {success_count}/{len(ab1_files)}")
                    self.status_label.config(
                        text=f"完成: {success_count}/{len(ab1_files)}", 
                        foreground="green"
                    )
            else:
                raise FileNotFoundError(f"输入路径不存在: {input_path}")
                
        except Exception as e:
            error_msg = f"转换过程中出错: {str(e)}"
            self.log(f"✗ {error_msg}")
            self.status_label.config(text="转换出错", foreground="red")
            messagebox.showerror("错误", error_msg)
        finally:
            self.progress.stop()
            self.convert_button.config(state=tk.NORMAL)
            self.is_processing = False

def main():
    root = tk.Tk()
    app = Ab1ToPngGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

