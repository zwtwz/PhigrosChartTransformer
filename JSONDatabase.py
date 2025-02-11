import orjson
import threading
import os
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Union, Callable
import config


class LazyCopyDict(dict):
    """在修改时创建深拷贝的字典"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._copied = False

    def _ensure_copy(self):
        """如果尚未创建副本，则创建副本"""
        if not self._copied:
            self._copied = True
            self.update(deepcopy(self))

    def __setitem__(self, key, value):
        self._ensure_copy()
        super().__setitem__(key, value)

    def update(self, *args, **kwargs):
        self._ensure_copy()
        super().update(*args, **kwargs)

    def pop(self, key, default=None):
        self._ensure_copy()
        return super().pop(key, default)

    def popitem(self):
        self._ensure_copy()
        return super().popitem()

    def clear(self):
        self._ensure_copy()
        super().clear()

    def setdefault(self, key, default=None):
        self._ensure_copy()
        return super().setdefault(key, default)


class LazyCopyList(list):
    """在修改时创建深拷贝的列表"""
    def __init__(self, *args):
        super().__init__(*args)
        self._copied = False

    def _ensure_copy(self):
        """如果尚未创建副本，则创建副本"""
        if not self._copied:
            self._copied = True
            self[:] = deepcopy(self)

    def __setitem__(self, index, value):
        self._ensure_copy()
        super().__setitem__(index, value)

    def append(self, item):
        self._ensure_copy()
        super().append(item)

    def extend(self, iterable):
        self._ensure_copy()
        super().extend(iterable)

    def insert(self, index, item):
        self._ensure_copy()
        super().insert(index, item)

    def remove(self, item):
        self._ensure_copy()
        super().remove(item)

    def pop(self, index=-1):
        self._ensure_copy()
        return super().pop(index)

    def clear(self):
        self._ensure_copy()
        super().clear()



@dataclass
class JSONDatabase:
    """为json数据存储提供类似于sqlite的接口"""
    data_file_path: str  # JSON 数据存储文件
    caller: str  # 调用者标识
    cache_dir: str = field(default=config.paths["cacheDataPath"])   # 缓存存储目录
    compact_encoding: bool = field(default=False)
    enable_non_volatile_cache: bool = field(default=True)  # 是否启用非易失性缓存
    __cache: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # 非易失性缓存
    __lock: threading.Lock = field(default_factory=threading.Lock, init=False)  # 文件写入锁

    def __repr__(self):
        return f"<JSONDatabase caller={self.caller} data_file_path={self.data_file_path}>"
    
    def __str__(self):
        return self.__repr__()

    def __load_data(self) -> Dict:
        """从 JSON 文件加载数据"""
        try:
            with open(self.data_file_path, "rb") as f:
                return orjson.loads(f.read())
        except (FileNotFoundError, orjson.JSONDecodeError):
            return {}

    def __save_data(self, data: Dict):
        """保存数据到 JSON 文件（加锁以避免竞态条件）"""
        # 若不启用 compact_encoding，则使用 orjson.OPT_INDENT_2 产生格式化输出
        option = orjson.OPT_INDENT_2 if not self.compact_encoding else 0
        with self.__lock:
            with open(self.data_file_path, "wb") as f:
                f.write(orjson.dumps(data, option=option))

    def __get_by_path(self, data: Union[Dict, List], path: str) -> Any:
        """通过路径获取数据（支持字典和列表），返回引用"""
        if path == ".":  # 获取整个数据
            return data
        keys = path.split(".")
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            elif isinstance(data, list) and key.isdigit():
                index = int(key)
                if 0 <= index < len(data):
                    data = data[index]
                else:
                    return None
            else:
                return None
        return data

    def __get_parent_element_by_path(self, data: Union[Dict, List], path: str) -> Union[Dict, List]:
        """通过路径获取数据（支持字典和列表）的父元素，返回引用"""
        if path == ".":  # 获取整个数据
            return data
        keys = path.split(".")
        keys.pop()  # 移除最后一个元素(子元素)
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            elif isinstance(data, list) and key.isdigit():
                index = int(key)
                if 0 <= index < len(data):
                    data = data[index]
                else:
                    return None
            else:
                return None
        
        if isinstance(data, (dict, list)):
            return data
        else:
            return None

    def __get_last_key(self, path: str) -> str:
            """获取路径的最后一个键名"""
            keys = path.split(".")
            return keys[-1] if keys else ""
    
    def __set_by_path(self, data: Union[Dict, List], path: str, value: Any):
        """通过路径设置数据（支持字典和列表）"""
        keys = path.split(".")
        d = data
        for i, key in enumerate(keys[:-1]):
            if isinstance(d, dict):
                if key not in d:
                    # 若下一个key为数字，则创建列表，否则创建字典
                    d[key] = [] if keys[i + 1].isdigit() else {}
                d = d[key]
            elif isinstance(d, list) and key.isdigit():
                index = int(key)
                # 扩充列表长度
                while len(d) <= index:
                    d.append({} if not keys[i + 1].isdigit() else [])
                d = d[index]
            else:
                raise ValueError(f"无法设置路径 '{'.'.join(keys[:i+1])}'，类型不匹配: {type(d)}")

        last_key = keys[-1]
        if isinstance(d, dict):
            d[last_key] = value
        elif isinstance(d, list) and last_key.isdigit():
            index = int(last_key)
            while len(d) <= index:
                d.append(None)
            d[index] = value
        else:
            raise ValueError(f"路径 '{path}' 结尾无效，数据结构错误")

    def __merge_data(self,
                       base: Union[Dict, List],
                       update: Union[Dict, List],
                       overwrite: bool,
                       list_merge_mode: str = "unique"):
        """
        合并 base 和 update 数据：
        - 字典：递归合并
        - 列表：支持 append / unique / index 三种模式
        - 类型冲突：默认报错，若 overwrite=True，则覆盖 base

        list_merge_mode:
        - "append" -> 追加 update 的内容
        - "unique" -> 追加去重后内容
        - "index" -> 逐项覆盖索引相同的元素
        """
        if isinstance(base, dict) and isinstance(update, dict):
            for key, value in update.items():
                if key in base:
                    base[key] = self.__merge_data(base[key], value, overwrite, list_merge_mode)
                else:
                    base[key] = value
            return base

        elif isinstance(base, list) and isinstance(update, list):
            if list_merge_mode == "append":
                return base + update
            elif list_merge_mode == "unique":
                old_list = [item for item in update if item not in update]
                merged = old_list + update
                return merged
            elif list_merge_mode == "index":
                merged = base[:]
                for i, val in enumerate(update):
                    if i < len(merged):
                        merged[i] = val  # 覆盖
                    else:
                        merged.append(val)  # 追加
                return merged
            else:
                raise ValueError(f"不支持的 list_merge_mode: {list_merge_mode}")

        elif overwrite:
            return update  # 直接覆盖

        else:
            raise TypeError(f"数据类型冲突: {type(base)} vs {type(update)}，请启用 overwrite=True 以覆盖")

    def get(self, path: str = ".", default=None, enable_deepcopy:bool=True) -> Any:
        """获取缓存中加载的的数据，默认值：None; enable_deepcopy: 是否启用深拷贝，启用后会返回延迟拷贝的新对象"""
        cache_data = self.__load_cache()
        target_data = self.__get_by_path(cache_data, path)

        if target_data is None:
            return default
        elif enable_deepcopy and isinstance(target_data, dict):
            return LazyCopyDict(target_data)
        elif enable_deepcopy and isinstance(target_data, list):
            return LazyCopyList(target_data)
        else:
            return target_data

    def set(self, path: str, value: Any):
        """设置数据到缓存文件"""
        cache_data = self.__load_cache()
        self.__set_by_path(cache_data, path, value)
        if self.enable_non_volatile_cache:
            self.save_cache()

    def commit(self, merge: bool = False, overwrite: bool = False, list_merge_mode: str = "unique"):
        """
        提交缓存到数据文件，支持合并或覆盖
        merge: 是否合并缓存到数据文件，支持合并列表和字典，默认 False 即直接覆盖

        在启用了 merge 的情况下，以下参数有效：
        overwrite: 在需要合并的数据既非字典又非列表的情况下，控制是否用新数据直接覆盖旧数据，默认 False。
        （如果禁用此选项且数据格式不受支持，merge 将会报错）
        list_merge_mode: 列表合并模式，
        支持 "append"（直接追加）/ "unique"（去重合并，默认）/ "index"（按索引覆盖）
        """
        cache_data = self.__load_cache()

        if merge:
            file_data = self.__load_data()
            merged_data = self.__merge_data(file_data, cache_data, overwrite, list_merge_mode=list_merge_mode)
            file_data = merged_data
        else:
            file_data = cache_data

        self.__save_data(file_data)
        self.__cache[self.caller] = file_data

    def __load_cache_file(self) -> Dict:
        """加载指定 caller 的缓存文件"""
        cache_path = os.path.join(self.cache_dir, f"{self.caller}.json")
        try:
            with open(cache_path, "rb") as f:
                return orjson.loads(f.read())
        except (FileNotFoundError, orjson.JSONDecodeError):
            return {}

    def __load_cache(self) -> Dict:
        """加载指定 caller 的缓存"""
        if self.caller in self.__cache:
            return self.__cache[self.caller]
        else:
            cache_data = self.__load_cache_file()
            self.__cache[self.caller] = cache_data
            self.save_cache()
            return cache_data

    def save_cache(self):
        """保存缓存数据到指定 caller 的缓存文件"""
        if self.caller not in self.__cache:
            self.__cache[self.caller] = self.__load_data()
        cache_path = os.path.join(self.cache_dir, f"{self.caller}.json")
        option = orjson.OPT_INDENT_2 if not self.compact_encoding else 0
        with open(cache_path, "wb") as f:
            f.write(orjson.dumps(self.__cache[self.caller], option=option))

    def __clear_cache_file(self):
        """清除指定 caller 的缓存文件"""
        cache_path = os.path.join(self.cache_dir, f"{self.caller}.json")
        if os.path.exists(cache_path):
            os.remove(cache_path)

    def reset_cache(self, user_check: bool = False):
        """从数据库文件中加载数据到对应 caller 的缓存中，并清除缓存文件"""
        if not user_check:
            user_choice = "y"
        else:
            while True:
                user_choice = input("是否重置缓存（所有进度都将丢失）？(y/n) ")
                if user_choice.lower() in ["y", "n"]:
                    break
                else:
                    print("无效输入。")
        if user_choice.lower() == "y":
            self.__clear_cache_file()  # 清除缓存文件
            self.__cache[self.caller] = self.__load_data()
            if self.enable_non_volatile_cache:
                self.save_cache()
            print("缓存已重置。")
        elif user_choice.lower() == "n":
            print("缓存未重置。")

    def reload_cache(self, user_check: bool = False):
        """重新（从缓存文件）加载特定调用者的缓存。当缓存文件不存在时，将重置缓存。"""
        cache_path = os.path.join(self.cache_dir, f"{self.caller}.json")
        if os.path.exists(cache_path):
            if not user_check:
                user_choice = "y"
            else:
                while True:
                    user_choice = input("是否从文件加载缓存？(y/n) ")
                    if user_choice.lower() in ["y", "n"]:
                        break
                    else:
                        print("无效输入。")
            if user_choice.lower() == "y":
                self.__cache[self.caller] = self.__load_cache_file()
                print("缓存已加载。")
            elif user_choice.lower() == "n":
                print("缓存未加载。")
        else:
            self.reset_cache(user_check)

    def __apply_where_filter(self,
                               data: Union[List[Dict],
                                           Dict[str, Dict]],
                               where: Union[Dict[str, Any],
                                            Callable[[Dict], bool],
                                            None],
                               match_mode: str) -> Union[List[Dict], Dict[str, Dict]]:
        """应用 WHERE 过滤逻辑，返回过滤后的数据"""
        if where is None:
            return data

        if isinstance(where, dict):
            def filter_func(item):
                if not isinstance(item, dict):
                    return False
                matches = (item.get(k) == v for k, v in where.items())
                return all(matches) if match_mode == "and" else any(matches)
        elif callable(where):
            def filter_func(item: dict):
                if not isinstance(item, dict):
                    return False
                return where(item)
        else:
            raise ValueError("where 参数必须是字典或函数。")

        if isinstance(data, list):
            return [item for item in data if filter_func(item)]
        elif isinstance(data, dict):
            return {k: v for k, v in data.items() if filter_func(v)}
        else:
            raise ValueError("数据格式不支持 where 过滤。")

    def exists(self,
               table: str,
               where: Union[Dict[str, Any],
                            Callable[[Dict], bool],
                            None] = None,
               match_mode: str = "and") -> bool:
        """
        检查数据是否存在
        - table: 查询的 JSON 路径（例如 "users"）
        - where: 过滤条件（支持 {"key": "value"} 或 lambda item: 条件）
        - match_mode: "and"（所有键值匹配）或 "or"（只需匹配其中之一）
        """
        data = self.__load_cache()
        d = self.__get_by_path(data, table)
        if d is None:
            return False

        if where is None:
            return True

        if isinstance(d, list):
            filtered = self.__apply_where_filter(d, where, match_mode)
            return len(filtered) > 0
        else:
            raise ValueError("where 参数仅适用于列表类型的数据。")

    def select(
        self, 
        path: str, 
        where: Union[Dict[str, Any], Callable[[Dict], bool], None] = None, 
        match_mode: str = "and", 
        fields: List[str] = None,
        deepcopy = True
    ) -> Union[List[Dict], Dict[str, Dict]]:
        """执行 SQL 风格查询"""
        data = self.__load_cache()
        table_data = self.__get_by_path(data, path)

        if not isinstance(table_data, (list, dict)):
            raise ValueError(f"路径 '{path}' 不是列表或字典，无法执行查询。")

        filtered_data = self.__apply_where_filter(table_data, where, match_mode)

        if fields:
            if isinstance(filtered_data, list):
                return [{field: self.__get_by_path(item, field) for field in fields} for item in filtered_data]
            elif isinstance(filtered_data, dict):
                return {k: {field: self.__get_by_path(v, field) for field in fields} for k, v in filtered_data.items()}
            else:
                raise ValueError("fields 参数必须用于列表或字典数据。")

        if not deepcopy:
            return filtered_data
        
        if isinstance(filtered_data, list):
            return LazyCopyList(filtered_data)
        elif isinstance(filtered_data, dict):
            return LazyCopyDict(filtered_data)
        else:
            return filtered_data

    def delete(self,
               path: str,
               where: Union[Dict[str, Any],
                            Callable[[Dict], bool],
                            None] = None,
               match_mode: str = "and"):
        """根据路径和 where 参数删除数据并写入缓存"""
        cache_data = self.__load_cache()
        target_data = self.__get_by_path(cache_data, path)

        if where is None:
            # 删除整个元素
            key_of_element = path.split(".")[-1] if "." in path else path
            parent = self.__get_parent_element_by_path(cache_data, path)
            if parent is None:
                raise ValueError(f"无法找到路径 '{path}' 的父元素。")
            if isinstance(parent, dict):
                parent.pop(key_of_element, None)
            elif isinstance(parent, list) and key_of_element.isdigit():
                index = int(key_of_element)
                if 0 <= index < len(parent):
                    parent.pop(index)
                else:
                    raise ValueError(f"索引 {index} 超出列表范围。")
            else:
                raise ValueError("删除操作不支持的数据结构。")
        else:
            if not isinstance(target_data, (list, dict)):
                raise ValueError(f"路径 '{path}' 不是列表或字典，无法执行 where 筛选删除。")
            filtered_data = self.__apply_where_filter(target_data, where, match_mode)
            if isinstance(target_data, list):
                for item in filtered_data:
                    target_data.remove(item)
            elif isinstance(target_data, dict):
                # 对字典，移除符合条件的键值对
                for key, value in list(target_data.items()):
                    if value in filtered_data:
                        target_data.pop(key)
                        
        if self.enable_non_volatile_cache:
            self.save_cache()

    def append(self,
               path: str,
               data: Any):
        """
        将数据添加到指定路径并写入缓存。
        路径需要指向 list 或 dict 类型。对于 dict 类型的目标，data 需要是 dict。
        """
        cache_data = self.__load_cache()
        target_data = self.__get_by_path(cache_data, path)
        if target_data is None:
            raise ValueError(f"路径 '{path}' 不存在。")
        if isinstance(target_data, list):
            target_data.append(data)
        elif isinstance(target_data, dict):
            if not isinstance(data, dict):
                raise ValueError(f"路径 '{path}' 指向字典，但是 data 并非字典，无法添加数据。")
            target_data.update(data)
        else:
            raise ValueError(f"路径 '{path}' 不是列表或字典，无法添加数据。")
        
        if self.enable_non_volatile_cache:
            self.save_cache()
    
    def modify(
        self, 
        path: str,
        new_data: Any,
        where: Union[Dict[str, Any], Callable[[Dict], bool], None] = None, 
        match_mode: str = "and", 
        fields: List[str] = None
    ) -> None:
        """
        根据路径和 where 参数修改数据并写入缓存。
        where 参数可以是字典、函数或 None。
        如果为字典，则将字典中的键值对应用到符合条件的数据上。
        如果为函数，则将函数返回值应用到符合条件的数据上。
        如果为 None，则将整个数据替换为 fields 参数指定的值。
        match_mode 参数可以是 "and" 或 "or"，表示where 条件的匹配方式。
        fields 参数表示要修改的字段名列表，如果为 None，则修改所有符合where的数据。
        """
        
        cache_data = self.__load_cache()
        parent_data = self.__get_parent_element_by_path(cache_data, path)
        last_key = self.__get_last_key(path)

        if where is None:
            # 修改整个元素
            target_data = parent_data
            target_data_keys = [last_key]
        else:
            target_data = parent_data[last_key]
            if not isinstance(target_data, (list, dict)):
                raise ValueError(f"路径 '{path}' 不是列表或字典，无法执行 where 筛选修改。")
            
            """应用 WHERE 过滤逻辑"""
            if isinstance(where, dict):
                def filter_func(item: dict):
                    matches = [item.get(k) == v for k, v in where.items()]
                    return all(matches) if match_mode == "and" else any(matches)
            elif callable(where):
                def filter_func(item: dict):
                    if not isinstance(item, dict):
                        return False
                    return where(item)
            else:
                raise ValueError("where 参数必须是字典或函数。")

            if isinstance(target_data, list):
                target_data_keys = [i for i,v in enumerate(target_data) if filter_func(v)]
            elif isinstance(target_data, dict):
                target_data_keys = [k for k,v in target_data.items() if filter_func(v)]
            else:
                raise ValueError("数据格式不支持 where 过滤。")
        
        for target_key in target_data_keys:
            if not fields:
                target_data[target_key] = new_data
                continue
            new_target_data = target_data[target_key]
            for field in fields:
                if field in new_target_data:
                    new_target_data[field] = new_data
                else:
                    raise ValueError(f"目标键{target_key}中不存在字段{field}，数据无法修改。")
        
        if self.enable_non_volatile_cache:
            self.save_cache()
            


    def __post_init__(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
        # 初次将文件数据加载到对应 caller 的缓存中
        self.__cache[self.caller] = self.__load_data()

    def close(self):
        """关闭数据库连接"""
        if self.enable_non_volatile_cache:
            self.save_cache()
        self.__cache.pop(self.caller, None)