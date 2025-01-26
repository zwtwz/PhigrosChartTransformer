#听歌识曲识别模块
import pyautogui, time, pytesseract, config

pytesseract.pytesseract.tesseract_cmd = config.tesseractPath

resultStateButtonText = config.resultStateButtonText
runningStateButtonText = config.runningStateButtonText


def getText(position):
    if position == 1: #歌名识别
        screenshot = pyautogui.screenshot(region=(config.songNameX, config.songNameY, config.songNameWidth, config.songNameHeight))
    elif position == 2: #按钮文字识别
        screenshot = pyautogui.screenshot(region=(config.buttonX, config.buttonY, config.buttonWidth, config.buttonHeight))
    context = pytesseract.image_to_string(screenshot, lang='chi_sim', config='--psm 7 -c page_separator=""')
    return context

def songRecognize():
    print("开始识别歌曲...")
    #识别歌曲
    if getText(2) == "停止识别":
        pyautogui.click(config.buttonX,config.buttonY)
        pyautogui.move(0,200)
        time.sleep(0.1)
    pyautogui.click(config.buttonX,config.buttonY)
    pyautogui.move(0,200)

    duration = 0
    while duration < 17:
        time.sleep(1)
        duration += 1
        if "重新识别" in getText(2):
            break

    if duration >= 17:
        print("识别超时")
        return None
    else:
        songName = getText(1)
        print("歌曲名：", songName)
        return songName.replace("\n", "")

getText(1)
