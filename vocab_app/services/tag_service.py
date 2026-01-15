import re
import json
import os

class TagService:
    # 小型内置考纲关键词库 (示例)
    EXAM_DICT = {
        'CET4': ['abandon', 'ability', 'abnormal', 'aboard', 'absence', 'absolute', 'absorb', 'abstract', 'abundant', 'abuse'],
        'CET6': ['aesthetic', 'alleviate', 'ambiguous', 'analogy', 'anonymous', 'arbitrary', 'augment', 'authentic'],
        'GRE': ['aberrant', 'abjure', 'abnegation', 'abscission', 'abscond', 'abstemious', 'abstruse', 'accretion'],
        'IELTS': ['accumulate', 'adequate', 'adjacent', 'adjust', 'advocate', 'aggregate', 'albeit', 'allocate'],
    }

    _freq_data = None

    @classmethod
    def _load_freq_data(cls):
        if cls._freq_data is not None:
            return cls._freq_data

        cls._freq_data = {}
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(base_dir, 'resources', 'word_freq.json')
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    cls._freq_data = json.load(f)
        except Exception as e:
            print(f"Error loading frequency data: {e}")
        return cls._freq_data

    @staticmethod
    def get_tags_for_word(word, html_content=None):
        """
        根据有道 HTML、本地词频库或内置考纲库获取单词标签。
        """
        tags = set()
        word_lower = word.lower().strip()

        # 1. 词频数据匹配 (COCA/BNC)
        freq_map = TagService._load_freq_data()
        rank = freq_map.get(word_lower)
        if rank:
            if rank <= 3000:
                tags.add(f"核心({rank})")
            elif rank <= 8000:
                tags.add(f"常用({rank})")
            elif rank <= 15000:
                tags.add(f"高阶({rank})")
            else:
                tags.add(f"扩展({rank})")

        # 2. 内置库匹配
        for tag, words in TagService.EXAM_DICT.items():
            if word_lower in words:
                tags.add(tag)

        # 3. 从有道 HTML 抓取 (更准确)
        if html_content:
            # 查找类似于 "考研 / CET4 / CET6" 的文本
            for pattern, predicate in [
                (r'class="exam-type">([^<]+)</span>', lambda m: True),
                (r'class="additional">([^<]+)</span>', lambda m: any(x in m for x in ["4", "6", "研", "托", "雅", "GRE"]))
            ]:
                matches = re.findall(pattern, html_content)
                for m in matches:
                    if predicate(m):
                        tags.update([t.strip() for t in m.replace("考试：", "").split('/')])

        return list(tags)

    @staticmethod
    def format_tags(tags_list):
        if not tags_list: return ""
        if isinstance(tags_list, str): return tags_list
        # 排序：让考纲标签排前面，词频标签排后面
        sorted_tags = sorted(list(tags_list), key=lambda x: (0 if any(e in x for e in ["CET", "GRE", "IELTS"]) else 1, x))
        return ",".join(sorted_tags)
