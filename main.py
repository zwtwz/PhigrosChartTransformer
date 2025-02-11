#主程序
import os, pygame
from tinytag import TinyTag
from copy import deepcopy
import config

#程序运行目录检查，配置加载
data_path = config.paths["dataPath"]
data_file_path = os.path.join(data_path, "songsInformation.json")

musics_path = config.paths["musicsPath"]
illustration_path = config.paths["illustrationsPath"]
charts_path = config.paths["inputChartsPath"]
enabled_levels = config.enabledLevels

for _, path in config.paths.items():
    if not os.path.exists(path):
        os.mkdir(path)

import chartSearch
from metadataGrab import get_file_md5, get_metadata
from chartTransform import chart_transform
from fileSelect import select_dir
import illustrationSearch
import JSONDatabase
import prompts

for handlingLevel in enabled_levels:
    if not handlingLevel in ["IN", "EZ", "HD", "SP", "Legacy", "AT"]:
        print("Error: 配置文件中的handlingLevels参数错误")
        exit()

use_auto_song_recognizing = config.useAutoSongRecognizing

db = JSONDatabase.JSONDatabase(data_file_path, "main")


#音乐集成
class MusicPlayer:
    def __init__(self):
        pygame.mixer.init()
    def play(self, music_file):
        pygame.mixer.music.load(music_file)
        pygame.mixer.music.play(1)
        return int(TinyTag.get(music_file).duration)
    def stop(self):
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    def is_playing(self):
        return pygame.mixer.music.get_busy()


def info_handle(option=1):
    """
    信息收集函数，根据需要进行手动或自动信息收集
    实现谱面、元数据全新生成、部分更新、信息错误处理
    option 0: 全新生成信息文件
    option 1: 信息错误处理
    option 2: 曲绘错误处理
    option 3: 谱面错误处理
    """

    #尝试加载元数据
    db.reload_cache(True)

    #判断运行模式：全自动0、半自动1、手动2，并输出提示信息
    chart_search_mode = 0
    illustration_search_mode = 0
    save_path = ""
    #option等于123对应的错误，与状态码指示的错误一一对应
    match option:
        case 0:
            print(prompts.进行重置或新生成)
            db.set("metadatas", [])
            #加载音乐播放器
            player = MusicPlayer()
            old_metadata_list = db.select("metadatas", where=lambda x: x["status"] == [-1,-1,-1])
            ignored_songs = [music["music"] for music in old_metadata_list]
            music_list = [music for music in os.listdir(musics_path) if "wav" in music and music not in ignored_songs]
        case 1:
            print(prompts.进行歌曲信息错误处理)
            player = MusicPlayer()
            old_metadata_list = db.select("metadatas", where=lambda x: x["status"][0] in [2,0])
            music_list = [music["music"] for music in old_metadata_list]
        case 2:
            print(prompts.进行曲绘未找到错误处理)
            player = MusicPlayer()
            old_metadata_list = db.select("metadatas", where=lambda x: x["status"][1] == 2)
            music_list = [music["music"] for music in old_metadata_list]
            while True:
                choice = input("请从上面选一个选项，并输入单个小写字母后按下回车> ")
                if choice in ["a", "b"]: break
            if choice == "a":
                illustration_search_mode = 2
            else:
                illustration_search_mode = 1
        case 3:
            old_metadata_list = db.select("metadatas", where=lambda x: x["status"][2] == 2)
            music_list = [music["music"] for music in old_metadata_list]
            print(prompts.进行谱面未找到错误处理)
            chart_search_mode = 1
            save_path = select_dir()
    
    choice = ""
    if option == 0 and use_auto_song_recognizing:
        #自动模式
        print("\n请保证听歌识曲软件处于正确状态")
        get_metadata_mode = 0
    elif option in [0, 1]:
        #手动模式
        print(prompts.请选择信息收集方式)
        choice = ""
        while not choice in ["a", "b"]:
            choice = input("请输入单个小写字母> ")

        if choice == "a":
            get_metadata_mode = 1
            print(prompts.半自动模式提示词)
        else:
            get_metadata_mode = 2
            print(prompts.全手动模式提示词)


    choiceD = input("按下回车键开始,输入n返回")
    if choiceD == "n":
        return
    num_of_musics = len(music_list)
    print("普通高中phigros听力测试现在开始(雾)")
    print("共有%s个音频文件需要处理" % str(num_of_musics))


    num_of_success_addressed = 0
    num_of_failed_addressed = 0

    #信息处理
    try:
        for i, music_file_name in enumerate(music_list):
            i += 1
            print(f"正在处理: {music_file_name} ({i}/{num_of_musics}, {int(i*100/num_of_musics)}%)")
            music_file_path = os.path.join(musics_path, music_file_name)

            # 获取元数据
            if option == 2:
                metadata = deepcopy(db.select("metadatas", where={"music": music_file_name})[0])
                print("    " + metadata["name"])
                player.play(music_file_path)
            elif option == 3:
                metadata = deepcopy(db.select("metadatas", where={"music": music_file_name})[0])
            else:
                duration_of_music_file = player.play(music_file_path)
                metadata = get_metadata(get_metadata_mode, duration_of_music_file, music_file_name, player.stop)
                if metadata["status"][0] == 2:
                    db.delete("metadatas", where={"music": music_file_name})
                    db.append("metadatas", metadata)
                    num_of_failed_addressed += 1
                    continue
                    
            # 获取曲绘
            if metadata["status"][1] == 0 or option == 2:
                illustration_file_name = illustrationSearch.get_illustration(metadata["illustrationUrl"],
                                                        music_file_name,
                                                        illustration_search_mode)
                if illustration_file_name == None:
                    metadata["status"][1] = 2
                    db.delete("metadatas", where={"music": music_file_name})
                    db.append("metadatas", metadata)
                    num_of_failed_addressed += 1
                    continue
                metadata["illustration"] = illustration_file_name
                metadata["status"][1] = 1

            # 谱面处理
            if metadata["status"][2] == 0 or option == 3:
                result_of_chart_serach = chartSearch.get_chart(metadata, chart_search_mode, save_path)
                if result_of_chart_serach == -1:
                    metadata["status"][0] = 2
                    metadata["status"][2] = 0
                    db.delete("metadatas", where={"music": music_file_name})
                    db.append("metadatas", metadata)
                    num_of_failed_addressed += 1
                    continue
                elif result_of_chart_serach == -2:
                    metadata["status"][2] = 2
                    db.delete("metadatas", where={"music": music_file_name})
                    db.append("metadatas", metadata)
                    num_of_failed_addressed += 1
                    continue
                metadata["status"][2] = 1
            
            chart_transform(metadata)  # 转换谱面
            db.delete("metadatas", where={"music": music_file_name})
            db.append("metadatas", metadata)
            num_of_success_addressed += 1

    except KeyboardInterrupt:
        print("程序终止")
    except BaseException as e:
        print("程序因未知错误而终止")
        print(e)
    else:
        db.commit()
    finally:
        try: player.stop()
        except: pass
        db.close()


    #战后结算
    num_of_total_addressed = num_of_success_addressed + num_of_failed_addressed
    num_of_unhandled = num_of_musics - num_of_total_addressed
    
    print("处理完成：")
    print("总数 " + str(num_of_musics))
    print("成功处理 " + str(num_of_success_addressed))
    print("处理失败 " + str(num_of_failed_addressed))
    print("未处理 " + str(num_of_unhandled))
    print("请立即检查并处理错误歌曲。")


def check_and_generate_pez():
    db.reload_cache(True)
    metadatas = db.select("metadatas", where={"status":[1,1,1]}, deepcopy=False)
    num_of_musics = len(metadatas)
    num_of_success_addressed = 0
    print("总数： " + str(num_of_musics) + "\n正在处理...")
    for i, metadata in enumerate(metadatas):
        song_name = metadata["name"]
        i += 1
        print(f"正在处理: {song_name} ({i}/{num_of_musics}, {int(i*100/num_of_musics)}%)")
        try:
            result = chart_transform(metadata)
        except Exception as e:
            print("未知错误")
            print(e)
            continue

        match result:
            case None:
                num_of_success_addressed += 1
            case 1: 
                print("音频文件 " + song_name + " 不存在，请手动检查。")
            case 2:
                metadata["status"][1] = 2
            case 3:
                metadata["status"][2] = 2
        db.save_cache()
    if not num_of_success_addressed == num_of_musics:
        print("处理失败：" + str(num_of_musics - num_of_success_addressed))
        print("请检查并处理错误歌曲。")
    db.commit()

def update_songs_info_file():
    db.reset_cache()
    new_music_list = [music for music in os.listdir(musics_path) if "wav" in music]
    for new_music_file_name in new_music_list:
        new_music_path = os.path.join(musics_path, new_music_file_name)
        new_md5 = get_file_md5(new_music_path)

        metadatas = db.select("metadatas", where={"md5": new_md5})
        if len(metadatas) == 0:
            print("新增：" + new_music_file_name)
            metadata={
                    "music": new_music_file_name,
                    "old_music_file_name": new_music_file_name,
                    "md5": new_md5,
                    "status": [0,0,0]
                }
            db.append("metadatas", metadata)
            continue

        for metadata in metadatas:
            try:
                for chart in metadata["charts"]:
                    charts = chartSearch.db.select(chart["level"], where={"old_filename": chart["chart"]})
                    if not len(charts) == 0:
                        chart["chart"] = charts[0]["chart"]
                        continue
                    print("chart not found: " + chart["chart"])
                    metadata["status"][0] = 2
                    metadata["status"][2] = 0
                    
                illustrations = illustrationSearch.db.select("fileLUT", where={"old_filename": metadata["illustration"]})
                new_illustration = illustrations[0]["filename"] if len(illustrations) > 0 else metadata["illustration"]
                metadata["illustration"] = new_illustration
            except KeyError:
                print("忽略 " + metadata["music"])
            metadata.update({
                "old_music_file_name": metadata["music"],
                "music": new_music_file_name,
            })
            db.modify("metadatas", metadata, where={"md5": new_md5})
            
    db.commit()
    print("处理完成，请立即检查并处理新增错误。")




if __name__ == "__main__":
    print(prompts.欢迎)
    print("当前数据库对应游戏版本: " + db.get("info.version"))

    print("目前启用难度：")
    for level in enabled_levels:
        print(level, end=" ")

    while True:
        choiceA = input(prompts.请选择功能)
        
        match choiceA:
            case "1":
                #根据本地数据文件直接生成谱面文件
                print("将根据本地数据文件直接生成全部谱面文件")
                print("请确保所有原始文件均已放入相应文件夹")
                choiceB = input("直接按下回车开始，输入n取消。")
                if choiceB == "n":
                    continue
                check_and_generate_pez()
                print("处理完成")

            case "2":
                #更新本地数据文件
                #检查是否有新的音频文件，据此更新本地数据文件并生成对应的新谱面文件
                print(prompts.更新数据文件)
                choiceB = input("直接按下回车开始，输入n取消。")
                if choiceB == "n":
                    continue
                chartSearch.update_chart_filename_lut(charts_path)
                illustrationSearch.updateIllustrationFilenameLUT()
                update_songs_info_file()
                db.set("info.version",input("请输入新的数据库对应游戏版本号: "))
                db.commit()
                
            case "3":
                #重置本地数据文件（仅包括谱面元数据）
                print("注意，原先的歌曲元数据（包括错误信息）将被重置。")
                choiceB = input("直接按下回车开始，输入n取消。")
                if choiceB == "n":
                    continue
                info_handle(option = 1)
                    
            case "4":
                #重置查找表
                choiceB = input("直接按下回车开始，输入n取消。")
                if choiceB == "n":
                    continue

                chartSearch.generate_chart_filename_lut(charts_path)
                illustrationSearch.generateIllustrationFvLUT()
                illustrationSearch.generateIllustrationFilenameLUT()

            case "5":
                #错误处理
                def len_err(y, z=2):
                    return len(db.select("metadatas", where=lambda x: x["status"][y] == z))
                
                print("请选择要人工处理的错误")
                print("【1】谱面信息错误：%s个" % int(len_err(0) + len_err(0, 0)))
                print("【2】曲绘未找到：%s个" % int(len_err(1)))
                print("【3】谱面未找到：%s个" % int(len_err(2)))
                print("【4】忽略现存的谱面信息错误")
                print("注意：任何一类错误，只有当其被完全处理（即“未处理”为0）时，\n  处理结果才会被整合进数据文件，在此之间只会保存处理进度。")
                choiceB = input("请输入一位整数：")
                match choiceB:
                    case "1":
                        info_handle(option = 1)
                    case "2":
                        info_handle(option = 2)
                    case "3":
                        info_handle(option = 3)
                    case "4":
                        print(prompts.添加到忽略列表中)
                        music_list = db.select("metadatas", where=lambda x: x["status"][0] == 2, deepcopy=False)
                        info_err_list = [music["music"] for music in music_list]
                        for i in info_err_list:
                            print(i)
                        choiceC = input("按下万恶的回车开始，输入n取消。")
                        if choiceC == "n":
                            continue
                        
                        for metadata in music_list:
                            metadata["status"] = [-1,-1,-1]

                        print("已忽略。")
                        db.commit()

                    case _:
                        print("输入错误，请重新选择")
                        continue

            case _:
                print("输入错误，请重新选择")
                continue
