import sqlite3
import json
import os
import time
import threading
from datetime import datetime, timedelta

class DatabaseManager:
    """
    SQLite 数据库管理器，使用线程本地存储的长连接。

    优化策略：
    - 每个线程维护一个独立的数据库连接（线程本地存储）
    - 避免频繁创建/关闭连接的开销
    - 线程安全，支持多线程环境（如词典查询线程）
    """

    def __init__(self, db_path="vocab.db", json_path="vocab.json"):
        self.db_path = db_path
        self.json_path = json_path
        self._local = threading.local()  # 线程本地存储
        self._lock = threading.Lock()     # 用于初始化时的锁

        self.init_db()
        self.check_schema_updates()
        self.migrate_from_json()

    def get_connection(self):
        """
        获取当前线程的数据库连接。
        每个线程使用独立的连接，避免线程安全问题。
        """
        # 检查当前线程是否已有连接
        conn = getattr(self._local, 'connection', None)

        if conn is None:
            # 当前线程没有连接，创建新连接
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")  # 使用 WAL 模式提升并发性能
            conn.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全
            self._local.connection = conn

        return conn

    def close_connection(self):
        """关闭当前线程的数据库连接。"""
        conn = getattr(self._local, 'connection', None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.connection = None

    def execute(self, query, params=(), fetch=False, commit=True):
        """Helper to execute a single query with automatic connection handling."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
            if fetch:
                return cursor.fetchall()
            return None
        except sqlite3.Error as e:
            # 连接可能已损坏，尝试重新连接
            if "database is locked" in str(e) or "disk I/O error" in str(e):
                self.close_connection()
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute(query, params)
                if commit:
                    conn.commit()
                if fetch:
                    return cursor.fetchall()
                return None
            raise

    def execute_many(self, queries):
        """Execute multiple queries in a single transaction."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            for query, params in queries:
                cursor.execute(query, params)
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise

    def init_db(self):
        """Initialize the database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Main words table
        # We pre-add SM-2 algorithm fields (easiness, interval, repetitions) for Step 2
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE NOT NULL,
                phonetic TEXT,
                meaning TEXT,
                example TEXT,
                roots TEXT,          -- New: Root/Affix
                synonyms TEXT,       -- New: Synonyms
                context_en TEXT,
                context_cn TEXT,
                date_added TEXT,

                next_review_time REAL DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                mastered INTEGER DEFAULT 0,  -- 0: Learning, 1: Mastered

                -- Fields for Old Logic (Stage) and Future SM-2
                stage INTEGER DEFAULT 0,      -- Currently used for "1,2,4,7..." logic
                easiness REAL DEFAULT 2.5,    -- For SM-2
                interval INTEGER DEFAULT 0,   -- For SM-2
                repetitions INTEGER DEFAULT 0, -- For SM-2
                tags TEXT                      -- New: Exam tags (CET4, GRE, etc.)
            )
        ''')

        # History table for Heatmap (Step 3 preparation)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS review_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER,
                review_date TEXT,  -- YYYY-MM-DD
                rating INTEGER,    -- 0=Forgot, 1=Remembered (Simple) / 1-4 (SM-2)
                FOREIGN KEY(word_id) REFERENCES words(id)
            )
        ''')

        # Word families table for derivative words (派生词群组)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS word_families (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                root TEXT NOT NULL,           -- 词根 (e.g., "creat")
                root_meaning TEXT,            -- 词根释义 (e.g., "创造")
                word TEXT NOT NULL,           -- 单词 (e.g., "create")
                UNIQUE(root, word)
            )
        ''')

        # Study Statistics table (Step 4: Review Timer & Stats)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,    -- YYYY-MM-DD
                total_duration INTEGER DEFAULT 0, -- Seconds
                review_count INTEGER DEFAULT 0
            )
        ''')

        # Create indexes for frequently queried columns to improve performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_word ON words(word)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_next_review_time ON words(next_review_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mastered ON words(mastered)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stage ON words(stage)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_word_families_root ON word_families(root)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_word_families_word ON word_families(word)')

        # Dictionary cache table (持久化词典查询缓存)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dict_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                source TEXT NOT NULL,
                data TEXT,
                created_at REAL,
                UNIQUE(word, source)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dict_cache_word ON dict_cache(word)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dict_cache_created ON dict_cache(created_at)')

        conn.commit()
        # 注意：不再关闭连接，使用长连接

    def check_schema_updates(self):
        """Check and update database schema for new columns."""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Check if 'roots' column exists
            cursor.execute("PRAGMA table_info(words)")
            columns = [info[1] for info in cursor.fetchall()]

            if 'roots' not in columns:
                print("Adding 'roots' column to words table...")
                cursor.execute("ALTER TABLE words ADD COLUMN roots TEXT")

            if 'synonyms' not in columns:
                print("Adding 'synonyms' column to words table...")
                cursor.execute("ALTER TABLE words ADD COLUMN synonyms TEXT")

            if 'tags' not in columns:
                print("Adding 'tags' column to words table...")
                cursor.execute("ALTER TABLE words ADD COLUMN tags TEXT")

            conn.commit()
        except Exception as e:
            print(f"Schema update error: {e}")
        # 注意：不再关闭连接，使用长连接

    def migrate_from_json(self):
        """Migrate data from vocab.json if DB is empty."""
        if not os.path.exists(self.json_path):
            return

        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if DB is empty
        cursor.execute('SELECT count(*) FROM words')
        if cursor.fetchone()[0] > 0:
            return # Already has data, skip migration

        print("Migrating data from JSON to SQLite...")
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO words (
                            word, phonetic, meaning, example, 
                            context_en, context_cn, date_added, 
                            next_review_time, review_count, mastered, stage
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('word'),
                        item.get('phonetic', ''),
                        item.get('meaning', ''),
                        item.get('example', ''),
                        item.get('context_en', ''),
                        item.get('context_cn', ''),
                        item.get('date', datetime.now().strftime('%Y-%m-%d')),
                        item.get('next_review_time', 0),
                        item.get('review_count', 0),
                        1 if item.get('mastered') else 0,
                        item.get('stage', 0)
                    ))
                except Exception as e:
                    print(f"Skipping error word {item.get('word')}: {e}")
            
            conn.commit()
            print(f"Migration complete. {len(data)} words imported.")

            # Optional: Rename json file to backup
            # os.rename(self.json_path, self.json_path + ".bak")

        except Exception as e:
            print(f"Migration failed: {e}")
        # 注意：不再关闭连接，使用长连接

    # --- CRUD Operations ---

    def add_word(self, data):
        """Add a new word dictionary."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO words (word, phonetic, meaning, example, roots, synonyms, tags, date_added, next_review_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['word'],
                data.get('phonetic', ''),
                data.get('meaning', ''),
                data.get('example', ''),
                data.get('roots', ''),
                data.get('synonyms', ''),
                data.get('tags', ''),
                data.get('date', datetime.now().strftime('%Y-%m-%d')),
                0
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False # Already exists

    def get_word(self, word):
        """Get a single word as dict."""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM words WHERE word = ?', (word,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            d['mastered'] = bool(d['mastered'])
            d['date'] = d['date_added']
            return d
        return None

    def get_all_words(self):
        """Get all words as list of dicts."""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM words ORDER BY next_review_time ASC')
        rows = cursor.fetchall()

        result = []
        for row in rows:
            d = dict(row)
            d['mastered'] = bool(d['mastered'])
            d['date'] = d['date_added']
            result.append(d)
        return result

    def get_all_tags(self):
        """Get all unique tags from the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT tags FROM words WHERE tags IS NOT NULL AND tags != ""')
        rows = cursor.fetchall()
        tags_set = set()
        for row in rows:
            if row[0]:
                for tag in row[0].split(','):
                    tag = tag.strip()
                    if tag:
                        tags_set.add(tag)
        return sorted(list(tags_set))

    def update_context(self, word, en, cn):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE words SET context_en = ?, context_cn = ? WHERE word = ?', (en, cn, word))
        conn.commit()

    def delete_word(self, word):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM words WHERE word = ?', (word,))
        conn.commit()

    def mark_word_mastered(self, word):
        """Mark a word as mastered."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE words SET mastered = 1 WHERE word = ?', (word,))
        conn.commit()

    def update_review_status(self, word, stage, next_time, mastered, review_count_inc=True):
        """Update fields after a review."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        sql = '''
            UPDATE words 
            SET stage = ?, next_review_time = ?, mastered = ?
        '''
        params = [stage, next_time, 1 if mastered else 0]
        
        if review_count_inc:
            sql += ', review_count = review_count + 1'
            
        sql += ' WHERE word = ?'
        params.append(word)
        
        cursor.execute(sql, tuple(params))
        
        # Log history (For Step 3 Heatmap)
        today = datetime.now().strftime('%Y-%m-%d')
        # Get word ID first
        cursor.execute('SELECT id FROM words WHERE word = ?', (word,))
        res = cursor.fetchone()
        if res:
            wid = res[0]
            # Simple rating for now: 1 if stage increased (remembered), 0 if reset (forgot)
            # This is an approximation since we don't pass the explicit "ok/fail" bool here but derive from stage
            # Actually, let's just log it.
            cursor.execute('INSERT INTO review_history (word_id, review_date, rating) VALUES (?, ?, ?)', (wid, today, 1))

        conn.commit()

    def update_sm2_status(self, word, easiness, interval, repetitions, next_time, rating):
        """Update fields after a review using SM-2 algorithm."""
        # 判断是否掌握 (例如间隔超过 180 天或重复次数超过 7 次，可自定义)
        # 这里为了保持与旧逻辑一致，暂时不自动设为 mastered，除非间隔极大
        mastered = 1 if interval > 180 else 0

        self.execute('''
            UPDATE words
            SET easiness = ?, interval = ?, repetitions = ?, next_review_time = ?,
                mastered = ?, review_count = review_count + 1
            WHERE word = ?
        ''', (easiness, interval, repetitions, next_time, mastered, word))

        # Log history
        today = datetime.now().strftime('%Y-%m-%d')
        res = self.execute('SELECT id FROM words WHERE word = ?', (word,), fetch=True, commit=False)
        if res and res[0]:
            self.execute(
                'INSERT INTO review_history (word_id, review_date, rating) VALUES (?, ?, ?)',
                (res[0][0], today, rating)
            )

    def get_review_heatmap_data(self):
        """获取过去一年的复习热力图数据 {date: count}"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 获取一年前的日期
        one_year_ago = (datetime.now() - timedelta(days=366)).strftime('%Y-%m-%d')

        cursor.execute('''
            SELECT review_date, COUNT(*)
            FROM review_history
            WHERE review_date >= ?
            GROUP BY review_date
        ''', (one_year_ago,))

        rows = cursor.fetchall()
        return {row[0]: row[1] for row in rows}

    def get_word_review_history(self, word_id):
        """Get review history for a specific word"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT review_date, rating FROM review_history WHERE word_id = ? ORDER BY review_date', (word_id,))
        rows = cursor.fetchall()
        return rows

    def get_statistics(self):
        """获取学习统计信息"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 总单词数
        cursor.execute('SELECT COUNT(*) FROM words')
        total = cursor.fetchone()[0]

        # 已掌握数量
        cursor.execute('SELECT COUNT(*) FROM words WHERE mastered = 1')
        mastered = cursor.fetchone()[0]

        # 今日待复习数量
        now_ts = time.time()
        cursor.execute('SELECT COUNT(*) FROM words WHERE mastered = 0 AND next_review_time <= ?', (now_ts,))
        due_today = cursor.fetchone()[0]

        # 学习中的单词
        learning = total - mastered

        return {
            'total': total,
            'mastered': mastered,
            'learning': learning,
            'due_today': due_today
        }

    def log_study_session(self, duration_seconds, review_count=0):
        """Log a study session duration."""
        if duration_seconds <= 0: return
        
        today = datetime.now().strftime('%Y-%m-%d')
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Upsert using SQLite syntax (INSERT OR IGNORE then UPDATE, or newer ON CONFLICT)
            # Standard way: Try update, if 0 rows, insert
            cursor.execute('''
                UPDATE study_stats 
                SET total_duration = total_duration + ?, review_count = review_count + ?
                WHERE date = ?
            ''', (duration_seconds, review_count, today))
            
            if cursor.rowcount == 0:
                cursor.execute('''
                    INSERT INTO study_stats (date, total_duration, review_count)
                    VALUES (?, ?, ?)
                ''', (today, duration_seconds, review_count))
            
            conn.commit()
        except Exception as e:
            print(f"Log study session error: {e}")

    def get_total_study_time(self):
        """Get total study time in seconds across all history."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(total_duration) FROM study_stats")
        res = cursor.fetchone()
        return res[0] if res and res[0] else 0

    # --- Word Family Operations (派生词群组) ---

    def add_word_family(self, root, root_meaning, word):
        """Add a word to a word family."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO word_families (root, root_meaning, word)
                VALUES (?, ?, ?)
            ''', (root.lower(), root_meaning, word.lower()))
            conn.commit()
            return True
        except Exception as e:
            print(f"Add word family error: {e}")
            return False

    def add_word_families_batch(self, root, root_meaning, words):
        """Add multiple words to a word family."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            for word in words:
                cursor.execute('''
                    INSERT OR IGNORE INTO word_families (root, root_meaning, word)
                    VALUES (?, ?, ?)
                ''', (root.lower(), root_meaning, word.lower()))
            conn.commit()
            return True
        except Exception as e:
            print(f"Add word families batch error: {e}")
            return False

    def get_word_family(self, word):
        """Get all words in the same family as the given word."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # First find the root(s) for this word
        cursor.execute('SELECT DISTINCT root, root_meaning FROM word_families WHERE word = ?', (word.lower(),))
        roots = cursor.fetchall()

        if not roots:
            return []

        # Get all words that share these roots
        result = []
        for root, root_meaning in roots:
            cursor.execute('''
                SELECT wf.word,
                       CASE WHEN w.word IS NOT NULL THEN 1 ELSE 0 END as in_vocab
                FROM word_families wf
                LEFT JOIN words w ON LOWER(w.word) = wf.word
                WHERE wf.root = ?
                ORDER BY wf.word
            ''', (root,))
            family_words = cursor.fetchall()
            result.append({
                'root': root,
                'root_meaning': root_meaning,
                'words': [{'word': w[0], 'in_vocab': bool(w[1])} for w in family_words if w[0] != word.lower()]
            })

        return result

    def get_roots_for_word(self, word):
        """Get the roots associated with a word."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT root, root_meaning FROM word_families WHERE word = ?', (word.lower(),))
        rows = cursor.fetchall()
        return [{'root': r[0], 'meaning': r[1]} for r in rows]

    # --- 搜索与分页 (性能优化) ---

    def search_words(self, keyword="", tag_filter="", mastered_filter=None, status_filter=None, sort_by="next_review_time", sort_order="ASC", limit=50, offset=0):
        """
        在数据库层进行搜索和过滤，避免内存中遍历全部单词。

        Args:
            keyword: 搜索关键词（匹配 word 或 meaning）
            tag_filter: 标签过滤（如 "CET4", "GRE"）
            mastered_filter: 掌握状态过滤 (True/False/None)
            status_filter: 复习状态过滤 ("due"=待复习, "new"=新单词, "learning"=学习中, None=全部)
            sort_by: 排序字段
            sort_order: 排序方向 (ASC/DESC)
            limit: 返回数量限制
            offset: 偏移量（用于分页）

        Returns:
            (list[dict], int): (单词列表, 总匹配数量)
        """
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 构建 WHERE 子句
        conditions = []
        params = []

        if keyword:
            conditions.append("(word LIKE ? OR meaning LIKE ?)")
            like_pattern = f"%{keyword}%"
            params.extend([like_pattern, like_pattern])

        if tag_filter:
            conditions.append("tags LIKE ?")
            params.append(f"%{tag_filter}%")

        if mastered_filter is not None:
            conditions.append("mastered = ?")
            params.append(1 if mastered_filter else 0)

        # 复习状态过滤（基于 next_review_time）
        if status_filter:
            now_ts = time.time()
            if status_filter == "due":
                # 待复习：未掌握 且 next_review_time > 0 且 <= 当前时间
                conditions.append("mastered = 0 AND next_review_time > 0 AND next_review_time <= ?")
                params.append(now_ts)
            elif status_filter == "new":
                # 新单词：next_review_time = 0
                conditions.append("next_review_time = 0")
            elif status_filter == "learning":
                # 学习中：未掌握 且 next_review_time > 当前时间
                conditions.append("mastered = 0 AND next_review_time > ?")
                params.append(now_ts)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 验证排序字段（防止 SQL 注入）
        valid_sort_fields = {"word", "next_review_time", "date_added", "review_count", "mastered", "easiness", "interval"}
        if sort_by not in valid_sort_fields:
            sort_by = "next_review_time"
        if sort_order.upper() not in ("ASC", "DESC"):
            sort_order = "ASC"

        # 查询总数
        count_sql = f"SELECT COUNT(*) FROM words WHERE {where_clause}"
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]

        # 查询数据
        query_sql = f"""
            SELECT * FROM words
            WHERE {where_clause}
            ORDER BY {sort_by} {sort_order}
            LIMIT ? OFFSET ?
        """
        cursor.execute(query_sql, params + [limit, offset])
        rows = cursor.fetchall()

        result = []
        for row in rows:
            d = dict(row)
            d['mastered'] = bool(d['mastered'])
            d['date'] = d['date_added']
            result.append(d)

        return result, total_count

    def get_words_count(self):
        """获取单词总数"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM words')
        return cursor.fetchone()[0]

    # --- 词典缓存操作 (Dict Cache) ---

    def get_dict_cache(self, word, source, ttl=86400):
        """
        获取词典缓存。

        Args:
            word: 单词
            source: 词典源标识 (bing, cambridge, freedict 等)
            ttl: 缓存有效期（秒），默认 24 小时

        Returns:
            缓存的数据字典，或 None（未找到/已过期）
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        now = time.time()
        cursor.execute('''
            SELECT data, created_at FROM dict_cache
            WHERE word = ? AND source = ?
        ''', (word.lower(), source))

        row = cursor.fetchone()
        if row:
            data_json, created_at = row
            # 检查是否过期
            if now - created_at < ttl:
                try:
                    return json.loads(data_json)
                except (json.JSONDecodeError, TypeError):
                    return None
            else:
                # 过期，删除旧缓存
                cursor.execute('DELETE FROM dict_cache WHERE word = ? AND source = ?',
                              (word.lower(), source))
                conn.commit()
        return None

    def set_dict_cache(self, word, source, data):
        """
        设置词典缓存。

        Args:
            word: 单词
            source: 词典源标识
            data: 要缓存的数据字典
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            data_json = json.dumps(data, ensure_ascii=False)
            cursor.execute('''
                INSERT OR REPLACE INTO dict_cache (word, source, data, created_at)
                VALUES (?, ?, ?, ?)
            ''', (word.lower(), source, data_json, time.time()))
            conn.commit()
        except Exception as e:
            print(f"Set dict cache error: {e}")

    def clear_expired_dict_cache(self, ttl=86400):
        """
        清理过期的词典缓存。

        Args:
            ttl: 缓存有效期（秒），默认 24 小时

        Returns:
            删除的记录数
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        expired_time = time.time() - ttl
        cursor.execute('DELETE FROM dict_cache WHERE created_at < ?', (expired_time,))
        deleted = cursor.rowcount
        conn.commit()
        return deleted

    def get_dict_cache_stats(self):
        """获取词典缓存统计信息"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM dict_cache')
        total = cursor.fetchone()[0]

        # 按来源统计
        cursor.execute('SELECT source, COUNT(*) FROM dict_cache GROUP BY source')
        by_source = {row[0]: row[1] for row in cursor.fetchall()}

        return {'total': total, 'by_source': by_source}

    def clear_all_dict_cache(self):
        """清空所有词典缓存"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM dict_cache')
        deleted = cursor.rowcount
        conn.commit()
        return deleted
