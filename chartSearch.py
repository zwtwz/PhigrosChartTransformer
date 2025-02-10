#文件搜索模块
import orjson, os, hashlib
from copy import deepcopy

import config
import JSONDatabase
from chartTransform import chart_transform

input_charts_path = config.paths["inputChartsPath"]
levels = ('EZ', 'HD', 'IN', 'AT', 'Legacy', 'SP')
lutPath = os.path.join(config.paths["dataPath"], "chartFilenameLUT.json")

db = JSONDatabase.JSONDatabase(lutPath, "chartSearch", enable_non_volatile_cache=False)

def getFileMd5(img_bin) -> str:
    """获取文件的 MD5 值"""
    md5 = hashlib.md5()
    md5.update(img_bin)
    return md5.hexdigest()

def get_number(j): # 我用的版本已经找不到numOfNotes了，所以自己写了物量计算函数
    return sum([
        len(line['notesAbove']) + len(line['notesBelow'])
        for line in j['judgeLineList']
    ])


#生成谱面文件查找表
def generate_chart_filename_lut(input_charts_path):
    print("正在生成谱面查找列表...")
    original_chart_filename_list = os.listdir(input_charts_path)

    #分等级生成信息，按物量排序，包含谱面文件名和bpm
    for level in levels:
        print(f"正在处理 {level} 难度...")

        formatted_level_specilized_infomations = []  #创建列表，存储最终格式的物量与谱面信息列表

        # 按难度筛选谱面
        level_specilized_filenames = [fn for fn in original_chart_filename_list if fn.startswith('Chart_' + level[:2])]

        # 生成谱面信息字典及谱面索引元组列表
        for ordinal, filename in enumerate(level_specilized_filenames):
            chart_path = os.path.join(input_charts_path, filename)
            try:
                with open(chart_path, 'rb') as f:
                    f_bin = f.read()
                    js = orjson.loads(f_bin.decode("utf-8"))
                    single_chart_information = {
                        "chart": filename,
                        "num_of_notes": get_number(js),
                        "bpm": js["judgeLineList"][0]["bpm"],
                        "md5": getFileMd5(f_bin),
                        "old_filename": filename
                    }
                    formatted_level_specilized_infomations.append((single_chart_information))
            except FileNotFoundError:
                print(f"  文件 {chart_path} 不存在")
                continue
            except orjson.JSONDecodeError:
                print(f"  文件 {chart_path} 解析失败")
                continue

        # 格式化索引
        num_of_level_specilized_charts = len(formatted_level_specilized_infomations)
        print(f"  共有 {num_of_level_specilized_charts} 个谱面")

        db.set(level, formatted_level_specilized_infomations)
    
    print("存储谱面查找列表中...")
    db.commit()


#更新谱面文件查找表
def update_chart_filename_lut(input_charts_path):
    print("正在更新谱面查找列表...")
    original_chart_filename_list = os.listdir(input_charts_path)

    #分等级生成信息，按物量排序，包含谱面文件名和bpm
    for level in levels:
        print(f"正在处理 {level} 难度...")
        num_of_updated_charts = 0
        num_of_new_charts = 0

        # 按难度筛选谱面
        level_specilized_filenames = [fn for fn in original_chart_filename_list if fn.startswith('Chart_' + level[:2])]

        # 生成谱面信息字典及谱面索引元组列表
        for ordinal, filename in enumerate(level_specilized_filenames):
            chart_path = os.path.join(input_charts_path, filename)
            try:
                with open(chart_path, 'rb') as f:
                    f_bin = f.read()
                    js = orjson.loads(f_bin.decode("utf-8"))
                    new_md5 = getFileMd5(f_bin)
                    old_info = db.select(level, where={"md5": new_md5})

                    if len(old_info) == 0:
                        # 插入新谱面
                        print("  新增谱面: " + filename)
                        db.append(level, {
                            "chart": filename,
                            "num_of_notes": get_number(js),
                            "bpm": js["judgeLineList"][0]["bpm"],
                            "md5": new_md5,
                            "old_filename": filename
                        })
                        num_of_new_charts += 1
                    else:
                        # 更新谱面
                        db.modify(level, {
                            "chart": filename,
                            "num_of_notes": get_number(js),
                            "bpm": js["judgeLineList"][0]["bpm"],
                            "md5": new_md5,
                            "old_filename": old_info[0]["chart"]
                        }, where={"md5": new_md5})
                        num_of_updated_charts += 1

            except FileNotFoundError:
                print(f"  文件 {chart_path} 不存在")
                continue
            except orjson.JSONDecodeError:
                print(f"  文件 {chart_path} 解析失败")
                continue

        # 输出结果
        print(f"  共更新 {num_of_updated_charts} 个谱面")
        print(f"  共新增 {num_of_new_charts} 个谱面")
    
    print("存储谱面查找列表中...")
    db.commit()


#谱面查找函数
def searchSingleChartFilename(numOfNotes, level, bpm=None, isErrorDealing=False):
    print(" 开始查找%s谱面……" % level)
    if not isinstance(numOfNotes, int):
        numOfNotes = int(numOfNotes)
    
    if db.exists(level):
        charts = db.select(level, where={"num_of_notes": numOfNotes})
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
                            print("查找到多张铺面:")
                            for chart in chartsMatchBpm:
                                print(chart["chart"])
                            print("  物量：%s bpm：%s"%(numOfNotes, bpmOfChart))
                            return [-2, [i["chart"] for i in chartsMatchBpm]]
    print("未找到谱面")
    return [-1]


def searchChartFilename(charts):
    """
    查找谱面，传入charts引用，补充数据
    返回正数：此数据为歌曲bpm
    返回-2：找不到谱面
    返回-1：存在多张谱面，需要手动选择
    """
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
    
    result = 1024  # 结果优先级为越小越优先，因此需要选一个很大的值
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
            chartFileInformation = searchSingleChartFilename(numOfNotes, level, bpm=bpm)

            if chartFileInformation[0] == 0:
                print("    找到：" + chartFileInformation[1])
                chart["chart"] = chartFileInformation[1]
            elif chartFileInformation[0] == -2:
                chart["possibleCharts"] = chartFileInformation[1]
                chart["chart"] = ""
                if -1 < result:
                    result = -1
            elif not level == "Legacy":
                print("查找谱面失败")
                chart["chart"] = ""
                if chartFileInformation[0] == -1:
                    result = -2
    
    if float(bpm) < result:
        result = float(bpm)
    return result


def get_chart(metadata: dict, mode: int = 0, save_path: str = "") -> (None | int):
    """
    谱面搜索，传入metadata引用，补充数据\n
    mode: 0 自动模式\n
    mode: 1 手动选择模式\n
    返回None：操作成功\n
    返回-1：未找到谱面\n
    返回-2：存在多张谱面，需要手动选择
    """
    search_result_bpm = searchChartFilename(metadata["charts"])
    #部分曲子实际上没有Legacy难度，故删除之。
    for i in range(len(metadata["charts"])):
        chart = metadata["charts"][i]
        if chart["level"] == "Legacy" and chart["chart"] == "":
            del metadata["charts"][i]
    del i
    
    if search_result_bpm > 0:
        metadata["bpm"] = search_result_bpm
        return None
    
    elif search_result_bpm == -1:
        #多个谱面处理
        if not mode == 1:
            return -2
        for chart in [item for item in metadata["charts"] if item["chart"] == ""]:
            print("  处理 %s 难度" % chart["level"])
            possibleCharts:list = chart["possibleCharts"]

            #先检查是否有选项谱面已被选择
            def filter_func(x: dict):
                if "charts" in x.keys():
                    return any([y["chart"] in possibleCharts for y in x["charts"]])
                else:
                    return False
            charts_include_options = db.select("metadatas",
                                         where=filter_func,
                                         fields=["charts"])  # 返回 [{charts:[{chart: "chart1"}}...] 结构
            unselected_options = possibleCharts.copy()  # 筛选没用过的谱面
            for item in charts_include_options:
                if not "charts" in item.keys() or len(item["charts"]) == 0:
                    continue
                for item2 in item["charts"]:
                    if item2["chart"] in unselected_options:
                        unselected_options.remove(item2["chart"])
            
            if len(unselected_options) == 1:
                print("  自动选择：" + unselected_options[0])
                chart["chart"] = unselected_options[0]
                continue

            #手动处理
            #将“难度”替换为“选项n”，生成“选项元数据”，其中仅charts字段不同。
            under_processing_metadata = deepcopy(metadata)
            del under_processing_metadata["charts"]
            under_processing_charts = []
            numOfpossibleCharts = len(possibleCharts)

            for i in range(numOfpossibleCharts):
                possibleChart = possibleCharts[i]
                onProcessingChart = deepcopy(chart)
                onProcessingChart["level"] = "选项" + str(i + 1)
                onProcessingChart["chart"] = possibleChart
                under_processing_charts.append(onProcessingChart)

            under_processing_metadata["charts"] = under_processing_charts

            chart_transform(under_processing_metadata, save_path, isErrorDealing=True)
            while True:
                try:
                    choice = int(input("请选择要使用的文件，并输入整数：")) - 1
                except:
                    print("请输入整数!")
                else:
                    break
            chart["chart"] = possibleCharts[choice]
    else:
        return -1



#谱面信息初始化
if not all([db.exists(level) for level in levels]):
    generate_chart_filename_lut(input_charts_path)

if __name__ == "__main__":
    while True:
        numOfNotes = input("请输入物量：")
        level = None
        while level not in levels:
            print("存在以下难度：" + str(levels))
            level = input("请选择上述之一输入：")
        #print(searchChartFilename([{"level": level, "numOfNotes": numOfNotes}]))
        bpm = float(input("请输入BPM："))
        print(searchSingleChartFilename(numOfNotes, level, bpm))
