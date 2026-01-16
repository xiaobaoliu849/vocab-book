"""
多词典聚合查询服务
支持: 有道词典、剑桥词典 (Cambridge)、Bing词典、Free Dictionary
"""
import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed


def _get_clean_text(el):
    """Helper to safely extract clean text from a BeautifulSoup element."""
    if not el:
        return ""
    text = el.get_text(separator=' ', strip=True)
    return re.sub(r'\s+', ' ', text).strip()


class MultiDictService:
    """多词典聚合查询服务"""

    # 词典源标识
    DICT_YOUDAO = "youdao"
    DICT_CAMBRIDGE = "cambridge"
    DICT_BING = "bing"
    DICT_FREE = "freedict"

    # 词典显示名称
    DICT_NAMES = {
        DICT_YOUDAO: "有道词典",
        DICT_CAMBRIDGE: "剑桥词典 (Cambridge)",
        DICT_BING: "Bing 词典",
        DICT_FREE: "Free Dictionary",
    }

    @staticmethod
    def search_cambridge(word):
        """
        剑桥词典查询 (High Quality)
        """
        try:
            # 剑桥词典 URL (English-Chinese Simplified)
            url = f"https://dictionary.cambridge.org/dictionary/english-chinese-simplified/{word}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7'
            }
            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, 'html.parser')

            # 检查是否找到单词 (di-title)
            if not soup.find('div', class_='di-title'):
                return None

            # 音标 (dpron)
            phonetic = ""
            us_pron = soup.find('span', class_='us')
            if us_pron:
                pron_span = us_pron.find('span', class_='pron')
                if pron_span:
                    phonetic = f"US {pron_span.get_text(strip=True)}"

            # 释义 & 例句
            # 剑桥词典结构: entry-body -> pr-entry-body__el -> sense-block -> def-block
            meanings = []
            examples = []
            
            # 获取前 3 个释义块
            def_blocks = soup.find_all('div', class_='def-block', limit=3)

            for block in def_blocks:
                # 英文释义 (ddef_h -> def)
                ddef_h = block.find('div', class_='ddef_h')
                eng_def = ""
                if ddef_h:
                    def_text = ddef_h.find('div', class_='def')
                    eng_def = _get_clean_text(def_text)

                # 中文释义 (def-body -> trans)
                chn_def = ""
                trans = block.find('span', class_='trans')
                chn_def = _get_clean_text(trans)

                if eng_def or chn_def:
                    m_text = f"{eng_def} {chn_def}".strip()
                    meanings.append(m_text)

                # 例句 (examp)
                examps = block.find_all('div', class_='examp', limit=2)
                for ex in examps:
                    eg = ex.find('span', class_='eg')
                    eg_trans = ex.find('span', class_='trans')
                    if eg:
                        eg_text = _get_clean_text(eg)
                        trans_text = _get_clean_text(eg_trans)
                        if trans_text:
                            examples.append(f"{eg_text}\n{trans_text}")
                        else:
                            examples.append(eg_text)

            meaning = "\n".join([f"• {m}" for m in meanings])
            example = "\n".join(examples[:3]) # 限制例句数量

            return {
                "source": MultiDictService.DICT_CAMBRIDGE,
                "source_name": MultiDictService.DICT_NAMES[MultiDictService.DICT_CAMBRIDGE],
                "word": word,
                "phonetic": phonetic,
                "meaning": meaning,
                "example": example
            }

        except Exception as e:
            print(f"Cambridge search error: {e}")
            return None

    @staticmethod
    def search_bing(word):
        """Bing 词典查询"""
        try:
            # 使用 mkt=zh-cn 强制中文版，setlang 备用
            url = f"https://cn.bing.com/dict/search?q={word}&mkt=zh-cn&setlang=zh-hans"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            resp = requests.get(url, headers=headers, timeout=8)

            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, 'html.parser')

            if not soup.find('div', class_='qdef'):
                return None

            phonetic = ""
            pron_us = soup.find('div', class_='hd_prUS')
            if pron_us:
                phonetic = pron_us.get_text(strip=True)

            meaning = ""
            # Bing 结构变化：div.qdef 里面直接包含 li（无 class）
            qdef = soup.find('div', class_='qdef')
            if qdef:
                meanings = []
                for li in qdef.find_all('li'):
                    text = li.get_text(separator=' ', strip=True)
                    if text and len(text) > 1:
                        meanings.append(text)
                meaning = "\n".join(meanings)

            example = ""
            se_div = soup.find('div', id='sentenceSeg')
            if se_div:
                first_sent = se_div.find('div', class_='se_li')
                if first_sent:
                    en_sent = first_sent.find('div', class_='sen_en')
                    cn_sent = first_sent.find('div', class_='sen_cn')
                    if en_sent and cn_sent:
                        example = f"{en_sent.get_text(separator=' ', strip=True)}\n{cn_sent.get_text(separator=' ', strip=True)}"

            return {
                "source": MultiDictService.DICT_BING,
                "source_name": MultiDictService.DICT_NAMES[MultiDictService.DICT_BING],
                "word": word,
                "phonetic": phonetic,
                "meaning": meaning,
                "example": example
            }

        except Exception as e:
            print(f"Bing search error: {e}")
            return None

    @staticmethod
    def search_free_dict(word):
        """Free Dictionary API 查询"""
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            resp = requests.get(url, timeout=8)

            if resp.status_code != 200:
                return None

            data = resp.json()
            if not data or not isinstance(data, list):
                return None

            entry = data[0]
            phonetic = entry.get('phonetic', '')
            
            meanings = []
            examples = []

            for m in entry.get('meanings', []):
                part = m.get('partOfSpeech', '')
                for d in m.get('definitions', [])[:2]:
                    text = d.get('definition', '')
                    if text:
                        meanings.append(f"{part}. {text}")
                    if d.get('example'):
                        examples.append(d['example'])

            meaning = "\n".join(meanings[:5])
            example = "\n".join(examples[:2])

            return {
                "source": MultiDictService.DICT_FREE,
                "source_name": MultiDictService.DICT_NAMES[MultiDictService.DICT_FREE],
                "word": word,
                "phonetic": phonetic,
                "meaning": meaning, 
                "example": example
            }

        except Exception as e:
            print(f"Free Dictionary search error: {e}")
            return None

    @staticmethod
    def aggregate_search(word, enabled_dicts=None, youdao_result=None):
        """
        聚合查询，包含 Youdao, Cambridge, Bing, FreeDict
        """
        if enabled_dicts is None:
            enabled_dicts = [
                MultiDictService.DICT_YOUDAO,
                MultiDictService.DICT_CAMBRIDGE, 
                MultiDictService.DICT_BING,
                MultiDictService.DICT_FREE
            ]

        results = {"primary": None, "sources": {}}

        # 有道
        if youdao_result:
            results["sources"][MultiDictService.DICT_YOUDAO] = {
                "source": MultiDictService.DICT_YOUDAO,
                "source_name": MultiDictService.DICT_NAMES[MultiDictService.DICT_YOUDAO],
                **youdao_result
            }
            results["primary"] = youdao_result

        # 并发查询其他
        tasks = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            if MultiDictService.DICT_CAMBRIDGE in enabled_dicts:
                tasks[executor.submit(MultiDictService.search_cambridge, word)] = MultiDictService.DICT_CAMBRIDGE
            
            if MultiDictService.DICT_BING in enabled_dicts:
                tasks[executor.submit(MultiDictService.search_bing, word)] = MultiDictService.DICT_BING

            if MultiDictService.DICT_FREE in enabled_dicts:
                tasks[executor.submit(MultiDictService.search_free_dict, word)] = MultiDictService.DICT_FREE

            for future in as_completed(tasks, timeout=12):
                source = tasks[future]
                try:
                    result = future.result()
                    if result:
                        results["sources"][source] = result
                except Exception as e:
                    print(f"Dict {source} error: {e}")

        # 确定主要结果 (有道 > 剑桥 > Bing)
        if not results["primary"]:
            for source in [MultiDictService.DICT_YOUDAO, MultiDictService.DICT_CAMBRIDGE, MultiDictService.DICT_BING]:
                if source in results["sources"]:
                    results["primary"] = results["sources"][source]
                    break
        
        # 兜底
        if not results["primary"] and results["sources"]:
            results["primary"] = list(results["sources"].values())[0]

        return results

    @staticmethod
    def get_best_phonetic(sources):
        for source in [MultiDictService.DICT_CAMBRIDGE, MultiDictService.DICT_YOUDAO, MultiDictService.DICT_BING]:
            if source in sources and sources[source].get('phonetic'):
                return sources[source]['phonetic']
        return ""

    @staticmethod
    def get_all_examples(sources):
        """合并所有来源的例句 (无标题版)"""
        example_groups = []  # 每组是 (英文, 中文) 或 (英文,)
        # 优先级: Cambridge > Youdao > Bing > Free
        order = [MultiDictService.DICT_CAMBRIDGE, MultiDictService.DICT_YOUDAO, MultiDictService.DICT_BING, MultiDictService.DICT_FREE]
        
        seen_examples = set()  # 简单的去重

        for source in order:
            if source in sources:
                data = sources[source]
                if data.get('example'):
                    ex_text = data['example'].strip()
                    if not ex_text:
                        continue
                    
                    # 按行分割
                    lines = ex_text.split('\n')
                    
                    # 临时存储当前正在处理的英文例句
                    current_en = None
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # 检查是否包含来源标记（防御性编程）
                        if line.startswith("【") and line.endswith("】"):
                            continue

                        # 简单的长度过滤，太短的可能是干扰字符
                        if len(line) < 3:
                            continue

                        # 跳过已见过的内容
                        if line in seen_examples:
                            continue
                        
                        seen_examples.add(line)
                        
                        # 判断是英文还是中文
                        # 简单判断：第一个字符是否是 ASCII（英文/标点）
                        is_english = line[0].isascii()
                        
                        if is_english:
                            # 如果之前有未配对的英文例句，先保存它
                            if current_en:
                                example_groups.append((current_en, None))
                            # 开始新的英文例句
                            current_en = line
                        else:
                            # 这是中文翻译
                            if current_en:
                                # 与当前英文配对
                                example_groups.append((current_en, line))
                                current_en = None
                            else:
                                # 没有英文配对，单独的中文（可能是某些格式问题）
                                example_groups.append((None, line))
                    
                    # 处理剩余未配对的英文
                    if current_en:
                        example_groups.append((current_en, None))
        
        # 格式化输出，每组例句之间空一行
        output_parts = []
        for en, cn in example_groups:
            group_lines = []
            if en:
                group_lines.append(f"• {en}")
            if cn:
                group_lines.append(f"  {cn}")
            if group_lines:
                output_parts.append("\n".join(group_lines))
        
        # 用空行分隔各组
        return "\n\n".join(output_parts)