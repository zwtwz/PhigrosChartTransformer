#从主程序调用，在特定网址搜索传入的歌曲名，抓取歌曲元数据
import requests, re, config, hashlib, os
from lxml import html
from typing import Callable
from songRecognize import songRecognize

musics_path = config.paths["musicsPath"]
enabled_levels = config.enabledLevels

if "SP" in enabled_levels:
    #将SP提到最前，满足查找谱面时的顺序
    enabled_levels.remove("SP")
    enabled_levels.insert(0, "SP")

requests.urllib3.disable_warnings() #不知道为什么我这里ssl证书老是有问题，所以忽略警告

url = 'https://phigros.fandom.com/wiki/Special:Search'
proxy = {
    'https': 'http://127.0.0.1:1081',
}


def get_file_md5(file_path) -> str:
    """获取文件的 MD5 值"""
    with open(file_path, 'rb') as f:
        md5 = hashlib.md5()
        md5.update(f.read())
        return md5.hexdigest()

#获取页面内容
def get_elements(url, params={}):
    tryingTime = 0
    while tryingTime < 3:
        try:
            response = requests.get(url, params, verify=False, proxies=proxy)
        except BaseException as e:
            print(e)
        else:
            break
        finally:
            tryingTime += 1
    if not tryingTime < 3:
        print('获取页面失败')
        return None
    
    response.encoding = 'utf-8'
    return html.fromstring(response.text)
    
def get_web_file_bin(url):
    try:
        result = requests.get(url).content
    except:
        return None
    if not result == "":
        return result
    else:
        return None

def metadataGrab(matchedLink):
    try:
        #谱面信息获取
        #获取页面内容并读取基本信息
        tree = get_elements(matchedLink)
        if tree is None:
            print("Error：页面内容为空")
            return None
        
        songName = tree.xpath('string(//table[@class="wikitable centre-text"]/tbody/tr[1]/th/text())').replace("\n", "")
        composer = tree.xpath('string(//table[@class="wikitable centre-text"]//tr[th[contains(text(), "Artist")]]/td[1])').replace("\n", "")

        durationText:str = tree.xpath('string(//table[@class="wikitable centre-text"]//th[contains(text(), "Duration")]/following-sibling::td[1]/text())').replace("\n", "")
        durationList = re.split(":", durationText.replace(" ", ""))
        try:
            duration = int(durationList[0]) * 60 + int(durationList[1])
        except:
            print("Error: 页面格式不匹配")
            return None

        illustrator = tree.xpath('string(//table[@class="wikitable centre-text"]//th[contains(text(), "Illustration")]/following-sibling::td[1]/text())').replace("\n", "")

        illustrationUrl = tree.xpath('string(//table[contains(@class,"wikitable centre-text")]/tbody[1]/tr[2]/td[1]/a[1]/@href)')

        #获取难度列表，判断谱面类型，分类处理
        htmlOflevels = tree.xpath('//table[@class="wikitable centre-text"]//tr[th[contains(text(), "Level")]]/td[not(contains(text(), "Level"))]')
        htmlOfNOC = tree.xpath('//table[@class="wikitable centre-text"]//tr[th[contains(text(), "Note count")]]/td[not(contains(text(), "Note count"))]')
        isWithLegacy = False if len(tree.xpath('//table[@class="wikitable centre-text"]//tr[th[contains(text(), "Level")]]/td[not(contains(text(), "Level"))]/div')) == 0 else True
        numOfLevels = len(htmlOflevels)

        if numOfLevels == 0:
            #如果难度列表为空，检查是否为SP谱面
            gatewaySong = tree.xpath('string(//table[@class="wikitable centre-text"]//th[contains(text(), "Gateway song")]/following-sibling::td[1])').replace("\n", "")
            if gatewaySong == "":
                print("Error: 谱面信息为空")
                return None
            else:
                #如果存在Gateway song，则为SP谱面
                difficultys = ["SP"]
                levels = ["17"]
                NOCs = [htmlOfNOC[0].text_content().replace("\n", "")]
                charters = [tree.xpath('string(//table[@class="wikitable centre-text"]//th[contains(text(), "Charter")]/following-sibling::td[1])').replace("\n", "")]
        else:
            #如果谱面名中不包含"Introduction", 则为普通谱面
            if not "Introduction" in songName:
                difficultys = ["EZ", "HD", "IN"]
                if numOfLevels > 3 and not "Random" in songName:
                    difficultys.append("AT")
                if isWithLegacy:
                    difficultys.append("Legacy")
            else:
                #新手指引只有EZ难度
                difficultys = ["EZ"]
            
            #获取每难度的谱面信息
            levels, NOCs, charters = [], [], []
            for i in range(numOfLevels - 1 if isWithLegacy else numOfLevels):
                levels.append(htmlOflevels[i].text_content().replace("\n", ""))
                NOCs.append(htmlOfNOC[i].text_content().replace("\n", ""))
            
            #如果存在LE难度, 获取IN, Legacy难度谱面信息
            if isWithLegacy:
                htmlOfLevelsOfCompoesdInAndLegacy = [i for i in htmlOflevels if i.text == None][0]
                htmlOfNOCsOfCompoesdInAndLegacy = [i for i in htmlOfNOC if i.text == None][0]
                #print(etree.tostring(htmlOflevels[numOfLevels - 1], pretty_print=True).decode())
                #print(htmlOflevels[numOfLevels - 1].xpath('./div/div/text()'))
                levels.append(htmlOfLevelsOfCompoesdInAndLegacy.xpath('./div/div/text()')[0])
                levels.append(htmlOfLevelsOfCompoesdInAndLegacy.xpath('./div/div/text()')[1])
                NOCs.append(htmlOfNOCsOfCompoesdInAndLegacy.xpath('./div/div/text()')[0])
                NOCs.append(htmlOfNOCsOfCompoesdInAndLegacy.xpath('./div/div/text()')[1])
            
            for difficulty in difficultys:
                charters.append(tree.xpath('string(//table[@class="wikitable centre-text"]//th[contains(text(), "Chart design") and contains(text(), "' + difficulty + '")] /following-sibling::td[1])').replace("\n", ""))

        charts = []
        for i in range(len(difficultys)):
            chart = {
                    "level": difficultys[i],    #fandom页面和phira中难度等级和定数是反的，所以换一下
                    "difficulty": levels[i],
                    "numOfNotes": NOCs[i],
                    "chart": "",
                    "charter": charters[i]
                }
            if chart["level"] in enabled_levels:
                charts.append(chart)

        metadata = {
            "name": songName,
            "composer": composer,
            "illustrator": illustrator,
            "illustration": "",
            "illustrationUrl": illustrationUrl,
            "music": "",
            "duration": duration,
            "bpm": "",
            "charts": charts
        }

        #检查空元素数量
        if len([emptyContext for emptyContext in metadata if metadata[emptyContext] == "" or metadata[emptyContext] == None]) == 3:
            return metadata
        else:
            print("Error: 元数据存在空元素")
            return None
    
    except BaseException as e:
        print("Error: 获取元数据失败，未知错误：")
        print(e)
        return None


def searchSong(songName):
    #对歌名进行搜索，每次检查前五个是否匹配
    #如果无匹配项，尝试依次删除首位字符搜索，直到字符串过短
    #歌名关键字剔除特殊符号和'phigros'等无关词汇
    print("开始抓取歌曲元数据……")
    pattern = r'[()（）\[\]【】. ,-/]'
    banedWords = ["phigros", "ver", "单曲精选"]
    items = re.split(pattern, songName.lower())
    cleanedItems = [i for i in items 
                    if i not in banedWords 
                    and i != '']

    for i in range(len(cleanedItems) * 2):
        if i < len(cleanedItems):
            #逐个向前删除关键词匹配
            searchWord = " ".join(cleanedItems[0:len(cleanedItems)-i])
        else:
            #逐个向后删除关键词匹配
            searchWord = " ".join(cleanedItems[i - len(cleanedItems):len(cleanedItems)])
            
        print("搜索中：" + searchWord)
        htmltreeOfSearchResult = get_elements(url, {'query': searchWord})
        if htmltreeOfSearchResult is not None:
            elements = htmltreeOfSearchResult.xpath('//*[@id="mw-content-text"]/section/div/div[2]/ul/li[*]/article/h3/a')
        else:
            return None

        #取搜索结果前3尝试匹配
        for ordinalOfResult in range(3 if len(elements) > 3 else len(elements)):
            element = elements[ordinalOfResult]
            title = element.text_content().lower()
            for bannedWord in banedWords: #剔除无关词汇
                title = title.replace(bannedWord, "")

            for keyword in cleanedItems:
                if keyword in title:    #如果歌名关键字在搜索结果中，则认为匹配
                    matchedLink = element.get('href')
                    print("匹配：" + matchedLink)
                    result = metadataGrab(matchedLink)
                    if result is not None:
                        return result


def get_metadata(mode: int = 0,
                  duration_of_music_file: int = 0,
                  music_file_name: str = "",
                  after_get_song_name: Callable = lambda *a, **k: None) -> dict:
    """
    获取谱面元数据\n
    mode: 0 全自动听歌识曲\n
    mode: 1 手动输入网址\n
    mode: 2 手动输入全部元数据\n
    after_get_song_name: 手动输入曲名后执行的函数\n
    music_file_name: 本地歌曲文件名\n
    duration_of_music_file: 本地文件歌曲时长\n
    status: 0:未处理 1:已处理 2:异常\n
        [谱面信息，曲绘，谱面文件]
    """
    error_metadata = {
        "music": music_file_name,
        "old_music_file_name": music_file_name,
        "md5": get_file_md5(os.path.join(musics_path, music_file_name)),
        "status": [2,0,0]
    }

    if mode == 0:
        #自动识别
        recognized_song_name = songRecognize()
        after_get_song_name()
        if recognized_song_name is None:
            return error_metadata.copy()
        metadata = searchSong(recognized_song_name)
        if metadata is None:
            return error_metadata.copy()
        
        #歌曲时长匹配检测
        if not metadata["duration"] in range(duration_of_music_file-3, duration_of_music_file+3) :
            print("歌曲时长不匹配:")
            print(" 本地文件: " + str(duration_of_music_file))
            print(" wiki记录: " + str(metadata["duration"]))
            return error_metadata.copy()
        
    elif mode == 1:
        #手动输入网址
        url = input("请输入wiki链接，留空跳过：")
        after_get_song_name()
        if url == "":
            print("Error: 跳过")
            return error_metadata.copy()
        metadata = metadataGrab(url)
        if metadata == None:
            print("Error: 获取元数据失败")
            return error_metadata.copy()
    
    elif mode == 2:
        #手动输入全部元数据模式
        while True:
            song_name = input("曲名（留空跳过此歌曲）：")
            after_get_song_name()
            if song_name == "":
                print("Error: 跳过此歌曲")
                metadata = None
                break
            metadata = {
                "name": song_name,
                "composer": input("曲师(Artist)："),
                "illustrator": input("绘师(Illustration)："),
                "illustration": "",
                "illustrationUrl": input("曲绘图片的在线链接（可以在图片上右键，复制图片链接）："),
                "duration": 0,
                "bpm": "",
                "charts": None
            }

            charts = []
            last_charter = "佚名"
            for level in enabled_levels:
                print("填写%s难度谱面信息：" % level)
                difficulty = input("  谱面定数(Level)（留空跳过此难度）：")
                if difficulty == "":
                    continue
                else:
                    difficulty = float(difficulty)
                
                charter = input("  谱师(Chart design)（留空将设置为: %s ）\n    请输入：" % last_charter)
                if charter == "":
                    charter = last_charter
                else:
                    last_charter = charter

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
        if metadata is None:
            return error_metadata.copy()

    metadata.update({
        "music": music_file_name,
        "old_music_file_name": music_file_name,
        "md5": get_file_md5(os.path.join(musics_path, music_file_name)),
        "status": [1,0,0]
    })

    #非法字符剔除
    pattern = r'[<>:"/\\|?*\x00-\x1F]'
    metadata["name"] = re.sub(pattern, "_", metadata["name"])
    pattern = r'"'
    metadata["illustrator"] = re.sub(pattern, "_", metadata["illustrator"])
    return metadata


if __name__ == "__main__":
    songname = input("输入歌名进行查询")
    print(searchSong(songname))