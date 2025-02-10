from tkinter import filedialog
from config import paths

def select_dir():
    """弹出文件选择对话框，选择目录"""
    filepath = filedialog.askdirectory(initialdir="%%homepath%%\\Desktop",
                                title="选择文件保存目录")
    return filepath

def select_file():
        """弹出文件选择对话框，选择文件"""
        # 在vscode内调试可能会出现文件选择框打不开的情况，但是单独打开文件能用。
        filepath = filedialog.askopenfilename(initialdir=paths["illustrationsPath"],
                                    title="选择曲绘",
                                    filetypes=[('png imgs', '.png'), ('jpg imgs', '.jpg'), ('all files', '.*')])
        return filepath