# 配置文件
# 这两行别动
import os
currentPath = os.getcwd()

# 程序运行目录，如有需要自行更改（虽然我没测试过改了以后能不能运行）
rootPath = currentPath # 根目录，默认为当前路径
dataPath = os.path.join(rootPath, 'data') # 数据文件目录
inputChartsPath = os.path.join(rootPath, 'Charts') # 原始谱面目录
illustrationsPath = os.path.join(rootPath, 'Illustrations') # 曲绘目录
musicsPath = os.path.join(rootPath, 'Musics') # 音乐目录
outputChartsPath = os.path.join(rootPath, 'Output') # 输出谱面目录

#别动
paths = [rootPath, dataPath, inputChartsPath, illustrationsPath, musicsPath, outputChartsPath]

# 控制是否在曲绘文件夹内搜索使用已存在的曲绘文件
# （就是phi包内自带的）
# 设为True会检索匹配的文件，耗时长但分辨率较高
# 设为False会直接保存网页上的曲绘文件，耗时短但是分辨率只有一半
useExistedIllustration = True

# 程序处理的难度，不要哪个删哪个（不能全删完）（注意格式,大小写,必须一字不差）
# 可以是如下值：EZ , HD , IN , AT , SP , Legacy
# 更改完后需要重置谱面元数据
handlingLevels = ["EZ", "HD", "IN", "AT", "SP", "Legacy"]



# 以下为自动识别歌曲设置，建议先去看下“songRecognize.py”写了点啥再改
# 程序会模拟键盘鼠标来操控电脑上的听歌识曲软件，识别歌名
# 然后用截图ocr（图片转文字）来识别曲名。
# 不同音乐软件逻辑不同，因此可以根据需要自行修改。
# 注：听歌识曲模块 songRecognize.py
#    主函数 songRecognize() 调用时进行歌曲识别，阻塞进程。
#    无参数传入，成功时返回曲名（str），失败时返回None

# 设置为True启用自动识别歌曲，比较麻烦，默认关闭。
useAutoSongRecognizing = False

# tesseractOCR的可执行文件路径，需要手动本地安装。
tesseractPath = r'.\Tesseract-OCR\tesseract.exe'

# 听歌识曲OCR识别点位
# 歌名显示范围
# 以主屏幕左上角为坐标原点，向下、向右分别为x轴、y轴正方向。
# 坐标可利用程序文件夹中的“获取屏幕坐标.py”获取。
songNameX = 1395
songNameY = 455
songNameWidth = 570
songNameHeight = 50

# 控制按钮及文字范围
# 听歌识曲的软件（我用的电脑版q音）在识别中、识别结果等不同状态时 控制按钮上面的文字不同
# 程序以此判断软件识曲状态

# 在识别结果页按钮上显示的文字
resultStateButtonText = "重新识别"
# 在正在识别状态下按钮上显示的文字
runningStateButtonText = "停止识别"

buttonX = 1385 # 按钮位置，需要实际能够点到
buttonY = 925
buttonWidth = 110 # 按钮大小
buttonHeight = 45

