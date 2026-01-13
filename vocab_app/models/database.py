import sqlite3
import json
import os
import time
from datetime import datetime, timedelta

class DatabaseManager:
    def __init__(self, db_path="vocab.db", json_path="vocab.json"):
        self.db_path = db_path
        self.json_path = json_path
        self.init_db()
        self.check_schema_updates()
        self.migrate_from_json()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

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

        # Create indexes for frequently queried columns to improve performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_word ON words(word)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_next_review_time ON words(next_review_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mastered ON words(mastered)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stage ON words(stage)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_word_families_root ON word_families(root)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_word_families_word ON word_families(word)')

        conn.commit()
        conn.close()

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
        finally:
            conn.close()

    def migrate_from_json(self):
        """Migrate data from vocab.json if DB is empty."""
        if not os.path.exists(self.json_path):
            return

        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if DB is empty
        cursor.execute('SELECT count(*) FROM words')
        if cursor.fetchone()[0] > 0:
            conn.close()
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
        finally:
            conn.close()

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
        finally:
            conn.close()

    def get_word(self, word):
        """Get a single word as dict."""
        conn = self.get_connection()
        try:
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
        finally:
            conn.close()

    def get_all_words(self):
        """Get all words as list of dicts."""
        conn = self.get_connection()
        try:
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
        finally:
            conn.close()

    def update_context(self, word, en, cn):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('UPDATE words SET context_en = ?, context_cn = ? WHERE word = ?', (en, cn, word))
            conn.commit()
        finally:
            conn.close()

    def delete_word(self, word):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM words WHERE word = ?', (word,))
            conn.commit()
        finally:
            conn.close()

    def mark_word_mastered(self, word):
        """Mark a word as mastered."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('UPDATE words SET mastered = 1 WHERE word = ?', (word,))
            conn.commit()
        finally:
            conn.close()

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
        conn.close()

    def update_sm2_status(self, word, easiness, interval, repetitions, next_time, rating):
        """Update fields after a review using SM-2 algorithm."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 判断是否掌握 (例如间隔超过 180 天或重复次数超过 7 次，可自定义)
        # 这里为了保持与旧逻辑一致，暂时不自动设为 mastered，除非间隔极大
        mastered = 1 if interval > 180 else 0

        cursor.execute('''
            UPDATE words
            SET easiness = ?, interval = ?, repetitions = ?, next_review_time = ?,
                mastered = ?, review_count = review_count + 1
            WHERE word = ?
        ''', (easiness, interval, repetitions, next_time, mastered, word))

        # Log history
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT id FROM words WHERE word = ?', (word,))
        res = cursor.fetchone()
        if res:
            wid = res[0]
            cursor.execute('INSERT INTO review_history (word_id, review_date, rating) VALUES (?, ?, ?)', (wid, today, rating))

        conn.commit()
        conn.close()

    def get_review_heatmap_data(self):
        """获取过去一年的复习热力图数据 {date: count}"""
        conn = self.get_connection()
        try:
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
        finally:
            conn.close()

    def get_word_review_history(self, word_id):
        """Get review history for a specific word"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT review_date, rating FROM review_history WHERE word_id = ? ORDER BY review_date', (word_id,))
            rows = cursor.fetchall()
            return rows
        finally:
            conn.close()

    def get_statistics(self):
        """获取学习统计信息"""
        conn = self.get_connection()
        try:
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
        finally:
            conn.close()

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
        finally:
            conn.close()

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
        finally:
            conn.close()

    def get_word_family(self, word):
        """Get all words in the same family as the given word."""
        conn = self.get_connection()
        try:
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
        finally:
            conn.close()

    def get_roots_for_word(self, word):
        """Get the roots associated with a word."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT root, root_meaning FROM word_families WHERE word = ?', (word.lower(),))
            rows = cursor.fetchall()
            return [{'root': r[0], 'meaning': r[1]} for r in rows]
        finally:
            conn.close()
