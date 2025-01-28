#python3.10
#鼠标坐标获取器

import pyautogui, pyclip

while True:
    pause = input("保持此窗口处于活动状态，按回车键获取鼠标坐标")
    x,y = pyautogui.position()
    print(x,y)
    pyclip.copy(str(x)+','+str(y))