import csv
import json
import os
from datetime import datetime

class ExportService:
    @staticmethod
    def export_to_csv(filepath, words):
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['Word', 'Phonetic', 'Meaning', 'Example', 'Context_En', 'Context_Cn', 'Date_Added', 'Review_Count', 'Mastered'])
                for w in words:
                    writer.writerow([
                        w['word'],
                        w.get('phonetic', ''),
                        w.get('meaning', ''),
                        w.get('example', ''),
                        w.get('context_en', ''),
                        w.get('context_cn', ''),
                        w.get('date', ''),
                        w.get('review_count', 0),
                        1 if w.get('mastered') else 0
                    ])
            return True, "导出成功"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def import_from_csv(filepath, db):
        try:
            count = 0
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Basic mapping
                    word_data = {
                        'word': row.get('Word'),
                        'phonetic': row.get('Phonetic', ''),
                        'meaning': row.get('Meaning', ''),
                        'example': row.get('Example', ''),
                        'context_en': row.get('Context_En', ''),
                        'context_cn': row.get('Context_Cn', ''),
                        'date': row.get('Date_Added', datetime.now().strftime('%Y-%m-%d')),
                    }
                    if not word_data['word']: continue

                    # Try to add
                    if db.add_word(word_data):
                        # If added successfully, update context if present
                        if word_data['context_en']:
                            db.update_context(word_data['word'], word_data['context_en'], word_data['context_cn'])
                        count += 1
            return True, f"成功导入 {count} 个单词"
        except Exception as e:
            return False, str(e)
