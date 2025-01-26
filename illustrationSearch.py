import cv2, json, os
import numpy as np
import config

dataPath = os.path.join(config.rootPath, "data")
lutPath = os.path.join(dataPath, "illustrateFilenameLUT.json")
illustrationsPath = config.illustrationsPath

def readImage(path=None, imgBin=None):
    # 读取图像
    if path == None and imgBin == None:
        print("读取图像失败：传参错误")
        return None
    if path != None:
        with open(path, "rb") as f:
            imgBin = f.read()
    
    farray = np.frombuffer(imgBin, np.uint8)
    img = cv2.imdecode(farray, cv2.IMREAD_COLOR)

    if img is None:
        print("图像未成功加载，请检查文件路径或图像是否存在。")
        return None
    imgShape = img.shape
    if imgShape[0] != 540:
        img = cv2.resize(img,(1024,540), interpolation=cv2.INTER_CUBIC)
        
    return img


#计算相似度
def getVectorSimilarity(descriptors1, descriptors2):
    # 创建 FLANN 匹配器
    descriptors1 = descriptors1.astype(np.float32)
    descriptors2 = descriptors2.astype(np.float32)

    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)  # 使用 KD 树
    search_params = dict(checks=50)  # 检索时的迭代次数
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    # 匹配描述符
    matches = flann.knnMatch(descriptors1, descriptors2, k=2)

    # 筛选匹配点
    good_matches = []
    ratio_thresh = 0.7  # 比值阈值
    for m, n in matches:
        if m.distance < ratio_thresh * n.distance:
            good_matches.append(m)

    # 输出筛选后匹配点的数量
    #print(f"筛选后匹配点数：{len(good_matches)}")
    # 计算平均匹配距离
    if good_matches:
        similarity = len(good_matches) / len(descriptors1)
    else:
        similarity = 0

    return similarity



#生成特征向量
def generateFeatureVector(img):
    # 检查数据类型
    if img.dtype != 'uint8':
        image = (image * 255).astype('uint8')
    # 检测描述符
    _, descriptors = sift.detectAndCompute(img, None)

    #以4为步长求平均
    simplifiedDescriptions = []
    for vector in descriptors:
        splitedVectorsList = [vector[i: i+3] for i in range(0, 127, 4)]
        avgVector = [sum(vector)/4 for vector in splitedVectorsList]
        simplifiedDescriptions.append(avgVector)
    return descriptors


#生成图像特征码查找表
def generateIllustrationLUT():
    print("生成图像特征码中...")
    global illustrationLUT
    illustrationLUT = []
    illustrations = [i for i in os.listdir(illustrationsPath) if ".png" in i]

    for illustration in illustrations:
        img = readImage(os.path.join(illustrationsPath,illustration))
        if img is None:
            print("Error: Can't read IMG.")
            continue

        fv = generateFeatureVector(img).tolist()
        illustrationLUT.append([illustration, fv])

    with open(lutPath, "w", encoding="utf-8") as lutFile:
        lutFile.write(json.dumps(illustrationLUT))


#查找最相似的图片路径
def illustrationSearch(img1Bin):
    print("开始查找曲绘……")
    img1 = readImage(imgBin = img1Bin)
    if str(type(img1)) == "<class 'NoneType'>":
        print("查找曲绘错误")
        return None
    
    v1 = generateFeatureVector(img1)
    mostSimilarImg = ["", 0]
    for img2 in illustrationLUT:
        v2 = np.array(img2[1])
        #print(img2[0])
        similarity = getVectorSimilarity(v1, v2)
        if similarity > mostSimilarImg[1]:
            mostSimilarImg = [img2[0], similarity]
    
    if mostSimilarImg[1] >= 0.4:
        print("查找到图片：%s 相似度：%s" % (mostSimilarImg[0], mostSimilarImg[1]))
        return mostSimilarImg[0]
    else:
        print("相似度过低，查找失败，图片：%s，相似度%s" % (mostSimilarImg[0], mostSimilarImg[1]))



# 初始化 SIFT 检测器
sift = cv2.SIFT_create()

if not os.path.exists(dataPath):
    os.makedirs(dataPath)

if not os.path.exists(lutPath):
    generateIllustrationLUT()
else:
    with open(lutPath, "r", encoding="utf-8") as lutFile:
        try:
            illustrationLUT = json.load(lutFile)
        except:
            lutFile.close()
            os.remove(lutPath)
            generateIllustrationLUT()



if __name__ == "__main__":
    with open(r"C:\Users\zwt\Desktop\rr.png", "rb") as img1:
        img1Bin = img1.read()
    illustrationSearch(img1Bin)

