#文件搜索模块
import json, os, config

levels = ('EZ', 'HD', 'IN', 'AT', 'Legacy', 'SP')
lutPath = os.path.join(config.dataPath, "chartFilenameLUT.json")


def getNumber(j): # 我用的版本已经找不到numOfNotes了，所以自己写了物量计算函数
    return sum([
        len(line['notesAbove']) + len(line['notesBelow'])
        for line in j['judgeLineList']
    ])

#生成谱面文件查找表
def generatechartFilenameLUT(rootPath):
    print("正在生成谱面查找列表...")
    global originalChartInfomations
    originalChartInfomations = {}
    originalChartFilenames = os.listdir(rootPath)

    #分等级生成信息，按物量排序，包含谱面文件名和bpm
    for level in levels:
        print("正在处理 " + level + " 难度...")
        levelSpecilizedInfomations = []
        NONIndex = []

        #按难度筛选谱面
        levelSpecilizedFilenames = [i for i in originalChartFilenames if i[:8] == 'Chart_' + level[:2]]

        #生成谱面信息字典，及谱面索引元组列表
        for ordinal in range(len(levelSpecilizedFilenames)):
            filename = levelSpecilizedFilenames[ordinal]
            chartPath = os.path.join(rootPath, filename)
            with open(chartPath, 'r', encoding='utf-8') as f:
                singelChartInfomation = {}
                js = json.load(f)
                NON = str(getNumber(js))
                NONIndex.append(NON) #物量列表
                singelChartInfomation["chart"] = filename
                singelChartInfomation["bpm"] = js["judgeLineList"][0]["bpm"]
                levelSpecilizedInfomations.append((NON, singelChartInfomation))

        #无需排序，格式化索引
        foramtedLevelSpecilizedInfomations = {}
        #生成格式化后的谱面信息字典
        for i in NONIndex:
            numOfNotes = i
            foramtedLevelSpecilizedInfomations[numOfNotes] = []
        numOflevelSpecilizedCharts = len(foramtedLevelSpecilizedInfomations)
        print("  共有 " + str(numOflevelSpecilizedCharts) + " 个谱面")

        for i in levelSpecilizedInfomations:
            numOfNotes = i[0]
            ordinal = i[1]
            foramtedLevelSpecilizedInfomations[numOfNotes].append(ordinal)
        originalChartInfomations[level] = (foramtedLevelSpecilizedInfomations)
    
    print("存储谱面查找列表中...")
    with open(lutPath, 'w', encoding='utf-8') as f:
        json.dump(originalChartInfomations, f, ensure_ascii=False, indent=4)


#谱面查找函数
def searchSingleChartFilename(numOfNotes, level, bpm=None, isErrorDealing=False):
    print(" 开始查找%s谱面……" % level)
    if not isinstance(numOfNotes, str):
        numOfNotes = str(numOfNotes)
    
    if level in originalChartInfomations and numOfNotes in originalChartInfomations[level]:
        charts = originalChartInfomations[level][numOfNotes]
        match len(charts):
            case 1:
                return [0, charts[0]["chart"], charts[0]["bpm"]]
            case 0:
                print("    未找到谱面")
                return [-1]
            case _:
                bpmOfChart = bpm
                
                chartsMatchBpm = []
                if bpmOfChart != None:
                    for chart in charts:
                        if chart["bpm"] >= bpmOfChart - 1 and chart["bpm"] <= bpmOfChart + 1:
                            chartsMatchBpm.append(chart)
                        elif chart["bpm"] >= 2 * bpmOfChart -1 and chart["bpm"] <= 2 * bpmOfChart + 1:
                            chartsMatchBpm.append(chart)
                        elif chart["bpm"] >= 0.5 * bpmOfChart -1 and chart["bpm"] <= 0.5 * bpmOfChart + 1:
                            chartsMatchBpm.append(chart)
                
                match len(chartsMatchBpm):
                    case 1:
                        return [0, chartsMatchBpm[0]["chart"], chartsMatchBpm[0]["bpm"]]
                    case 0:
                        print("    未找到匹配bpm谱面")
                        return [-1]
                    case _:
                        if not isErrorDealing:
                            print("仍然查找到多张铺面，跳过此铺:")
                            for chart in chartsMatchBpm:
                                print(chart["chart"])
                            print("  物量：%s bpm：%s"%(numOfNotes, bpmOfChart))
                            return [1]
                        else:
                            print("进行错误处理")
                            return [2, [i["chart"] for i in chartsMatchBpm]]

    print("未找到谱面")
    return [-1]

def searchChartFilename(charts, isErrorDealing=False):
    numOfLevels = len(charts)
    searchError = []

    #第一次遍历查找，找到能够判断的铺面，以及歌曲的bpm
    for i in range(numOfLevels):
        chart = charts[i]
        numOfNotes = chart["numOfNotes"]
        level = chart["level"]

        chartFileInformation = searchSingleChartFilename(numOfNotes, level)
        if chartFileInformation[0] == 0:
            print("    找到：" + chartFileInformation[1])
            chart["chart"] = chartFileInformation[1]
            bpm = chartFileInformation[2]
        else:
            searchError.append(i)
    
    if len(searchError) == 0:
        return float(bpm)
    elif len(searchError) >= numOfLevels:
        return None
    else:
        #第二次遍历，根据第一次返回的bpm来确定剩余谱面
        print("开始第二轮查找……")
        for i in searchError:
            chart = charts[i]
            numOfNotes = chart["numOfNotes"]
            level = chart["level"]
            chartFileInformation = searchSingleChartFilename(numOfNotes, level, bpm=bpm, isErrorDealing=isErrorDealing)

            if chartFileInformation[0] == 0:
                print("    找到：" + chartFileInformation[1])
                chart["chart"] = chartFileInformation[1]
            elif chartFileInformation[0] == 2 and isErrorDealing:
                chart["possibleCharts"] = chartFileInformation[1]
            elif not level == "Legacy":
                print("查找谱面失败")
                if chartFileInformation[0] == 1:
                    return -1
                else:
                    return None
    
    return float(bpm)



#谱面信息初始化
originalChartsPath = config.inputChartsPath
try:
    originalChartInfomations
except NameError:
    if os.path.exists(lutPath):
        with open(lutPath, 'r', encoding='utf-8') as f:
            originalChartInfomations = json.load(f)
    else:
        print("正在初始化谱面信息")
        generatechartFilenameLUT(originalChartsPath)

if __name__ == "__main__":
    while True:
        numOfNotes = input("请输入物量：")
        level = None
        while level not in levels:
            print("存在以下难度：" + str(levels))
            level = input("请选择上述之一输入：")
        print(searchChartFilename([{"level": level, "numOfNotes": numOfNotes}]))
