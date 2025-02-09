#转铺模块
#转换phigros谱面为outputChart谱面
import orjson, math, os, config
from zipfile import ZipFile

#初始化配置
outputDir = config.paths["outputChartsPath"]
illustrationDir = config.paths["illustrationsPath"]
musicDir = config.paths["musicsPath"]
chartDir = config.paths["inputChartsPath"]
handlingLevels = config.enabledLevels


#音符转换逻辑
typeLut = [1, 4, 2, 3]
def transformNote(originalNote, isAbove):
    type = originalNote["type"]
    postransformType = typeLut[type - 1] #转换为outputChart的type
    time = originalNote["time"]
    startTime = [math.floor(time / 32),
               int(time) % 32,
               32]
    positionX = originalNote["positionX"]*(675.0/9)

    if type == 3:
        holdTime = originalNote["holdTime"]
        endTime = [math.floor((time + holdTime) / 32),
                   int(time + holdTime) % 32,
                   32]
        speed = 1.0
    else:
        speed = originalNote["speed"]
        endTime = startTime
    
    return {
        "above": isAbove,
        "alpha": 255,
        "startTime": startTime,
        "endTime": endTime,
        "isFake": 0,
        "positionX": positionX,
        "size": 1.0,
        "speed": speed,
        "type": postransformType,
        "visibleTime": 999999.0,
        "yOffset": 0.0
    }



def transform(metadata: dict, savingPath=outputDir, isErrorDealing=False) -> (None|int):
    """
    转换谱面，生成pez文件
    返回None为成功
    返回1为音频文件不存在
    返回2为图片文件不存在
    返回3为有谱面文件不存在
    """
    print("开始转换谱面...")
    #读取歌曲元数据
    songName = metadata["name"]
    illustrationPath = os.path.join(illustrationDir, metadata["illustration"])
    musicPath = os.path.join(musicDir, metadata["music"])
    if not os.path.isfile(musicPath):
        print("Error: 音乐文件不存在")
        return 1
    if not os.path.isfile(illustrationPath):
        print("Error: 图片文件不存在")
        return 2

    #依次处理铺面
    has_chart_not_exists = False
    for chart in metadata["charts"]:
        difficulty = str(chart["difficulty"])
        level = chart["level"]
        displayedDifficulty = "%s Lv.%s"%(level, str(int(float(difficulty))))

        if not level in handlingLevels and not isErrorDealing:
            continue
        
        inputChartPath = os.path.join(chartDir, chart["chart"])
        if not os.path.exists(inputChartPath):
            os.mkdir(inputChartPath)
        
        outputName = "%s [%s]"%(metadata["name"], level)
        print("  正在处理 %s 谱面"%level)

        if not os.path.isfile(inputChartPath):
            print("Error: 谱面文件不存在!" + inputChartPath)
            has_chart_not_exists = True
            continue

        with open(inputChartPath,"r",encoding="utf-8") as file_json:
            inputChart = orjson.loads(file_json.read())
            
        #创建rpe格式谱，并写入元数据等
        outputChart = {
            "BPMList": [{"bpm":inputChart["judgeLineList"][0]["bpm"],"startTime":[0,0,1]}],
            "META": {
                "outputChartVersion": 150,
                "level": displayedDifficulty,
                "name": songName,
                "song": songName + ".wav",
                "background": songName + ".png",
                "charter": chart["charter"],
                "composer": metadata["composer"],
                "illustration": metadata["illustrator"],
                "id": "00000000",
                "offset": 0
            },
            "judgeLineGroup": ["Default"],
            "judgeLineList": []
        }

        infotxt = "#\nName: {}\nChart: {}\nPath: {}\nSong: {}\nPicture: {}\nLevel: {}\nComposer: {}\nCharter: {}".format(
            songName,
            outputName + ".json",
            outputChart["META"]["id"],
            outputChart["META"]["song"],
            outputChart["META"]["background"],
            outputChart["META"]["level"],
            outputChart["META"]["composer"],
            outputChart["META"]["charter"])
        infoyaml = 'name: "{}"\nlevel: {}\ndifficulty: {}\nillustrator: "{}"\ntip: "{}"\nintro: "{}"\nformat: null'.format(
            songName,
            displayedDifficulty,
            difficulty,
            metadata["illustrator"],
            "Phigros官谱，仅限个人学习使用",
            "本谱面为phigros官谱，由程序自动生成，仅限个人学习使用，并且请在24小时内删除。严禁传播。")


        #遍历判定线列表，转换数据
        count = 0
        for judgeline in inputChart["judgeLineList"]:
            outputChart["judgeLineList"].append({"Group":0,"Name":"Untitled","Texture":"line.png","eventLayers":[{"alphaEvents":[],"moveXEvents":[],"moveYEvents":[],"rotateEvents":[],"speedEvents":[]}]})

            #判定线不透明度
            for i in judgeline["judgeLineDisappearEvents"]:
                outputChart["judgeLineList"][count]["eventLayers"][0]["alphaEvents"].append(
                    {"easingType":1,
                    "end":i["end"]*255,
                    "endTime":[math.floor(i["endTime"]/32),int(i["endTime"])%32,32],
                    "linkgroup":0,
                    "start":i["start"]*255,
                    "startTime":[math.floor(i["startTime"]/32),int(i["startTime"])%32,32]})
                
            #判定线坐标，根据格式版本不同，分别处理
            if inputChart["formatVersion"] == 3:
                for i in judgeline["judgeLineMoveEvents"]:
                    outputChart["judgeLineList"][count]["eventLayers"][0]["moveXEvents"].append(
                        {"easingType":1,
                        "end": -675 + i["end"] * 1350,
                        "endTime":[math.floor(i["endTime"]/32),int(i["endTime"])%32,32],
                        "linkgroup":0,
                        "start": -675 + i["start"] * 1350,
                        "startTime":[math.floor(i["startTime"]/32),int(i["startTime"])%32,32]})
                    outputChart["judgeLineList"][count]["eventLayers"][0]["moveYEvents"].append(
                        {"easingType":1,
                        "end":-450+i["end2"]*900,
                        "endTime":[math.floor(i["endTime"]/32),int(i["endTime"])%32,32],
                        "linkgroup":0,
                        "start":-450+i["start2"]*900,
                        "startTime":[math.floor(i["startTime"]/32),int(i["startTime"])%32,32]})
                    
            elif inputChart["formatVersion"] == 1:
                #一代远古官谱
                for i in judgeline["judgeLineMoveEvents"]:
                    outputChart["judgeLineList"][count]["eventLayers"][0]["moveXEvents"].append(
                        {"easingType":1,
                        "end":-450+(i["end"]//1000)/880*900,
                        "endTime":[math.floor(i["endTime"]/32),int(i["endTime"])%32,32],
                        "linkgroup":0,
                        "start":-450+(i["start"]//1000)/880*900,
                        "startTime":[math.floor(i["startTime"]/32),int(i["startTime"])%32,32]})
                    outputChart["judgeLineList"][count]["eventLayers"][0]["moveYEvents"].append(
                        {"easingType":1,
                        "end":-450+(i["end"]%1000)/520*900,
                        "endTime":[math.floor(i["endTime"]/32),int(i["endTime"])%32,32],
                        "linkgroup":0,
                        "start":-450+(i["start"]%1000)/520*900,
                        "startTime":[math.floor(i["startTime"]/32),int(i["startTime"])%32,32]})
                    
            #判定线旋转
            for i in judgeline["judgeLineRotateEvents"]:
                outputChart["judgeLineList"][count]["eventLayers"][0]["rotateEvents"].append(
                    {"easingType":1,
                    "end":-i["end"],
                    "endTime":[math.floor(i["endTime"]/32),int(i["endTime"])%32,32],
                    "linkgroup":0,
                    "start":-i["start"],
                    "startTime":[math.floor(i["startTime"]/32),int(i["startTime"])%32,32]})
                
            #判定线速度
            for i in judgeline["speedEvents"]:
                outputChart["judgeLineList"][count]["eventLayers"][0]["speedEvents"].append(
                    {"end":i["value"]/(5/3)*7.5,
                    "endTime":[math.floor(i["startTime"]/32/32),int(i["startTime"]/32)%32,32],
                    "linkgroup":0,
                    "start":i["value"]/(5/3)*7.5,
                    "startTime":[math.floor(i["startTime"]/32),int(i["startTime"])%32,32]})
                
            #音符转换
            outputChart["judgeLineList"][count]["isCover"] = 1
            outputChart["judgeLineList"][count]["notes"] = []
            for originalNote in judgeline["notesAbove"]:
                postansformNote = transformNote(originalNote, 1)
                outputChart["judgeLineList"][count]["notes"].append(postansformNote)
            for originalNote in judgeline["notesBelow"]:
                postansformNote = transformNote(originalNote, 2)
                outputChart["judgeLineList"][count]["notes"].append(postansformNote)
            
            #计算音符数量
            if not ("numOfNotes" in judgeline): # 解决了部分谱面没有 numOfNotes 的问题
                outputChart["judgeLineList"][count]["numOfNotes"] = len(judgeline["notesAbove"]) + len(judgeline["notesBelow"])
            else:
                outputChart["judgeLineList"][count]["numOfNotes"] = judgeline["numOfNotes"]
            count+=1

        #打包谱面
        if isErrorDealing:
            outputZipFilePath = os.path.join(savingPath, outputName + ".pez")
        else:
            if not os.path.exists(os.path.join(savingPath, chart["level"])):
                os.makedirs(os.path.join(savingPath, chart["level"]))
            outputZipFilePath = os.path.join(savingPath, chart["level"], outputName + ".pez")

        with ZipFile(outputZipFilePath, 'w') as zipf:
            #将将元数据写入info.txt和info.yaml
            zipf.writestr("info.txt",infotxt)
            zipf.writestr("info.yml",infoyaml)
            zipf.writestr(outputName + ".json", orjson.dumps(outputChart))
            zipf.write(illustrationPath, outputChart["META"]["background"])
            zipf.write(musicPath, outputChart["META"]["song"])

    print("谱面转换完成！")

    if has_chart_not_exists:
        return 3
