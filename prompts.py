"""存储大段的提示词"""

进行歌曲信息错误处理 = """
进行歌曲信息错误处理
    此错误包含4种情况：
        1. 听歌识曲失败
        2. 没有搜到歌曲信息
        3. wiki记录的歌曲时长 与 本地音频文件时长 之间 误差超过范围
        4. wiki记录的谱面物量有误，导致搜不到相应谱子
"""

进行曲绘未找到错误处理 = """
进行曲绘未找到错误处理
    请选择处理方式：
        a. 直接下载网络曲绘（分辨率较低）
        b. 手动选择曲绘文件

    注意：在b模式下，在文件选择窗口点击取消会跳过歌曲
        在b模式下，会自动播放歌曲，请注意音量。
        如果发现没有选择曲绘的窗口，请检查其是否被挡在其他窗口后。（此窗口无任务栏图标）\n
"""

进行谱面未找到错误处理 = """
进行谱面未找到错误处理
此错误是由在查找谱面的过程中，通过bpm与物量无法定位到唯一谱面导致的。
接下来，对于每个无法确定的谱面，程序将分别生成编号的多个谱面文件，
你需要手动将他们导入phira（有电脑版）或其他模拟器，手动确定正确的文件，然后在程序中选择。

注意：此处按下ctrl+c(终止程序快捷键)会触发幽蓝边境异象（雾）并使数据丢失。

你需要先选择一个文件夹作为谱子保存的地方。
（没有弹出窗口？检查一下是不是被别的窗口挡住了）\n
"""

进行重置或新生成 = """
将全新生成谱面信息
注意，原先的歌曲元数据（包括错误信息）将被重置。
"""

请选择信息收集方式 = """
请选择信息收集方式：
    a. 在给出的wiki中手动搜索到所听到的歌曲，然后将页面地址输入程序，由程序抓据
    b. 手动输入所听到的歌曲的所有数据（非必要不要用，比较受罪。）

    注意：a选项中输入只有一次机会，请小心不要打错字，否则可能引起幽蓝边境异象(雾)
          对于自动、半自动处理无法解决的问题，请尝试手动解决。
          对于任意歌曲，其歌名在数据库中必须唯一，否则会被自动忽略（不管哪种模式）
            像random这种（这曲子肯定会出现在错误列表里），只能用手动收集信息解决，
            歌名需要标清楚是哪个谱，如 random[M]
          *会自动播放歌曲，请注意音量。\n
"""

半自动模式提示词 = """
    请在浏览器中打开此地址(必须为此地址)：https://phigros.fandom.com/wiki/Special:Search

    接下来，你将会听到音乐播放
    请在上述页面中搜索你听到的音乐，并将其wiki页面对应的地址复制下来，然后输入到本程序中。
    tips.你可以通过打开对应wiki并复制地址栏地址，也可以通过直接右键超链接，复制wiki链接地址获取地址。

    例如：
    你听到“登，登登登，登登登，等登邓灯蹬瞪凳磴嶝噔僜墱澄”
    所以，你在搜索框搜索“Rrhar'il”
    你找到了对应的搜索结果，是第一条，其标题链接写着：Rrhar'il
    你右键了那个链接，点击了“复制链接地址”，复制了如下链接地址：https://phigros.fandom.com/wiki/Rrhar'il
    你返回终端，在光标闪烁的位置右键点击，将其粘贴在程序内，然后按下了回车键。\n
"""

全手动模式提示词 = """
    请任意找一个提供歌曲信息的地方
    本程序默认自动采集fandom wiki的数据，但是其中包含一些错误，
    为了进行交叉验证，不建议在此处使用fandom wiki。
    推荐wiki：萌娘百科，https://zh.moegirl.org.cn/Phigros/谱面信息\n

    接下来，你将会听到音乐播放
    你需要根据音乐回答以下问题：
        曲名 曲师 绘师 歌曲持续时间 曲绘图片的在线链接
        每个难度的 谱面定数 物量 谱师
    根据提示，将答案输入程序并按下回车。
    如果有误，请继续按提示填完符合格式的数据（瞎填就行），最后会有一处提示修改的地方。

    注意：持续时间、谱面定数、物量需要为整数值
        曲绘图片的在线链接 可以直接复制你找的wiki的（推荐），也可以上网搜，
        一般在图片上右键会有复制图像链接的选项，实在不会上网搜。
        愚人节曲和其看门曲是两个不同的曲子，不要弄混
        愚人节曲只有SP难度，因此任意一个曲子，只要填了SP难度的信息，都会直接跳过其他所有难度。\n
"""

欢迎 = """
欢迎使用本谱面转换程序
在使用之前，请确保您已经完全阅读github主页上的内容，并已完成程序相关配置。
如果遇到异常终止，请选择您最后进行的操作，并按提示加载进度文件\n
"""

请选择功能 = """
请选择功能：
    【1】 根据本地数据，直接生成全部谱面文件（首次使用请选择）
    【2】 更新本地数据文件（将新版本phi的文件直接追加到相应目录中后，使用此项更新）
    【3】 重置本地数据文件（仅包括谱面元数据）
    【4】 重置歌曲查找表和曲绘查找表
    【5】 错误谱面处理（有错误存在时务必处理完错误）
请输入一位整数：
"""

添加到忽略列表中 = """
    注意，此操作将会将谱面信息错误列表中现存的歌曲全部添加到忽略列表中，不再处理
    此操作还会删除已存在的进度文件。
    除非你已经筋疲力尽、走投无路，否则不要使用此功能。
    想要恢复他们需要自行修改数据文件(./data/songsInformation.json)
    
    以下文件将会被忽略：\n
"""

更新数据文件 = """
将检查对应目录中是否有新的音频文件，据此更新本地数据文件。
注意：所有未完成的进度都将丢失！
"""
