import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import timedelta

class SubToLRCApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SubToLRC")
        self.root.geometry("400x250")  # 增加窗口高度以适应新控件

        # 创建主框架
        self.main_frame = tk.Frame(self.root, padx=20, pady=20)
        self.main_frame.pack(expand=True)

        # 创建标签显示选择的文件夹
        self.folder_label = tk.Label(self.main_frame, text="未选择文件夹", wraplength=350)
        self.folder_label.pack(pady=10)

        # 创建选择文件夹按钮
        self.select_button = tk.Button(self.main_frame, text="选择文件夹", command=self.select_folder)
        self.select_button.pack(pady=5)

        # 创建时间偏移输入框和标签
        self.offset_frame = tk.Frame(self.main_frame)
        self.offset_frame.pack(pady=10)
        
        self.offset_label = tk.Label(self.offset_frame, text="第一句歌词开始的时间：")
        self.offset_label.pack(side=tk.LEFT)
        
        self.offset_entry = tk.Entry(self.offset_frame, width=10)
        self.offset_entry.pack(side=tk.LEFT)
        self.offset_entry.insert(0, "[00:00.00]")  # 设置默认值
        
        # 创建说明标签
        self.hint_label = tk.Label(self.main_frame, text="格式：[mm:ss.xx]")
        self.hint_label.pack()

        # 创建转换按钮
        self.convert_button = tk.Button(self.main_frame, text="开始转换", command=self.start_conversion)
        self.convert_button.pack(pady=10)
        self.convert_button['state'] = 'disabled'  # 初始状态下禁用

        # 存储选择的文件夹路径
        self.folder_path = None

    def select_folder(self):
        self.folder_path = filedialog.askdirectory(title="选择文件夹")
        if self.folder_path:
            self.folder_label.config(text=f"已选择: {self.folder_path}")
            self.convert_button['state'] = 'normal'  # 启用转换按钮
        else:
            self.folder_label.config(text="未选择文件夹")
            self.convert_button['state'] = 'disabled'

    def start_conversion(self):
        if not self.folder_path:
            messagebox.showerror("错误", "请先选择文件夹")
            return

        # 获取偏移时间
        offset_str = self.offset_entry.get()
        if not offset_str:
            messagebox.showwarning("警告", "请输入偏移时间")
            return

        # 解析偏移时间
        offset_match = re.match(r'\[(\d+):(\d+\.\d+)\]', offset_str)
        if not offset_match:
            messagebox.showerror("错误", "偏移时间格式错误，请使用[mm:ss.xx]格式")
            return
        
        offset_minutes, offset_seconds = offset_match.groups()
        offset_time = timedelta(minutes=int(offset_minutes), seconds=float(offset_seconds))

        try:
            # 遍历文件夹中的文件
            for subdir, _, files in os.walk(self.folder_path):
                for file in files:
                    if file.endswith('.ass') or file.endswith('.srt'):
                        subdir_name = os.path.basename(subdir)
                        file_path = os.path.join(subdir, file)
                        self.create_lrc_file(subdir_name, file, file_path, offset_time)
            
            messagebox.showinfo("成功", "转换完成！")
        except Exception as e:
            messagebox.showerror("错误", f"转换过程中出现错误：\n{str(e)}")

    def create_lrc_file(self, subdir_name, file_name, file_path, offset_time):
        # 从文件夹名称提取歌手和专辑信息
        folder_artist, album = re.match(r'(.+?) - (\d+ .+)', subdir_name).groups()
        # 从文件名提取歌手和歌曲标题
        file_artist, song_title = re.match(r'(.+?) - (.+)\.(ass|srt)', file_name).groups()[:2]
        
        # 创建LRC文件头部信息
        lrc_content = (
            f"[ti:{song_title}]\n"
            f"[ar:{folder_artist}]\n"
            f"[al:{album}]\n"
            f"[by:SubToLRC]\n"
            f"[00:00.00]{file_artist} - {song_title}\n"
        )

        # 根据文件类型选择相应的解析方法
        if file_name.endswith('.ass'):
            lrc_content += self.parse_ass_file(file_path, offset_time)
        elif file_name.endswith('.srt'):
            lrc_content += self.parse_srt_file(file_path, offset_time)

        # 生成LRC文件
        lrc_file_path = os.path.join(os.path.dirname(file_path), f"{os.path.splitext(file_name)[0]}.lrc")
        with open(lrc_file_path, 'w', encoding='utf-8') as lrc_file:
            lrc_file.write(lrc_content)

    def parse_ass_file(self, file_path, offset_time):
        lrc_lines = []
        seen_lines = set()
        first_timestamp = None
        
        # 第一遍读取，获取第一个时间戳
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            for line in file:
                match = re.match(r'Dialogue: \d,(\d+):(\d+):([\d.]+),\d+:\d+:\d+.\d+,Default,,\d,\d,\d,,(.+)', line)
                if match:
                    hours, minutes, seconds, _ = match.groups()
                    first_timestamp = timedelta(hours=int(hours), minutes=int(minutes), seconds=float(seconds))
                    break

        # 第二遍读取，处理所有行
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            for line in file:
                match = re.match(r'Dialogue: \d,(\d+):(\d+):([\d.]+),\d+:\d+:\d+.\d+,Default,,\d,\d,\d,,(.+)', line)
                if match:
                    hours, minutes, seconds, text = match.groups()
                    current_time = timedelta(hours=int(hours), minutes=int(minutes), seconds=float(seconds))
                    # 计算相对时间并添加偏移
                    time_diff = current_time - first_timestamp + offset_time
                    # 转换为分钟和秒
                    total_seconds = time_diff.total_seconds()
                    minutes, seconds = divmod(total_seconds, 60)
                    # 生成时间标签
                    time_tag = f"[{int(minutes):02}:{seconds:05.2f}]"
                    line_content = f"{time_tag}{text.strip()}"
                    
                    if line_content not in seen_lines:
                        lrc_lines.append(line_content)
                        seen_lines.add(line_content)
        
        return '\n'.join(sorted(lrc_lines)) + '\n'

    def parse_srt_file(self, file_path, offset_time):
        lrc_lines = []
        first_timestamp = None

        # 第一遍读取，获取第一个时间戳
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            for line in file:
                time_match = re.match(r'(\d+):(\d+):(\d+),(\d+) --> \d+:\d+:\d+,\d+', line)
                if time_match:
                    hours, minutes, seconds, milliseconds = time_match.groups()
                    first_timestamp = timedelta(
                        hours=int(hours),
                        minutes=int(minutes),
                        seconds=int(seconds),
                        milliseconds=int(milliseconds)
                    )
                    break

        # 第二遍读取，处理所有行
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            time_tag = ''
            for line in file:
                time_match = re.match(r'(\d+):(\d+):(\d+),(\d+) --> \d+:\d+:\d+,\d+', line)
                if time_match:
                    hours, minutes, seconds, milliseconds = time_match.groups()
                    current_time = timedelta(
                        hours=int(hours),
                        minutes=int(minutes),
                        seconds=int(seconds),
                        milliseconds=int(milliseconds)
                    )
                    # 计算相对时间并添加偏移
                    time_diff = current_time - first_timestamp + offset_time
                    # 转换为分钟和秒
                    total_seconds = time_diff.total_seconds()
                    minutes, seconds = divmod(total_seconds, 60)
                    time_tag = f"[{int(minutes):02}:{seconds:05.2f}]"
                elif line.strip() and not line.isdigit():
                    if time_tag:
                        lrc_lines.append(f"{time_tag}{line.strip()}")
                        time_tag = ''

        return '\n'.join(sorted(lrc_lines)) + '\n'

if __name__ == "__main__":
    root = tk.Tk()
    app = SubToLRCApp(root)
    root.mainloop()
