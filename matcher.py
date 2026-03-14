import difflib
import re
import pandas as pd
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

class ColorMatcher:
    """颜色模糊匹配器 - 高性能版本"""
    
    # 颜色别名映射表
    COLOR_ALIASES = {
        '红': ['红', '粉红', '桃红', '玫红', '酒红', '大红', '朱红', '暗红', '砖红', '棕红'],
        '粉': ['粉', '粉红', '桃粉', '裸粉', '浅粉', '玫粉'],
        '黄': ['黄', '金黄', '鹅黄', '柠檬黄', '土黄', '橘黄', '米黄', '浅黄'],
        '蓝': ['蓝', '天蓝', '海蓝', '深蓝', '浅蓝', '藏蓝', '宝蓝', '湖蓝', '钴蓝', '靛蓝'],
        '绿': ['绿', '草绿', '墨绿', '浅绿', '深绿', '翠绿', '橄榄绿', '薄荷绿'],
        '黑': ['黑', '纯黑', '墨黑', '炭黑'],
        '白': ['白', '纯白', '米白', '乳白', '象牙白'],
        '灰': ['灰', '浅灰', '深灰', '银灰', '炭灰', '烟灰'],
        '紫': ['紫', '深紫', '浅紫', '紫罗兰', '葡萄紫'],
        '棕': ['棕', '咖啡', '驼色', '卡其', '褐色', '焦糖', '土棕'],
        '橙': ['橙', '橘色', '桔色', '珊瑚橙', '南瓜橙'],
        '杏': ['杏', '杏色', '杏黄', '米杏', '浅杏'],
        '青': ['青', '藏青', '青色', '青绿'],
    }
    
    def __init__(self, available_colors):
        """
        初始化颜色匹配器
        :param available_colors: 资料库中存在的颜色列表
        """
        self.available_colors = [str(c).strip() for c in available_colors if c]
        # 预计算颜色别名映射，加速查询
        self._build_color_map()
        self._build_index()
        
    def _build_color_map(self):
        """预构建颜色映射表"""
        self.color_to_group = {}
        for group, aliases in self.COLOR_ALIASES.items():
            for alias in aliases:
                self.color_to_group[alias] = group
    
    def _build_index(self):
        """构建颜色索引以加速匹配"""
        # 构建前缀索引
        self.prefix_index = {}
        for color in self.available_colors:
            # 为每个颜色的前2-4个字符建立索引
            for i in range(2, min(5, len(color) + 1)):
                prefix = color[:i]
                if prefix not in self.prefix_index:
                    self.prefix_index[prefix] = []
                self.prefix_index[prefix].append(color)
        
        # 构建别名索引
        self.alias_index = {}
        for color in self.available_colors:
            for alias, group in self.color_to_group.items():
                if alias in color:
                    if group not in self.alias_index:
                        self.alias_index[group] = set()
                    self.alias_index[group].add(color)
    
    @lru_cache(maxsize=1000)
    def match(self, query_color, threshold=0.6):
        """
        模糊匹配颜色 - 高性能版本
        :param query_color: 查询的颜色
        :param threshold: 相似度阈值
        :return: 匹配到的颜色列表，按相似度排序
        """
        query_color = str(query_color).strip()
        if not query_color:
            return []
        
        matches = set()
        
        # 1. 直接包含匹配 - O(1) 使用索引
        if query_color in self.prefix_index:
            for color in self.prefix_index[query_color]:
                if query_color in color or color in query_color:
                    matches.add((color, 1.0))
        
        # 如果没有索引命中，遍历所有颜色
        if not matches:
            for color in self.available_colors:
                if query_color in color or color in query_color:
                    matches.add((color, 1.0))
        
        # 2. 别名匹配 - 如果直接匹配不到
        if not matches:
            query_group = None
            # 快速查找查询颜色所属的组
            for alias, group in self.color_to_group.items():
                if query_color.startswith(alias) or alias in query_color:
                    query_group = group
                    break
            
            if query_group and query_group in self.alias_index:
                for color in self.alias_index[query_group]:
                    matches.add((color, 0.9))
        
        # 3. 相似度匹配 - 如果前两种都匹配不到（限制搜索范围）
        if not matches:
            # 只检查前缀相似的颜色
            candidate_colors = []
            for i in range(2, min(4, len(query_color) + 1)):
                prefix = query_color[:i]
                if prefix in self.prefix_index:
                    candidate_colors.extend(self.prefix_index[prefix])
            
            # 去重
            candidate_colors = list(set(candidate_colors)) if candidate_colors else self.available_colors[:100]
            
            for color in candidate_colors:
                similarity = SequenceMatcher(None, query_color, color).ratio()
                if similarity >= threshold:
                    matches.add((color, similarity))
        
        # 排序并返回
        matches = sorted(matches, key=lambda x: x[1], reverse=True)
        return [m[0] for m in matches]


class ProductMatcher:
    """商品匹配器 - 优化版本"""
    
    def __init__(self, data_loader):
        self.data_loader = data_loader
        self.color_matcher = None
        if data_loader.df is not None:
            self.color_matcher = ColorMatcher(data_loader.get_all_colors())
    
    def match_single(self, style_code, color_spec):
        """
        匹配单个商品 - 使用字典索引，O(1)查询
        :param style_code: 款式编码
        :param color_spec: 颜色及规格（如"红色;L" 或 "白色 白色;M"）
        :return: 匹配结果字典
        """
        # 标准化款式编码
        standard_code = str(style_code)[:13]
        
        # 解析查询的颜色和规格
        # 支持多种格式：
        # 1. "白色;M" - 标准格式
        # 2. "白花灰【专柜同款】M【建议90-110斤】" - 带规格在【】后面
        # 3. "白花灰M" - 颜色后直接跟规格
        
        color_spec_str = str(color_spec).strip()
        query_size = None
        
        # 先尝试用 ; 分割
        if ';' in color_spec_str:
            query_color, query_size = color_spec_str.split(';', 1)
            query_color = query_color.strip()
            query_size = query_size.strip()
        else:
            # 尝试提取规格（S, M, L, XL, 2XL, 3XL, 4XL, 5XL）
            # 匹配规格，后面可能是【、中文、或结尾
            size_match = re.search(r'(\d?XL|[SML])(?:\s*[【\[]|\s*[一-龥]|\s*$)', color_spec_str, re.IGNORECASE)
            if size_match:
                query_size = size_match.group(1).upper()
                # 移除规格部分得到颜色
                query_color = color_spec_str[:size_match.start()].strip()
            else:
                query_color = color_spec_str
        
        # 去掉【xxx】这样的后缀，提取纯颜色
        query_color = re.split(r'[【\[]', query_color)[0].strip()
        
        # 检查是否是组合商品（支持空格或+号分隔）
        is_combo = ' ' in query_color or '+' in query_color
        
        # 统一用+号分隔处理
        normalized_color = query_color.replace(' ', '+')
        combo_colors = [c.strip() for c in normalized_color.split('+') if c.strip()] if is_combo else [query_color]
        
        all_results = []
        
        if is_combo:
            # 组合商品：分别匹配每个颜色
            for combo_color in combo_colors:
                # 先尝试精确匹配
                matched = False
                for color in self.data_loader.style_color_size_index.get(standard_code, {}).keys():
                    if combo_color == color or combo_color in color or color in combo_color:
                        # 找到匹配的颜色，获取商品
                        products = self.data_loader.get_by_style_color_size(standard_code, color, query_size)
                        if products:
                            all_results.append(products[0])
                            matched = True
                            break
                
                # 精确匹配失败，使用模糊匹配
                if not matched:
                    matched_colors = self.color_matcher.match(combo_color)
                    for matched_color in matched_colors:
                        products = self.data_loader.get_by_style_color_size(standard_code, matched_color, query_size)
                        if products:
                            all_results.append(products[0])
                            break
            
            # 如果所有颜色都匹配到了，创建组合结果
            if len(all_results) == len(combo_colors) and len(all_results) > 0:
                combo_product_code = '+'.join([r['商品编码'] for r in all_results])
                result_row = all_results[0].copy()
                result_row['组合商品编码'] = combo_product_code
                # 新增：匹配商品编码（组合商品显示组合编码，单个显示单个编码）
                result_row['匹配商品编码'] = combo_product_code
                result_row['颜色匹配详情'] = ' + '.join([f"{c}→{r['颜色']}" for c, r in zip(combo_colors, all_results)])
                return result_row
            else:
                return None
        else:
            # 普通商品
            # 先尝试精确匹配
            for color in self.data_loader.style_color_size_index.get(standard_code, {}).keys():
                if query_color == color or query_color in color or color in query_color:
                    products = self.data_loader.get_by_style_color_size(standard_code, color, query_size)
                    if products:
                        result = products[0].copy()
                        # 新增：匹配商品编码（单个商品）
                        result['匹配商品编码'] = result['商品编码']
                        return result
            
            # 精确匹配失败，使用模糊匹配
            matched_colors = self.color_matcher.match(query_color)
            for matched_color in matched_colors:
                products = self.data_loader.get_by_style_color_size(standard_code, matched_color, query_size)
                if products:
                    result = products[0].copy()
                    # 新增：匹配商品编码（单个商品）
                    result['匹配商品编码'] = result['商品编码']
                    return result
            
            return None
    
    def match_batch(self, query_list, max_workers=8):
        """
        批量匹配 - 使用多线程
        :param query_list: 查询列表，每个元素是 (style_code, color_spec) 元组
        :param max_workers: 线程数
        :return: 匹配结果列表
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_index = {
                executor.submit(self.match_single, style_code, color_spec): idx 
                for idx, (style_code, color_spec) in enumerate(query_list)
            }
            
            # 收集结果
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    result = future.result()
                    results.append((idx, result))
                except Exception as e:
                    results.append((idx, None))
        
        # 按原始顺序排序
        results.sort(key=lambda x: x[0])
        return [r[1] for r in results]
