"""
数据库清理脚本
1. 清理单词字段中的标点符号
2. 删除重复的带标点版本
"""
import sqlite3
import re
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'vocab.db')

def clean_word_text(text):
    """Remove leading/trailing punctuation from word"""
    if not text:
        return text
    word = text.strip()
    # Remove leading and trailing punctuation
    word = re.sub(r'^[^\w]+|[^\w]+$', '', word, flags=re.UNICODE)
    return word

def main():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 检查单词字段中包含标点的条目
    cursor.execute("SELECT word, meaning FROM words")
    rows = cursor.fetchall()
    
    print(f"\n找到 {len(rows)} 个单词\n")
    
    # 获取所有纯净单词（用于检查重复）
    cursor.execute("SELECT word FROM words")
    all_words = set(row[0] for row in cursor.fetchall())
    
    problematic_words = []
    duplicates_to_delete = []
    
    for word, meaning in rows:
        cleaned = clean_word_text(word)
        
        # 检查单词是否需要清理
        if word != cleaned:
            # 检查清理后的版本是否已存在
            if cleaned in all_words and cleaned != word:
                duplicates_to_delete.append(word)
            else:
                problematic_words.append((word, cleaned))
    
    # 报告问题
    if duplicates_to_delete:
        print("=" * 50)
        print("⚠️ 发现重复的带标点单词（将被删除）:")
        print("=" * 50)
        for word in duplicates_to_delete:
            cleaned = clean_word_text(word)
            print(f"  删除 '{word}' (因为 '{cleaned}' 已存在)")
    
    if problematic_words:
        print("\n" + "=" * 50)
        print("⚠️ 需要清理标点的单词:")
        print("=" * 50)
        for old, new in problematic_words[:20]:
            print(f"  '{old}' -> '{new}'")
    
    # 执行清理
    total_to_fix = len(duplicates_to_delete) + len(problematic_words)
    if total_to_fix > 0:
        print(f"\n总共 {total_to_fix} 个需要处理")
        response = input("是否自动修复？(y/n): ")
        
        if response.lower() == 'y':
            # 删除重复项
            for word in duplicates_to_delete:
                cursor.execute("DELETE FROM words WHERE word = ?", (word,))
                print(f"  已删除: {word}")
            
            # 清理标点
            for old_word, new_word in problematic_words:
                cursor.execute("UPDATE words SET word = ? WHERE word = ?", (new_word, old_word))
                print(f"  已修复: {old_word} -> {new_word}")
            
            conn.commit()
            print(f"\n✅ 已处理 {total_to_fix} 个单词")
    else:
        print("✅ 没有发现需要清理的问题")
    
    conn.close()
    print("\n完成!")

if __name__ == "__main__":
    main()
