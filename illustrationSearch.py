import cv2, json, os, time
import numpy as np
import config
import hashlib
from JSONDatabase import JSONDatabase

dataPath = os.path.join(config.rootPath, "data")
lutPath = os.path.join(dataPath, "illustrationFilenameLUT.json")
illustrationsPath = config.paths["illustrationsPath"]

# 初始化 SIFT 检测器
sift = cv2.SIFT_create()
# 打开数据库
db = JSONDatabase(lutPath, "illustrationSearch", compact_encoding=True, enable_non_volatile_cache=False)


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

def getFileMd5(img_bin) -> str:
    """获取文件的 MD5 值"""
    md5 = hashlib.md5()
    md5.update(img_bin)
    return md5.hexdigest()

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
    
    illustrations = [i for i in os.listdir(illustrationsPath) if ".png" in i]
    illustrationLUT = []
    for illustration in illustrations:
        print("正在处理：" + illustration)
        imgPath = os.path.join(illustrationsPath,illustration)
        if os.path.exists(imgPath):
            with open(imgPath,"rb") as f:
                img_bin = f.read()
                img = readImage(imgBin=img_bin)
                if img is None:
                    print("Error: Can't read IMG.")
                    continue
                md5 = getFileMd5(img_bin)
                fv = generateFeatureVector(img).tolist()
        else:
            print("Error: 插图文件不存在!" + imgPath)
            continue
        
        #字典中分别是：文件名、特征向量、MD5、原文件名
        illustrationLUT.append({
            "filename": illustration,
            "fv": fv,
            "md5": md5,
            "old_filename": illustration
        })

    db.set("illustrationLUT", illustrationLUT)
    db.commit()


#更新图像特征码查找表
def updateIllustrationLUT():
    print("更新图像特征码中...")
    new_illustrations = [i for i in os.listdir(illustrationsPath) if ".png" in i]
    num_of_total_illustrations = len(new_illustrations)
    num_of_new_illustrations = 0

    for illustration in new_illustrations:
        imgPath = os.path.join(illustrationsPath,illustration)
        if os.path.exists(imgPath):
            with open(imgPath,"rb") as f:
                img_bin = f.read()
                img = readImage(imgBin=img_bin)
                if img is None:
                    print("Error: Can't read IMG.")
                    continue
                new_md5 = getFileMd5(img_bin)
        else:
            print("Error: 插图文件不存在!" + imgPath)
            continue
        
        existed_files = db.select("illustrationLUT", where={"md5": new_md5})
        if len(existed_files) == 0:
            print("新增：" + illustration)
            num_of_new_illustrations += 1
            fv = generateFeatureVector(img).tolist()
            #字典中分别是：文件名、特征向量、MD5、原文件名
            db.append("illustrationLUT", {
                "filename": illustration,
                "fv": fv,
                "md5": new_md5,
                "old_filename": illustration
            })

        else:
            db.delete("illustrationLUT", where={"md5": new_md5})
            db.append("illustrationLUT", {
                "filename": illustration,
                "fv": existed_files[0]["fv"],
                "md5": new_md5,
                "old_filename": existed_files[0]["filename"]
            })
            
    print("曲绘处理完成")
    print("共计：" + str(num_of_total_illustrations))
    print("新增：" + str(num_of_new_illustrations))
    db.commit()


#查找最相似的图片路径
def illustrationSearch(img1Bin,user_check: bool = False):
    illustrationLUT = db.get("illustrationLUT")
    print("开始查找曲绘……")
    img1 = readImage(imgBin = img1Bin)
    if str(type(img1)) == "<class 'NoneType'>":
        print("查找曲绘错误")
        return None
    
    v1 = generateFeatureVector(img1)
    mostSimilarImg = ["", 0]
    for img2 in illustrationLUT:
        v2 = np.array(img2["fv"])
        #print(img2[0])
        similarity = getVectorSimilarity(v1, v2)
        if similarity > mostSimilarImg[1]:
            mostSimilarImg = [img2["filename"], similarity]
    
    if user_check:
        search_img_path = os.path.join(illustrationsPath, mostSimilarImg[0])
        if not os.path.exists(search_img_path):
            print("Error: 插图文件不存在!" + search_img_path)
            return None
        print("(关闭展示图像的窗口以继续)")
        print("查找到图片：%s 相似度：%s" % (mostSimilarImg[0], mostSimilarImg[1]))
        cv2.imshow("搜索结果", cv2.imread(search_img_path))
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        print("是否使用此图片？(y/n)")
        while True:
            choice = input()
            if choice == "y":
                return mostSimilarImg[0]
            if choice == "n":
                return None
            print("请输入y或n")

    if mostSimilarImg[1] >= 0.30:
        print("查找到图片：%s 相似度：%s" % (mostSimilarImg[0], mostSimilarImg[1]))
        return mostSimilarImg[0]
    else:
        print("相似度过低，查找失败，图片：%s，相似度%s" % (mostSimilarImg[0], mostSimilarImg[1]))



if not db.exists("illustrationLUT"):
    generateIllustrationLUT()



if __name__ == "__main__":
    with open(r"C:\Users\zwt\Desktop\rr.png", "rb") as img1:
        img1Bin = img1.read()
    illustrationSearch(img1Bin)
    with open(r"C:\Users\zwt\Desktop\rr.png", "rb") as img1:
        img1Bin = img1.read()
    illustrationSearch(img1Bin)

