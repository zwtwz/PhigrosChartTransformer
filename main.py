#主程序
import os, json, pygame, re
from tkinter import filedialog
from tinytag import TinyTag
from copy import deepcopy

import config

#程序运行目录检查，配置加载
datapath = config.dataPath
songsInformationFile = os.path.join(datapath, "songsInformation.json")
ignoredSongsFile = os.path.join(datapath, "ignoredSongs.json")
onProcessingSongsInformationFile = os.path.join(datapath, "onProcessingSongsInformation.json")
musicsPath = config.musicsPath
illustrationPath = config.illustrationsPath
chartPath = config.inputChartsPath
handlingLevels = config.handlingLevels

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

   

for handlingLevel in handlingLevels:
    if not handlingLevel in ["IN", "EZ", "HD", "SP", "Legacy", "AT"]:
        print("Error: 配置文件中的handlingLevels参数错误")
        exit()
if "SP" in handlingLevels:
    #将SP提到最前，满足查找谱面时的顺序
    handlingLevels.remove("SP")
    handlingLevels.insert(0, "SP")

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

def readSongsInformation():
    if os.path.exists(songsInformationFile):
        with open(songsInformationFile, "r", encoding='utf-8') as f:
            songsInformation = json.loads(f.read())
    else:
        print("未找到本地数据文件")
        songsInformation = {"metadatas":[],
                "errors": {"informationError": [],
                "chartFileNotFoundError": [],
                "illustrationNotFoundError": []}}
    return songsInformation

def readIgnoredSongs():
    if os.path.exists(ignoredSongsFile):
        with open(ignoredSongsFile, "r", encoding='utf-8') as f:
            ignoredSongs = json.loads(f.read())
    else:
        ignoredSongs = []
    return ignoredSongs

def saveSongsInformation(songsInformation):
    #存储歌曲信息
    with open(songsInformationFile, "w", encoding="utf-8") as f:
        json.dump(songsInformation, f, ensure_ascii=False, indent=4)

def saveOnProcessingSongsInformation(data):
    #存储歌曲信息
    with open(onProcessingSongsInformationFile, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def saveIgnoredSongs(ignoredSongs):
    with open(ignoredSongsFile, "w", encoding="utf-8") as f:
        json.dump(ignoredSongs, f, ensure_ascii=False, indent=4)
    

def generateLutAndPezFiles(musicList, mode=0, lastOnProcessingSongsInformation=None):
    #根据musicList生成谱面查找表和谱面文件
    #mode 0: 正常模式，自动识别歌曲并获取元数据
    #mode 1: 错误处理模式，手动给定wiki链接，程序自动抓取数据
    #mode 2: 错误处理模式，手动输入全部元数据
    player = MusicPlayer()
    numOfMusic = len(musicList)
    ignoredSongs = readIgnoredSongs()

    def checkIfSongExist(songName):
        nonlocal numOfMusic
        #检查是否已经存在该歌曲
        existedSongs = [i["name"] for i in onProcessingSongsInformation["metadatas"] ]
        existedSongs.extend([i for i in onProcessingSongsInformation["errors"]["informationError"] ])
        existedSongs.extend([i["name"] for i in onProcessingSongsInformation["errors"]["illustrationNotFoundError"] ])
        existedSongs.extend([i["name"] for i in onProcessingSongsInformation["errors"]["chartFileNotFoundError"] ])
        for existedSong in existedSongs:
            if existedSong == songName:
                print("检测到重复歌曲")
                numOfMusic -= 1
                return True
        return False

    #加载进度
    if lastOnProcessingSongsInformation == None:
        onProcessingSongsInformation = {"metadatas":[],
                    "errors": {"informationError": [],
                    "chartFileNotFoundError": [],
                    "illustrationNotFoundError": []}}
    else:
        onProcessingSongsInformation = lastOnProcessingSongsInformation

    errors = onProcessingSongsInformation["errors"]

    print("""
    开始处理
    注意：此处按下ctrl+c(终止程序快捷键)，可以直接退出并保存进度（仍有一定概率触发异常）。""")
    #ctrl + c处理
    try:
        for i in range(numOfMusic):
            saveOnProcessingSongsInformation(onProcessingSongsInformation)
            saveIgnoredSongs(ignoredSongs)
            music = musicList[i]
            i += 1
            #开始处理
            print("\n处理(%s/%s, %s%%)：%s"%(i, numOfMusic, str(int(i * 100 / numOfMusic)), music ))
            musicPath = os.path.join(musicsPath, music)
            durationOfMusicFile = int(player.play(musicPath))

            if mode == 0:
                #正常模式下识别歌曲并获取歌曲元数据
                #听歌识曲
                recognizedSongName = songRecognize.songRecognize()
                player.stop()
                if recognizedSongName == None:
                    errors["informationError"].append(music)
                    continue

                #元数据抓取
                metadata = metadataGrab.searchSong(recognizedSongName)
                if metadata == None:
                    errors["informationError"].append(music)
                    continue

                #重复歌曲检测
                if checkIfSongExist(metadata["name"]):
                    ignoredSongs.append(music)
                    continue
                
                #歌曲时长匹配检测
                if not metadata["duration"] in range(durationOfMusicFile-3, durationOfMusicFile+3) :
                    errors["informationError"].append(music)
                    print("歌曲时长不匹配:")
                    print(" 本地文件: " + str(durationOfMusicFile))
                    print(" wiki记录: " + str(metadata["duration"]))
                    continue
                metadata["music"] = music

            elif mode == 1:
                #手动搜索模式
                url = input("请输入wiki链接，留空跳过：")
                player.stop()
                if url == "":
                    print("Error: 跳过")
                    errors["informationError"].append(music)
                    continue

                metadata = metadataGrab.metadataGrab(url)
                if metadata == None:
                    print("Error: 获取元数据失败")
                    errors["informationError"].append(music)
                    continue

                #重复歌曲检测
                if checkIfSongExist(metadata["name"]):
                    ignoredSongs.append(music)
                    continue

                metadata["music"] = music

            elif mode == 2:
                #手动输入全部元数据模式
                skipThisSong = False
                while True:
                    songName = input("曲名（留空跳过此歌曲）：")
                    player.stop()
                    if songName == "":
                        errors["informationError"].append(music)
                        skipThisSong = True
                        break

                    #重复歌曲检测
                    if checkIfSongExist(songName):
                        ignoredSongs.append(music)
                        continue
                    
                    #手动输入时不检查歌曲持续时间，因此不用填。
                    #duration = None
                    #while duration == None:
                    #    durationText = input("持续时间(Duration), 格式： mm:ss   > ")
                    #    durationList = re.split(":", durationText.replace(" ", ""))
                    #    try:
                    #        duration = int(durationList[0]) * 60 + int(durationList[1])
                    #    except:
                    #        print("请按正确格式输入(冒号用英文半角)持续时间")

                    metadata = {
                        "name": songName,
                        "composer": input("曲师(Artist)："),
                        "illustrator": input("绘师(Illustration)："),
                        "illustration": "",
                        "illustrationUrl": input("曲绘图片的在线链接（可以在图片上右键，复制图片链接）："),
                        "music": music,
                        "duration": 0,
                        "bpm": "",
                        "charts": None
                    }

                    charts = []
                    lastCharter = "佚名"
                    for level in handlingLevels:
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

                        while True:
                            try:
                                numOfNotes = int(input("  物量(Note count)（整数）："))
                            except:
                                print("Error: 请输入整数")
                                continue
                            else:
                                break

                        chart = {
                            "level": level,
                            "difficulty": difficulty,
                            "numOfNotes": numOfNotes,
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


            #非法字符剔除
            pattern = r'[<>:"/\\|?*\x00-\x1F]'
            metadata["name"] = re.sub(pattern, "_", metadata["name"])
            pattern = r'"'
            metadata["illustrator"] = re.sub(pattern, "_", metadata["illustrator"])


            #曲绘文件搜索或保存
            illustrationBin = metadataGrab.fileBinTextGet(metadata["illustrationUrl"])
            if illustrationBin == None:
                print("曲绘下载失败")
                errors["illustrationNotFoundError"].append(metadata)
                continue
            if useExistedIllustration:
                illustrationFileName = illustrationSearch.illustrationSearch(illustrationBin)
                if illustrationFileName == None:
                    errors["illustrationNotFoundError"].append(metadata)
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
                errors["chartFileNotFoundError"].append(metadata)
                continue
            elif searchResultBpm == None:
                #None为没有满足条件的谱面的情况，这通常是由于wiki信息有误，因此归为infoError
                errors["informationError"].append(music)
                continue
            metadata["bpm"] = searchResultBpm


            onProcessingSongsInformation["metadatas"].append(metadata)

            #谱面生成
            chartTransform.transform(metadata)
            print("处理成功！")

    except KeyboardInterrupt:
        print("Error：由于键盘事件，程序终止.")
    except BaseException as e:
        print("Error：由于未知错误，程序终止.")
        #raise e
        print(e)
    finally:
        player.stop()
        saveOnProcessingSongsInformation(onProcessingSongsInformation)

    return onProcessingSongsInformation



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
    
    choiceD = input("按下回车键开始,输入n返回")
    if choiceD == "n":
        return
    
    while not choice in ["a", "b"]:
        choice = input("请从上面选一个选项，并输入单个小写字母后按下回车> ")

    if choice == "b":
        player = MusicPlayer()
        
    songsInformation = readSongsInformation()

    errors  = songsInformation["errors"]["illustrationNotFoundError"]
    formerErrorNum = len(errors)
    #创建列表，存储新产生的错误
    newSongsInformation = {"metadatas":[],
                        "errors": {"informationError": [],
                        "chartFileNotFoundError": [],
                        "illustrationNotFoundError": []}}


    for i in range(formerErrorNum):
        metadata = errors[i]
        music = metadata["music"]
        print("\n处理："+ metadata["name"])

        if choice == "a":
            #网络下载曲绘并保存
            illustrationBin = metadataGrab.fileBinTextGet(metadata["illustrationUrl"])
            if illustrationBin == None:
                print("曲绘下载失败")
                newSongsInformation["errors"]["illustrationNotFoundError"].append(metadata)
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
                continue

            illustrationFilePath = selectFile()
            while not os.path.exists(illustrationFilePath) and not illustrationFilePath == "":
                print("文件不存在！")
                illustrationFilePath = selectFile()

            if illustrationFilePath == "":
                print("Error: 跳过歌曲")
                player.stop()
                newSongsInformation["errors"]["illustrationNotFoundError"].append(metadata)
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


        #谱面搜索
        searchResultBpm = chartSearch.searchChartFilename(metadata["charts"])
        #部分曲子实际上没有Legacy难度，故删除之。
        for i in range(len(metadata["charts"])):
            chart = metadata["charts"][i]
            if chart["level"] == "Legacy" and chart["chart"] == "":
                del metadata["charts"][i]
        
        if searchResultBpm == -1:
            #-1为满足条件谱面数量大于1而无法确定的情况
            newSongsInformation["errors"]["chartFileNotFoundError"].append(metadata)
            continue
        elif searchResultBpm == None:
            #None为没有满足条件的谱面的情况，这通常是由于wiki信息有误，因此归为infoError
            newSongsInformation["errors"]["informationError"].append(music)
            continue
        metadata["bpm"] = searchResultBpm

        #转换铺面
        chartTransform.transform(metadata)
        #追加至metadata
        newSongsInformation["metadatas"].append(metadata)
        print("处理成功！")
        

    #战后结算
    numOfSuccessAddressed = len(newSongsInformation["metadatas"])
    numOfFailedAddressed = sum([len(newSongsInformation["errors"]["illustrationNotFoundError"]), 
                                    len(newSongsInformation["errors"]["chartFileNotFoundError"]),
                                    len(newSongsInformation["errors"]["informationError"])])
    numOfTotalAddressed = numOfSuccessAddressed + numOfFailedAddressed
    numOfUnhandled = formerErrorNum - numOfTotalAddressed


    #合并数据
    songsInformation["metadatas"].extend(newSongsInformation["metadatas"])
    songsInformation["errors"]["chartFileNotFoundError"].extend(newSongsInformation["errors"]["chartFileNotFoundError"])
    songsInformation["errors"]["informationError"].extend(newSongsInformation["errors"]["informationError"])
    if numOfTotalAddressed < formerErrorNum:
        songsInformation["errors"]["illustrationNotFoundError"] = newSongsInformation["errors"]["illustrationNotFoundError"] + errors[numOfTotalAddressed:]
    else:
        songsInformation["errors"]["illustrationNotFoundError"] = newSongsInformation["errors"]["illustrationNotFoundError"]

    #存储歌曲信息
    saveSongsInformation(songsInformation)
    
    print("处理完成：")
    print("总数 " + str(formerErrorNum))
    print("成功处理 " + str(numOfSuccessAddressed))
    print("处理失败 " + str(numOfFailedAddressed))
    print("未处理 " + str(numOfUnhandled))
    print("请立即检查并处理错误歌曲。")
    input("\n按下回车退出")
    exit()



def informationHandling(option=1):
    #信息收集函数，根据需要进行手动或自动信息收集
    #实现谱面、元数据全新生成、部分更新、信息错误处理
    #option 1: 信息错误处理
    #option 2: 更新本地数据文件
    #option 3: 重置本地数据文件（仅包括谱面元数据）

    #尝试加载元数据
    songsInformation = readSongsInformation()
    ignoredSongs = readIgnoredSongs()


    #判断运行模式：全自动0、半自动1、手动2，并输出提示信息
    if option == 1:
        print("""\n进行歌曲信息错误处理
        此错误包含4种情况：
        1. 听歌识曲失败
        2. 没有搜到歌曲信息
        3. wiki记录的歌曲时长 与 本地音频文件时长 间 误差超过范围
        4. wiki记录的谱面物量有误，导致搜不到相应谱子\n""")
    
    choice = ""
    if option == 1 or not useAutoSongRecognizing:
        #手动模式
        print("""请选择信息收集方式：
        a. 在给出的wiki中手动搜索到所听到的歌曲，然后将页面地址输入程序，由程序抓据
        b. 手动输入所听到的歌曲的所有数据（非必要不要用，比较受罪。）
        注意：a选项中输入只有一次机会，请小心不要打错字，否则可能引起幽蓝边境异象(雾)
        注意：会自动播放歌曲，请注意音量。""")
        print("对于自动、半自动处理无法解决的问题，请尝试手动解决。")
        choice = ""
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
    else:
        #自动模式
        print("\n请保证听歌识曲软件处于正确状态")
        mode = 0

    choiceD = input("按下回车键开始,输入n返回")
    if choiceD == "n":
        return
    
    print("普通高中phigros听力测试现在开始(雾)")


    #根据模式生成musicList
    if option == 1:
        errors  = deepcopy(songsInformation["errors"]["informationError"])
        musicList = errors
    elif option == 2:
        print("检查新音频文件中……")
        musicList = [music for music in os.listdir(musicsPath) if "wav" in music]
        for existMusic in songsInformation["metadatas"]:
            if existMusic["music"] in musicList:
                musicList.remove(existMusic["music"])
            else:
                print(" 新增：" + existMusic["music"])
    elif option == 3:
        musicList = [music for music in os.listdir(musicsPath) if "wav" in music]


    #在onProcessingSongsInformationFile存在的情况下，尝试加载先前进度加载
    numOfFormerProcessedMusics = 0
    if os.path.exists(onProcessingSongsInformationFile):
        choiceC = input("检测到上次未完成的进度，是否继续？(y/其他)")
        if choiceC == "y":
            #防止数据文件不完整导致崩溃
            try:
                with open(onProcessingSongsInformationFile, "r", encoding='utf-8') as f:
                    onProcessingSongsInformation = json.loads(f.read())
            except:
                onProcessingSongsInformation = None
                print("Error: 读取进度文件失败")
            
            #剔除重复歌曲
            existedSongs = [i["music"] for i in onProcessingSongsInformation["metadatas"] ]
            existedSongs.extend(onProcessingSongsInformation["errors"]["informationError"])
            existedSongs.extend([i["music"] for i in onProcessingSongsInformation["errors"]["illustrationNotFoundError"] ])
            existedSongs.extend([i["music"] for i in onProcessingSongsInformation["errors"]["chartFileNotFoundError"] ])
            for i in existedSongs:
                if i in musicList:
                    musicList.remove(i)
                    numOfFormerProcessedMusics += 1
            print("成功加载%s个谱面" % str(numOfFormerProcessedMusics))
        else:
            onProcessingSongsInformation = None
    else:
        onProcessingSongsInformation = None

    #剔除忽略的谱面
    for ignoredSong in ignoredSongs:
        if ignoredSong in musicList:
            musicList.remove(ignoredSong)
    
    numOfMusics = len(musicList)
    print("共有%s个音频文件需要处理" % str(numOfMusics))


    #信息处理
    newSongsInformation = generateLutAndPezFiles(musicList, mode, onProcessingSongsInformation)

    #战后结算
    numOfSuccessAddressed = len(newSongsInformation["metadatas"])
    numOfFailedAddressed = sum([len(newSongsInformation["errors"]["illustrationNotFoundError"]), 
                                    len(newSongsInformation["errors"]["chartFileNotFoundError"]),
                                    len(newSongsInformation["errors"]["informationError"])])
    numOfTotalAddressed = numOfSuccessAddressed + numOfFailedAddressed
    numOfUnhandled = numOfMusics - numOfTotalAddressed + numOfFormerProcessedMusics


    if numOfUnhandled == 0:
        #元数据整合
        if option == 1:
            songsInformation["metadatas"].extend(newSongsInformation["metadatas"])
            songsInformation["errors"]["illustrationNotFoundError"].extend(newSongsInformation["errors"]["illustrationNotFoundError"])
            songsInformation["errors"]["chartFileNotFoundError"].extend(newSongsInformation["errors"]["chartFileNotFoundError"])
            if numOfTotalAddressed < numOfMusics:
                songsInformation["errors"]["informationError"] = newSongsInformation["errors"]["informationError"] + errors[numOfTotalAddressed:]
            else:
                songsInformation["errors"]["informationError"] = newSongsInformation["errors"]["informationError"]
        elif option == 2:
            songsInformation["metadatas"].extend(newSongsInformation["metadatas"])
            songsInformation["errors"]["illustrationNotFoundError"].extend(newSongsInformation["errors"]["illustrationNotFoundError"])
            songsInformation["errors"]["chartFileNotFoundError"].extend(newSongsInformation["errors"]["chartFileNotFoundError"])
            songsInformation["errors"]["informationError"].extend(newSongsInformation["errors"]["informationError"])
        else:
            songsInformation = newSongsInformation
        #存储歌曲信息
        saveSongsInformation(songsInformation)
        #完全处理完成时删除进度文件
        if os.path.exists(onProcessingSongsInformationFile):
            os.remove(onProcessingSongsInformationFile)
    
    print("处理完成：")
    print("总数 " + str(numOfMusics))
    print("成功处理 " + str(numOfSuccessAddressed))
    print("处理失败 " + str(numOfFailedAddressed))
    print("未处理 " + str(numOfUnhandled))
    print("请立即检查并处理错误歌曲。")
    input("\n按下回车退出")
    exit()



def chartFileNotFoundErrorDealing():
    def checkIfSongExist(songName):
        #检查是否已经存在该歌曲
        existedSongs = [i["name"] for i in songsInformation["metadatas"] ]
        existedSongs.extend([i["name"] for i in songsInformation["errors"]["illustrationNotFoundError"] ])
        existedSongs.extend([i for i in songsInformation["errors"]["informationError"] ])
        for i in existedSongs:
            if i == songName:
                print("检测到重复歌曲")
                return True
        return False
    
    print("""进行谱面未找到错误处理
          此错误是由在查找谱面的过程中，通过bpm与物量无法定位到唯一谱面导致的。
          接下来，对于每个无法确定的谱面，程序将分别生成编号的多个谱面文件，
          你需要手动将他们导入phira（有电脑版）或其他模拟器，手动确定正确的文件，然后在程序中选择。

          注意：此处按下ctrl+c(终止程序快捷键)会触发幽蓝边境异象（雾）并使数据丢失。

          你需要先选择一个文件夹作为谱子保存的地方。
          """)
    choiceD = input("按下回车键开始,输入n返回")
    if choiceD == "n":
        return

    savingPath = selectDir()
    songsInformation = readSongsInformation()
    errors = songsInformation["errors"]["chartFileNotFoundError"]
    numOfErrors = len(errors)

    for index in range(numOfErrors):
        metadata = deepcopy(errors[index])
        music = metadata["music"]
        songName = metadata["name"]
        print("\n处理(%s/%s, %s%%)：%s"%(index+1, numOfErrors, str(int((index+1) * 100 / numOfErrors)), songName ))

        #重复歌曲检测
        if checkIfSongExist(songName):
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
        print("处理成功！")

    print("处理完成")
    songsInformation["errors"]["chartFileNotFoundError"].clear()
    saveSongsInformation(songsInformation)




if __name__ == "__main__":
    print("""欢迎使用本谱面转换程序
    在使用之前，请确保您已经完全阅读github主页上的内容，并已完成程序相关配置。
    如果遇到异常终止，请选择您最后进行的操作，并按提示加载进度文件（仅部分功能支持回档）""")

    print("目前启用难度：")
    for level in handlingLevels:
        print(level, end=" ")

    while True:
        #尝试加载元数据
        songsInformation = readSongsInformation()
        choiceA = input("""
请选择功能：
    【1】 根据本地数据，直接生成全部谱面文件（首次使用请选择）
    【2】 更新本地数据文件（将新版本phi的文件直接追加到相应目录中后，使用此项更新）
    【3】 重置本地数据文件（仅包括谱面元数据）
    【4】 重置本地数据文件（全部）
    【5】 错误谱面处理（有错误存在时务必处理完错误）
请输入一位整数：
              """)
        
        match choiceA:
            case "1":
                #根据本地数据文件直接生成谱面文件
                print("将根据本地数据文件直接生成全部谱面文件")
                print("请确保所有原始文件均已放入相应文件夹")
                choiceB = input("直接按下回车开始，输入n取消。")
                if choiceB == "n":
                    continue

                for metadata in songsInformation["metadatas"]:
                    chartTransform.transform(metadata)
                print("处理完成")

            case "2":
                #更新本地数据文件
                #检查是否有新的音频文件，据此更新本地数据文件并生成对应的新谱面文件
                print("将检查对应目录中是否有新的音频文件，据此更新本地数据文件")
                choiceB = input("直接按下回车开始，输入n取消。")
                if choiceB == "n":
                    continue
                informationHandling(option = 2)

            case "3":
                #重置本地数据文件（仅包括谱面元数据）
                print("注意，原先的歌曲元数据（包括错误信息）将被重置。")
                choiceB = input("直接按下回车开始，输入n取消。")
                if choiceB == "n":
                    continue
                informationHandling(option = 3)
                    
            case "4":
                #重置全部本地数据文件
                print("注意，全部本地数据文件将被重置。")
                choiceB = input("直接按下回车开始，输入n取消。")
                if choiceB == "n":
                    continue

                chartSearch.generatechartFilenameLUT(chartPath)
                illustrationSearch.generateIllustrationLUT()
                informationHandling(option = 3)

            case "5":
                #错误处理
                print("请选择要人工处理的错误")
                print("【1】谱面信息错误：%s个" % str(len(songsInformation["errors"]["informationError"])))
                print("【2】曲绘未找到：%s个" % str(len(songsInformation["errors"]["illustrationNotFoundError"])))
                print("【3】谱面未找到：%s个" % str(len(songsInformation["errors"]["chartFileNotFoundError"])))
                print("【4】忽略现存的谱面信息错误")
                print("注意：任何一类错误，只有当其被完全处理（即“未处理”为0）时，\n  处理结果才会被整合进数据文件，在此之间只会保存处理进度。")
                choiceB = input("请输入一位整数：")
                match choiceB:
                    case "1":
                        informationHandling(option = 1)
                    case "2":
                        illustrationNotFoundErrorHandling()
                    case "3":
                        chartFileNotFoundErrorDealing()
                    case "4":
                        print("""注意，此操作将会将谱面信息错误列表中现存的歌曲全部添加到忽略列表中，不再处理
此操作还会删除已存在的进度文件。
除非你已经筋疲力尽、走投无路，否则不要使用此功能。
想要恢复他们需要自行修改数据文件(./data/ignoredSongs.json)""")
                        print("\n以下文件将会被忽略：")
                        for i in songsInformation["errors"]["informationError"]:
                            print(i)
                        choiceC = input("按下万恶的回车开始，输入n取消。")
                        if choiceC == "n":
                            continue

                        ignoredSongs = readIgnoredSongs()
                        ignoredSongs.extend([i for i in songsInformation["errors"]["informationError"] if i not in ignoredSongs])
                        saveIgnoredSongs(ignoredSongs)
                        songsInformation["errors"]["informationError"].clear()
                        saveSongsInformation(songsInformation)
                        print("已忽略。")

                        if os.path.exists(onProcessingSongsInformationFile):
                            os.remove(onProcessingSongsInformationFile)
                        print("已删除进度文件。")

                    case _:
                        print("输入错误，请重新选择")
                        continue

            case _:
                print("输入错误，请重新选择")
                continue
        
