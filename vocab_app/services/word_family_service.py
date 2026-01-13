"""
WordFamilyService - 派生词群组服务

负责：
1. 从外部API获取派生词数据
2. 解析词根信息
3. 管理词汇家族关联
"""

import requests
import re
from typing import List, Dict, Optional

# 常见词根词缀映射表 (本地缓存，提升性能)
COMMON_ROOTS = {
    # 常见词根
    "act": {"meaning": "做，行动", "words": ["act", "action", "active", "activate", "activity", "actor", "actual", "react", "reaction", "interact", "transaction"]},
    "aud": {"meaning": "听", "words": ["audio", "audience", "audible", "audition", "auditorium", "inaudible"]},
    "bio": {"meaning": "生命", "words": ["biology", "biography", "antibiotic", "biodegradable", "biochemistry", "biopsy"]},
    "cap": {"meaning": "拿，抓", "words": ["capture", "capable", "capacity", "captive", "accept", "except", "receive", "receipt", "recipe", "anticipate"]},
    "ced": {"meaning": "走，让步", "words": ["proceed", "succeed", "exceed", "precede", "recede", "concede", "access", "process", "necessary"]},
    "cred": {"meaning": "相信", "words": ["credit", "credible", "incredible", "credentials", "creed", "creditor", "accredit"]},
    "creat": {"meaning": "创造", "words": ["create", "creation", "creative", "creativity", "creator", "creature", "recreate", "procreate"]},
    "dict": {"meaning": "说", "words": ["dictate", "dictionary", "predict", "contradict", "verdict", "addict", "indicate", "dedicate"]},
    "duc": {"meaning": "引导", "words": ["produce", "reduce", "introduce", "conduct", "educate", "deduce", "induce", "seduce", "abduct"]},
    "fac": {"meaning": "做，制造", "words": ["factory", "factor", "fact", "manufacture", "facilitate", "faculty", "artifact", "artificial", "affect", "effect", "infect", "perfect", "defect"]},
    "fer": {"meaning": "带，搬运", "words": ["transfer", "refer", "prefer", "offer", "differ", "suffer", "confer", "infer", "defer"]},
    "fin": {"meaning": "结束，边界", "words": ["final", "finish", "finite", "infinite", "define", "refine", "confine", "finance", "efinite"]},
    "form": {"meaning": "形状", "words": ["form", "format", "formal", "formula", "reform", "transform", "inform", "conform", "perform", "uniform", "deform"]},
    "gen": {"meaning": "产生，种类", "words": ["generate", "generation", "general", "generous", "genius", "gene", "genetic", "gender", "genuine", "degenerate", "regenerate"]},
    "graph": {"meaning": "写，画", "words": ["graph", "graphic", "photograph", "telegraph", "biography", "geography", "autograph", "paragraph"]},
    "ject": {"meaning": "扔，投", "words": ["project", "reject", "inject", "subject", "object", "eject", "trajectory", "interjection"]},
    "log": {"meaning": "话，学说", "words": ["logic", "dialogue", "catalog", "apology", "biology", "psychology", "technology", "ecology", "ideology"]},
    "man": {"meaning": "手", "words": ["manual", "manage", "manufacture", "manipulate", "manifest", "manicure", "manuscript"]},
    "mem": {"meaning": "记忆", "words": ["memory", "remember", "memorial", "memorize", "memorable", "commemorate", "memoir"]},
    "mit": {"meaning": "送，发", "words": ["commit", "submit", "permit", "admit", "emit", "omit", "transmit", "remit", "intermittent"]},
    "mob": {"meaning": "移动", "words": ["mobile", "mobilize", "automobile", "immobile", "mobility"]},
    "mort": {"meaning": "死", "words": ["mortal", "immortal", "mortality", "mortgage", "mortify", "mortician"]},
    "mov": {"meaning": "移动", "words": ["move", "movement", "remove", "movie", "movable", "immovable", "removal"]},
    "pend": {"meaning": "悬挂，支付", "words": ["depend", "suspend", "spend", "pending", "appendix", "independent", "expenditure", "impending"]},
    "phon": {"meaning": "声音", "words": ["phone", "telephone", "microphone", "symphony", "phonetic", "phonics", "euphony"]},
    "port": {"meaning": "搬运，港口", "words": ["port", "report", "import", "export", "transport", "support", "portable", "portfolio", "deport"]},
    "pos": {"meaning": "放置", "words": ["position", "positive", "compose", "oppose", "propose", "dispose", "expose", "impose", "deposit", "suppose"]},
    "press": {"meaning": "压", "words": ["press", "pressure", "express", "impress", "compress", "depress", "oppress", "suppress", "repress"]},
    "rupt": {"meaning": "破裂", "words": ["rupt", "erupt", "corrupt", "disrupt", "interrupt", "abrupt", "bankrupt", "rupture"]},
    "scrib": {"meaning": "写", "words": ["scribe", "describe", "subscribe", "prescribe", "inscribe", "manuscript", "script", "scripture", "transcript"]},
    "sens": {"meaning": "感觉", "words": ["sense", "sensible", "sensitive", "sensation", "consent", "consensus", "nonsense", "resent"]},
    "spect": {"meaning": "看", "words": ["spectacle", "inspect", "expect", "respect", "suspect", "prospect", "aspect", "perspective", "spectrum", "spectator"]},
    "struct": {"meaning": "建造", "words": ["structure", "construct", "destruct", "instruct", "obstruct", "infrastructure", "restructure"]},
    "tact": {"meaning": "接触", "words": ["contact", "intact", "tactile", "tact", "tactics"]},
    "tele": {"meaning": "远", "words": ["telephone", "television", "telegram", "telescope", "telepathy", "teleport", "telecommunication"]},
    "tend": {"meaning": "伸展", "words": ["tend", "extend", "intend", "attend", "pretend", "contend", "tendency", "tension", "intense"]},
    "tract": {"meaning": "拉，拽", "words": ["attract", "contract", "extract", "subtract", "distract", "tractor", "abstract", "retract", "protract"]},
    "uni": {"meaning": "一", "words": ["unit", "unite", "unity", "unique", "uniform", "universe", "university", "union", "unify", "unanimous"]},
    "vers": {"meaning": "转", "words": ["verse", "version", "reverse", "converse", "diverse", "universe", "controversy", "anniversary", "versatile", "adverse"]},
    "vid": {"meaning": "看", "words": ["video", "evident", "provide", "divide", "individual", "invisible", "vision", "revise", "supervise"]},
    "voc": {"meaning": "声音，叫", "words": ["voice", "vocal", "vocabulary", "advocate", "provoke", "invoke", "revoke", "vocation", "evoke"]},
}


class WordFamilyService:
    """派生词群组服务"""

    @staticmethod
    def get_word_families_from_api(word: str) -> Optional[Dict]:
        """
        从 Free Dictionary API 获取单词信息。
        返回包含词源、派生词等信息的字典。
        """
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0]
        except Exception as e:
            print(f"Dictionary API error: {e}")
        return None

    @staticmethod
    def extract_root_from_word(word: str) -> List[Dict]:
        """
        从单词中识别可能的词根。
        返回匹配到的词根列表。
        """
        word_lower = word.lower()
        matched_roots = []

        for root, info in COMMON_ROOTS.items():
            # 检查单词是否包含该词根
            if root in word_lower:
                # 确保词根在合理位置（不是偶然匹配）
                # 简单规则：词根至少占单词30%长度
                if len(root) >= len(word_lower) * 0.3:
                    matched_roots.append({
                        'root': root,
                        'meaning': info['meaning'],
                        'derivatives': info['words']
                    })

        return matched_roots

    @staticmethod
    def get_derivatives(word: str, db_manager=None) -> Dict:
        """
        获取单词的派生词信息。

        返回格式：
        {
            'word': 'create',
            'families': [
                {
                    'root': 'creat',
                    'meaning': '创造',
                    'derivatives': ['creative', 'creation', ...],
                    'in_vocab': ['creative'],  # 已在词库中的
                    'not_in_vocab': ['creation', ...]  # 不在词库中的
                }
            ]
        }
        """
        result = {
            'word': word,
            'families': []
        }

        # 1. 先从本地词根库匹配
        local_matches = WordFamilyService.extract_root_from_word(word)

        # 2. 如果有数据库连接，查询已存储的词根关联
        stored_families = []
        if db_manager:
            stored_families = db_manager.get_word_family(word)

        # 3. 合并本地匹配和数据库存储的结果
        processed_roots = set()

        # 处理本地匹配的词根
        for match in local_matches:
            root = match['root']
            if root in processed_roots:
                continue
            processed_roots.add(root)

            derivatives = [w for w in match['derivatives'] if w.lower() != word.lower()]

            family_info = {
                'root': root,
                'meaning': match['meaning'],
                'derivatives': derivatives,
                'in_vocab': [],
                'not_in_vocab': []
            }

            # 如果有数据库，检查哪些派生词已在词库中
            if db_manager:
                for deriv in derivatives:
                    if db_manager.get_word(deriv):
                        family_info['in_vocab'].append(deriv)
                    else:
                        family_info['not_in_vocab'].append(deriv)

                # 将词根-单词关联存入数据库
                all_words = [word] + derivatives
                db_manager.add_word_families_batch(root, match['meaning'], all_words)
            else:
                family_info['not_in_vocab'] = derivatives

            result['families'].append(family_info)

        # 处理数据库中存储但本地未匹配的词根
        for stored in stored_families:
            root = stored['root']
            if root in processed_roots:
                continue
            processed_roots.add(root)

            family_info = {
                'root': root,
                'meaning': stored.get('root_meaning', ''),
                'derivatives': [],
                'in_vocab': [],
                'not_in_vocab': []
            }

            for word_info in stored.get('words', []):
                w = word_info['word']
                family_info['derivatives'].append(w)
                if word_info['in_vocab']:
                    family_info['in_vocab'].append(w)
                else:
                    family_info['not_in_vocab'].append(w)

            result['families'].append(family_info)

        return result

    @staticmethod
    def parse_roots_text(roots_text: str) -> List[Dict]:
        """
        解析有道词典返回的词根文本，提取结构化信息。
        """
        if not roots_text:
            return []

        results = []

        # 尝试匹配常见格式：
        # "[词根] creat = 创造" 或 "词根：-creat- 创造"
        patterns = [
            r'\[词根\]\s*(\w+)\s*[=:：]\s*(.+?)(?:\||$)',
            r'词根[：:]\s*-?(\w+)-?\s+(.+?)(?:\||$)',
            r'(\w{3,})\s*[=:：]\s*(.+?)(?:,|;|$)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, roots_text)
            for match in matches:
                root = match[0].strip().lower()
                meaning = match[1].strip()
                if root and meaning and root in COMMON_ROOTS:
                    results.append({
                        'root': root,
                        'meaning': meaning,
                        'derivatives': COMMON_ROOTS[root]['words']
                    })

        return results
