#主程序
import os, json, pygame, re
from tkinter import filedialog
from tinytag import TinyTag
from copy import deepcopy

import config
import chartSearch
import songRecognize
import metadataGrab
import chartTransform
import illustrationSearch

#音乐集成
class MusicPlayer:
    def __init__(self):
        pygame.mixer.init()
    def play(self, music_file):
        pygame.mixer.music.load(music_file)
        pygame.mixer.music.play(1)
        return TinyTag.get(music_file).duration
    def stop(self):
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    def is_playing(self):
        return pygame.mixer.music.get_busy()


#程序运行目录检查，配置加载
datapath = config.dataPath
songsInformationFile = os.path.join(datapath, "songsInformation.json")
musicsPath = config.musicsPath
illustrationPath = config.illustrationsPath

paths = config.paths
for i in paths:
    if not os.path.exists(i):
        os.mkdir(i)

useExistedIllustration = config.useExistedIllustration
handlingLevels = config.handlingLevels
useAutoSongRecognizing = config.useAutoSongRecognizing



def selectFile():
    # 弹出文件选择对话框，选择文件
    # 在vscode内调试可能会出现文件选择框打不开的情况，但是单独打开文件能用。
    filepath = filedialog.askopenfilename(initialdir=illustrationPath,
                                title="选择曲绘",
                                filetypes=[('png imgs', '.png'), ('jpg imgs', '.jpg'), ('all files', '.*')])
    return filepath

def selectDir():
    filepath = filedialog.askdirectory(initialdir="%%homepath%%\\Desktop",
                                title="选择文件保存目录")
    return filepath

    

def generateLutAndPezFiles(musicList, mode=0):
    #生成完整谱面查找表和谱面文件
    player = MusicPlayer()
    songsInformation = {"metadatas":[],
                 "errors": {"informationError": [],
                    "chartFileNotFoundError": [],
                    "illustrationNotFoundError": []}}
    print("""
    开始处理
    注意：此处按下ctrl+c(终止程序快捷键)，可以直接终止程序并保存（仍有一定概率触发异常）。""")
    #ctrl + c处理
    numOfMusic = len(musicList)
    try:
        for i in range(numOfMusic):
            music = musicList[i]
            i += 1
            #开始处理
            print("\n处理(%s/%s, %s%%)：%s"%(i, numOfMusic, str(int(i * 100 / numOfMusic)), music ))
            musicPath = os.path.join(musicsPath, music)
            durationOfMusicFile = int(player.play(musicPath))

            if mode == 0:
                #存储歌曲信息
                with open(songsInformationFile, "w", encoding="utf-8") as f:
                    json.dump(songsInformation, f, ensure_ascii=False, indent=4)

                #正常模式下识别歌曲并获取歌曲元数据
                #听歌识曲
                recognizedSongName = songRecognize.songRecognize()
                player.stop()
                if recognizedSongName == None:
                    songsInformation["errors"]["informationError"].append(music)
                    continue

                #元数据抓取
                metadata = metadataGrab.searchSong(recognizedSongName)
                if metadata == None:
                    songsInformation["errors"]["informationError"].append(music)
                    continue

                #重复歌曲检测
                skipThisSong = False
                existSongs = [*songsInformation["metadatas"]]
                for i in songsInformation["errors"]:
                    existSongs.extend(songsInformation["errors"][i])
                for i in existSongs:
                    if i == metadata["name"]:
                        print("检测到重复歌曲")
                        skipThisSong = True
                        break
                if skipThisSong:
                    continue
                
                #歌曲时长匹配检测
                if not metadata["duration"] in range(durationOfMusicFile-3, durationOfMusicFile+3) :
                    songsInformation["errors"]["informationError"].append(music)
                    print("歌曲时长不匹配:")
                    print(" 本地文件: " + str(durationOfMusicFile))
                    print(" wiki记录: " + str(metadata["duration"]))
                    continue
                metadata["music"] = music

            elif mode == 1:
                #错误处理模式：手动搜索模式
                url = input("请输入wiki链接，留空跳过：")
                player.stop()
                if url == "":
                    print("Error: 跳过")
                    songsInformation["errors"]["informationError"].append(music)
                    continue

                metadata = metadataGrab.metadataGrab(url)
                if metadata == None:
                    print("Error: 获取元数据失败")
                    songsInformation["errors"]["informationError"].append(music)
                    continue

                #重复歌曲检测
                skipThisSong = False
                existSongs = [*songsInformation["metadatas"]]
                for i in songsInformation["errors"]:
                    existSongs.extend(songsInformation["errors"][i])
                for i in existSongs:
                    if i == metadata["name"]:
                        print("检测到重复歌曲")
                        skipThisSong = True
                        break
                if skipThisSong:
                    continue

            elif mode == 2:
                #错误处理模式：手动输入全部元数据模式
                skipThisSong = False
                while True:
                    songName = input("曲名（留空跳过此歌曲）：")
                    player.stop()
                    if songName == "":
                        songsInformation["errors"]["informationError"].append(music)
                        skipThisSong = True
                        break

                    #重复歌曲检测
                    skipThisSong = False
                    existSongs = [*songsInformation["metadatas"]]
                    for i in songsInformation["errors"]:
                        existSongs.extend(songsInformation["errors"][i])
                    for i in existSongs:
                        if i == metadata["name"]:
                            print("检测到重复歌曲")
                            skipThisSong = True
                            break
                    if skipThisSong:
                        continue
                    
                    duration = None
                    while duration == None:
                        durationText = input("持续时间(Duration), 格式： mm:ss   > ")
                        durationList = re.split(":", durationText.replace(" ", ""))
                        try:
                            duration = int(durationList[0]) * 60 + int(durationList[1])
                        except:
                            print("请按正确格式输入(冒号用英文半角)持续时间")

                    metadata = {
                        "name": songName,
                        "composer": input("曲师(Artist)："),
                        "illustrator": input("绘师(Illustration)："),
                        "illustration": "",
                        "illustrationUrl": input("曲绘图片的在线链接（可以在图片上右键，复制图片链接）："),
                        "music": music,
                        "duration": duration,
                        "bpm": "",
                        "charts": None
                    }

                    charts = []
                    lastCharter = "佚名"
                    for level in ("SP", "EZ", "HD", "IN", "AT", "Legacy"):
                        print("填写%s难度谱面信息：" % level)
                        difficulty = input("  谱面定数(Level)（留空跳过此难度）：")
                        if difficulty == "":
                            continue
                        else:
                            difficulty = float(difficulty)
                        
                        charter = input("  谱师(Chart design)（留空将设置为: %s ）\n    请输入：" % lastCharter)
                        if charter == "":
                            charter = lastCharter
                        else:
                            lastCharter = charter
                        chart = {
                            "level": level,
                            "difficulty": difficulty,
                            "numOfNotes": int(input("  物量(Note count)（整数）：")),
                            "chart": "",
                            "charter": charter
                        }
                        charts.append(chart)
                        if level == "SP":
                            break
                    metadata["charts"] = charts

                    if input("请在核对以上信息正确后按下回车。\n输入其他字符将返回修改:") == "":
                        break

                if skipThisSong:
                    continue


            #曲名非法字符剔除
            pattern = r'[<>:"/\\|?*\x00-\x1F]'
            metadata["name"] = re.sub(pattern, "_", metadata["name"])


            #曲绘文件搜索或保存
            illustrationBin = metadataGrab.fileBinTextGet(metadata["illustrationUrl"])
            if illustrationBin == None:
                print("曲绘下载失败")
                songsInformation["errors"]["illustrationNotFoundError"].append(metadata)
                continue
            if useExistedIllustration:
                illustrationFileName = illustrationSearch.illustrationSearch(illustrationBin)
                if illustrationFileName == None:
                    songsInformation["errors"]["illustrationNotFoundError"].append(metadata)
                    continue
            else:
                illustrationFileName = metadata["name"] + ".png"
                print("保存曲绘中：" + illustrationFileName)
                with open(os.path.join(illustrationPath, illustrationFileName), "wb") as f:
                    f.write(illustrationBin)
            metadata["illustration"] = illustrationFileName


            #谱面搜索
            searchResultBpm = chartSearch.searchChartFilename(metadata["charts"])
            #部分曲子实际上没有Legacy难度，故删除之。
            for i in range(len(metadata["charts"])):
                chart = metadata["charts"][i]
                if chart["level"] == "Legacy" and chart["chart"] == "":
                    del metadata["charts"][i]
            
            if searchResultBpm == -1:
                #-1为满足条件谱面数量大于1而无法确定的情况
                songsInformation["errors"]["chartFileNotFoundError"].append(metadata)
                continue
            elif searchResultBpm == None:
                #None为没有满足条件的谱面的情况，这通常是由于wiki信息有误，因此归为infoError
                songsInformation["errors"]["informationError"].append(music)
                continue
            metadata["bpm"] = searchResultBpm


            songsInformation["metadatas"].append(metadata)

            #谱面生成
            chartTransform.transform(metadata)
            print("处理成功！")

    except KeyboardInterrupt:
        print("Error：由于键盘事件，程序终止.")
    except BaseException as e:
        print("Error：由于未知错误，程序终止.")
        print(e)
    finally:
        player.stop()
        if mode == 0:
            print("正在保存")
            with open(songsInformationFile, "w", encoding="utf-8") as f:
                    json.dump(songsInformation, f, ensure_ascii=False, indent=4)

    return songsInformation



def illustrationNotFoundErrorHandling():
    #处理曲绘未找到错误
    choice = illustrationBin =  ""
    print("""\n进行曲绘未找到错误处理
        请选择处理方式：
        a. 直接下载网络曲绘（分辨率较低）
        b. 手动选择曲绘文件
        注意：此处不捕获由ctrl+c(终止程序快捷键)引发的错误。
        注意：在b模式下，在文件选择窗口点击取消会跳过歌曲
        注意：在b模式下，会自动播放歌曲，请注意音量。""")
    
    while not choice in ["a", "b"]:
        choice = input("请输入单个小写字母> ")

    if choice == "b":
        player = MusicPlayer()
        
    global songsInformation
    #尝试加载元数据
    try:
        songsInformation
    except NameError:
        with open(songsInformationFile, "r", encoding='utf-8') as f:
            songsInformation = json.loads(f.read())

    errors  = songsInformation["errors"]["illustrationNotFoundError"]
    formerErrorNum = len(errors)
    #创建列表，存储新产生的错误
    undealedErrors = []


    for i in range(formerErrorNum):
        metadata = errors[i]
        print("\n处理："+ metadata["name"])

        if choice == "a":
            #网络下载曲绘并保存
            illustrationBin = metadataGrab.fileBinTextGet(metadata["illustrationUrl"])
            if illustrationBin == None:
                print("曲绘下载失败")
                undealedErrors.append(metadata)
                continue

        elif choice == "b":
            #选择本地文件
            print("曲师：" + metadata["composer"])
            print("绘师：" + metadata["illustrator"])

            musicPath = os.path.join(musicsPath, metadata["music"])
            if os.path.exists(musicPath):
                player.play(musicPath)
            else:
                print("Error: 歌曲音频文件不存在！")
                print(musicPath)
                undealedErrors.append(metadata)
                continue

            illustrationFilePath = selectFile()
            while not os.path.exists(illustrationFilePath) and not illustrationFilePath == "":
                print("文件不存在！")
                illustrationFilePath = selectFile()

            if illustrationFilePath == "":
                print("Error: 跳过歌曲")
                player.stop()
                undealedErrors.append(metadata)
                continue

            player.stop()

            #如果曲绘文件不在曲绘目录内，则复制之
            illustrationFileName = os.path.basename(illustrationFilePath)
            if not os.path.exists(os.path.join(illustrationPath,illustrationFileName)):
                with open(illustrationFilePath, "rb") as f:
                    illustrationBin = f.read()

        #通过判断是否存储曲绘数据，判断需要保存（或复制）曲绘文件，还是直接使用现有文件 
        if not illustrationBin == "":
            illustrationStorageName = metadata["name"] + ".png"
            print("保存曲绘中：" + illustrationStorageName)
            with open(os.path.join(illustrationPath, illustrationStorageName), "wb") as f:
                f.write(illustrationBin)
            metadata["illustration"] = illustrationStorageName
            illustrationBin = ""
        else:
            metadata["illustration"] = illustrationFileName

        #转换铺面
        chartTransform.transform(metadata)
        #追加至metadata
        songsInformation["metadatas"].append(metadata)
        print("处理成功！")
        
    #直接替换原有错误列表
    songsInformation["errors"]["illustrationNotFoundError"] = undealedErrors
    
    
    print("处理完成：")
    print("成功处理 " + str(formerErrorNum - len(undealedErrors)))
    print("未处理 " + str(len(undealedErrors)))

    #存储歌曲信息
    with open(songsInformationFile, "w", encoding="utf-8") as f:
        json.dump(songsInformation, f, ensure_ascii=False, indent=4)



def manualInformationHandling(musicList=[], isErrorHandling=False):
    #处理信息未找到错误
    #尝试加载元数据
    global songsInformation
    try:
        songsInformation
    except NameError:
        if os.path.exists(songsInformationFile):
            with open(songsInformationFile, "r", encoding='utf-8') as f:
                songsInformation = json.loads(f.read())
        else:
            print("未找到本地数据文件")
            songsInformation = {"metadatas":[],
                    "errors": {"informationError": [],
                    "chartFileNotFoundError": [],
                    "illustrationNotFoundError": []}}

    if isErrorHandling:
        errors  = songsInformation["errors"]["informationError"]
        musicList = errors
        numOfMusics = len(errors)
        print("""\n进行歌曲信息错误处理
            此错误包含3种情况：
            1. 听歌识曲失败
            2. 没有搜到歌曲信息
            3. wiki记录的歌曲时长 与 本地音频文件时长 间 误差超过范围
            4. wiki记录的谱面物量有误，导致搜不到相应谱子""")
        
    choice = ""
    print("""请选择信息收集方式：
        a. 在给出的wiki中手动搜索到所听到的歌曲，然后将页面地址输入程序，由程序抓据")
        b. 手动输入所听到的歌曲的所有数据（不建议活受罪）
        注意：输入只有一次机会，请小心不要打错字，否则可能引起幽蓝边境异象(雾)
        注意：会自动播放歌曲，请注意音量。""")
    
    while not choice in ["a", "b"]:
        choice = input("请输入单个小写字母> ")

    if choice == "a":
        mode = 1
        print("""请在浏览器中打开此地址(必须为此地址)：https://phigros.fandom.com/wiki/Special:Search
        接下来，你将会听到音乐播放
        请在上述页面中搜索你听到的音乐，并将其wiki页面对应的地址复制下来，然后输入到本程序中。
        tips.你可以通过打开对应wiki并复制地址栏地址，也可以通过直接右键超链接，复制wiki链接地址获取地址。
        例如：
        你听到“登，登登登，登登登，等登邓灯蹬瞪凳磴嶝噔僜墱澄”
        所以，你在搜索框搜索“Rrhar'il”
        你找到了对应的搜索结果，是第一条，其标题链接写着：Rrhar'il
        你右键了那个链接，点击了“复制链接地址”，复制了如下链接地址：https://phigros.fandom.com/wiki/Rrhar'il
        你返回终端，在光标闪烁的位置右键点击，将其粘贴在程序内，然后按下了回车键。\n""")
    else:
        mode = 2
        print("""请任意找一个提供歌曲信息的地方
        接下来，你将会听到音乐播放
        你需要根据音乐回答以下问题：
            曲名 曲师 绘师 歌曲持续时间 曲绘图片的在线链接
            每个难度的 谱面定数 物量 谱师
        根据提示，将答案输入程序并按下回车。
        注意：持续时间、谱面定数、物量需要为整数值
        注意：曲绘图片的在线链接 可以直接复制你找的wiki的（推荐），也可以上网搜，
            一般在图片上右键会有复制图像链接的选项，实在不会上网搜。
        注意：愚人节曲和其看门曲是两个不同的曲子，不要弄混
            愚人节曲只有SP难度，因此任意一个曲子，只要填了SP难度的信息，都会直接跳过其他所有难度。
              
        本程序默认自动采集fandom wiki的数据，但是其中包含一些错误，为了进行交叉验证，不建议在此处使用fandom wiki。
        推荐wiki：萌娘百科，https://zh.moegirl.org.cn/Phigros/谱面信息\n""")
        
    input("按下回车开始程序")
    print("普通高中phigros听力测试现在开始(雾)")
    
    #战后结算
    newSongsInformation = generateLutAndPezFiles(musicList, mode)

    numOfSuccessAddressedErrors = len(newSongsInformation["metadatas"])
    numOfFailedAddressedErrors = sum([len(newSongsInformation["errors"]["illustrationNotFoundError"]), 
                                    len(newSongsInformation["errors"]["chartFileNotFoundError"]),
                                    len(newSongsInformation["errors"]["informationError"])])
    numOfTotalAddressedErrors = numOfSuccessAddressedErrors + numOfFailedAddressedErrors

    #元数据整合
    if isErrorHandling:
        songsInformation["metadatas"].extend(newSongsInformation["metadatas"])
        songsInformation["errors"]["illustrationNotFoundError"].extend(newSongsInformation["errors"]["illustrationNotFoundError"])
        songsInformation["errors"]["chartFileNotFoundError"].extend(newSongsInformation["errors"]["chartFileNotFoundError"])
        if numOfTotalAddressedErrors < numOfMusics:
            songsInformation["errors"]["informationError"] = newSongsInformation["errors"]["informationError"] + errors[numOfTotalAddressedErrors:]
        else:
            songsInformation["errors"]["informationError"] = newSongsInformation["errors"]["informationError"]
    else:
        songsInformation = newSongsInformation
    

    #存储歌曲信息
    with open(songsInformationFile, "w", encoding="utf-8") as f:
        json.dump(songsInformation, f, ensure_ascii=False, indent=4)
    
    print("处理完成：")
    print("总数 " + str(numOfMusics))
    print("成功处理 " + str(numOfSuccessAddressedErrors))
    print("处理失败 " + str(numOfFailedAddressedErrors))
    print("未处理 " + str(numOfMusics - numOfTotalAddressedErrors))
    input("\n按下回车退出")



def chartFileNotFoundErrorDealing():
    print("""进行谱面未找到错误处理
          此错误是由在查找谱面的过程中，通过bpm与物量无法定位到唯一谱面导致的。
          接下来，对于每个无法确定的谱面，程序将分别生成编号的多个谱面文件，
          你需要手动将他们导入phira（有电脑版）或其他模拟器，手动确定正确的文件，然后在程序中选择。

          你需要先选择一个文件夹作为谱子保存的地方。
          """)
    input("按下回车键开始")

    savingPath = selectDir()

    global songsInformation
    try:
        songsInformation
    except NameError:
        with open(songsInformationFile, "r", encoding='utf-8') as f:
            songsInformation = json.loads(f.read())
    
    errors = songsInformation["errors"]["chartFileNotFoundError"]
    numOfErrors = len(errors)

    for index in range(numOfErrors):
        #存储元数据
        with open(songsInformationFile, "w", encoding="utf-8") as f:
            json.dump(songsInformation, f, ensure_ascii=False, indent=4)

        metadata = errors[index]
        music = metadata["music"]
        songName = metadata["name"]
        print("\n处理(%s/%s, %s%%)：%s"%(index+1, numOfErrors, str(int((index+1) * 100 / numOfErrors)), songName ))

        #重复歌曲检测
        skipThisSong = False
        existSongs = [*songsInformation["metadatas"]]
        for i in songsInformation["errors"]:
            if i == "chartFileNotFoundError":
                continue
            existSongs.extend(songsInformation["errors"][i])
        for i in existSongs:
            if i == metadata["name"]:
                print("检测到重复歌曲")
                skipThisSong = True
                break
        if skipThisSong:
            continue

        #谱面搜索
        searchResultBpm = chartSearch.searchChartFilename(metadata["charts"], isErrorDealing=True)
        #部分曲子实际上没有Legacy难度，故删除之。
        for i in range(len(metadata["charts"])):
            chart = metadata["charts"][i]
            if chart["level"] == "Legacy" and chart["chart"] == "":
                del metadata["charts"][i]

        if searchResultBpm == None:
            #None为没有满足条件的谱面的情况，这通常是由于wiki信息有误，因此归为infoError
            songsInformation["errors"]["informationError"].append(music)
            continue

        metadata["bpm"] = searchResultBpm

        #多谱面文件处理
        for chart in metadata["charts"]:
            if chart["chart"] == "":
                print("  处理 %s 难度" % chart["level"])
                onProcessingMetadata = deepcopy(metadata)
                del onProcessingMetadata["charts"]
                onProcessingCharts = []
                possibleCharts = chart["possibleCharts"]
                numOfpossibleCharts = len(possibleCharts)

                for i in range(numOfpossibleCharts):
                    possibleChart = possibleCharts[i]
                    onProcessingChart = deepcopy(chart)
                    onProcessingChart["level"] = "选项" + str(i + 1)
                    onProcessingChart["chart"] = possibleChart
                    onProcessingCharts.append(onProcessingChart)

                onProcessingMetadata["charts"] = onProcessingCharts

                chartTransform.transform(onProcessingMetadata, savingPath, isErrorDealing=True)
                while True:
                    try:
                        choice = int(input("请选择要使用的文件，并输入整数：")) - 1
                    except:
                        print("请输入整数!")
                    else:
                        break
                chart["chart"] = possibleCharts[choice]
                del chart["possibleCharts"]

        #谱面生成
        chartTransform.transform(metadata)
        songsInformation["metadatas"].append(metadata)
        del songsInformation["errors"]["chartFileNotFoundError"][index]

        print("处理成功！")

    #存储元数据
    with open(songsInformationFile, "w", encoding="utf-8") as f:
        json.dump(songsInformation, f, ensure_ascii=False, indent=4)

        
musicList = [music for music in os.listdir(musicsPath) if "wav" in music]
#musicList = ["music #2491.wav"]
#generateLutAndPezFiles(musicList)
#informationErrorHandling()
#chartFileNotFoundErrorDealing()
#illustrationNotFoundErrorHandling()


if __name__ == "__main__":
    print("""欢迎使用本谱面转换程序程序
    在使用之前，请确保您已经完全阅读github主页上的内容，并已完成程序相关配置。""")
    
    while True:
        choiceA = int(input("""
请选择功能：
    【1】 根据本地数据，直接生成全部谱面文件（首次使用请选择）
    【2】 根据本地数据，补全未转换的谱面（程序中途崩溃请选择）
    【3】 更新本地数据文件（将新版本phi的文件直接追加到相应目录中后，使用此项更新）
    【4】 重置本地数据文件（仅包括谱面元数据）
    【5】 重置本地数据文件（全部）
    【6】 错误谱面处理
请输入一位整数：
              """))
        
        match choiceA:
            case 1:
                #直接生成谱面文件
                pass

            case 2:
                #补全未转换的谱面
                pass

            case 3:
                #更新本地数据文件
                pass

            case 4:
                #重置本地数据文件（仅包括谱面元数据）
                musicList = [music for music in os.listdir(musicsPath) if "wav" in music]
                if useAutoSongRecognizing == True:
                    print("\n请保证听歌识曲软件处于正确状态")
                    print("注意，原先的歌曲元数据（包括错误信息）将被完全覆盖。")
                    choiceB = input("直接按下回车开始，输入n取消。")
                    if choiceB == "n":
                        continue
                    generateLutAndPezFiles(musicList=musicList)
                else:
                    print("注意，原先的歌曲元数据（包括错误信息）将被完全覆盖。")
                    choiceB = input("直接按下回车开始，输入n取消。")
                    if choiceB == "n":
                        continue
                    manualInformationHandling(musicList=musicList, isErrorHandling=False)
                    
            case 5:
                #重置全部数据文件
                pass

            case 6:
                #错误处理
                pass
        
