#从主程序调用，在特定网址搜索传入的歌曲名，抓取歌曲元数据
import requests, json, re, config
from lxml import html, etree

requests.urllib3.disable_warnings() #不知道为什么我这里ssl证书老是有问题，所以忽略警告

url = 'https://phigros.fandom.com/wiki/Special:Search'
proxy = {
    'https': 'http://127.0.0.1:1081',
}

#获取页面内容
def getElements(url, params={}):
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
    
def fileBinTextGet(url):
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
        tree = getElements(matchedLink)
        if tree is None:
            print("Error：页面内容为空")
            return None
        
        songName = tree.xpath('string(//table[@class="wikitable centre-text"]/tbody/tr[1]/th/text())').replace("\n", "")
        composer = tree.xpath('string(//table[@class="wikitable centre-text"]//tr[th[contains(text(), "Artist")]]/td[1])').replace("\n", "")

        durationText = tree.xpath('string(//table[@class="wikitable centre-text"]//th[contains(text(), "Duration")]/following-sibling::td[1]/text())').replace("\n", "")
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
    pattern = r'[()（）\[\]【】. ,-]'
    banedWords = ["phigros", "ver", "单曲精选"]
    items = re.split(pattern, songName.lower())
    cleanedItems = [i for i in items 
                    if i not in banedWords 
                    and i != '']

    for i in range(len(cleanedItems)):
        searchWord = " ".join(cleanedItems[0:len(cleanedItems)-i])
        print("搜索中：" + searchWord)
        htmltreeOfSearchResult = getElements(url, {'query': searchWord})
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
    
    print("未找到搜索到匹配项")
    return None

if __name__ == "__main__":
    songname = input("输入歌名进行查询")
    print(searchSong(songname))