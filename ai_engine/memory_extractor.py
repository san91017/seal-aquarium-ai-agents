import os
import json
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 載入環境變數
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 初始化 Gemini 與 MongoDB
client = genai.Client(api_key=GEMINI_API_KEY)
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['aquarium_db']
memories_collection = db['memories']

def extract_and_store_event(subject_id: str, object_id: str, context_text: str):
    """
    將對話紀錄壓縮成結構化的「事件記憶」，並存入 MongoDB。
    
    :param subject_id: 發起行動的人 (例如: tourist_abc 或 seal_02)
    :param object_id: 承受行動的人 (例如: seal_01)
    :param context_text: 完整的對話或行為描述
    """
    
    # 建立給 LLM 的系統指令，強制要求輸出特定 JSON 結構
    system_instruction = """
    你是一個心理學觀察者，正在記錄虛擬水族館中海豹與遊客/其他海豹的互動。
    請閱讀提供的對話紀錄，並將其提取為一個結構化的「事件」。
    
    請以 JSON 格式輸出，必須包含以下欄位：
    - action: (字串) 用一句簡短的話描述發生了什麼事，例如「嘲笑海豹太胖」、「關心海豹的疲勞」。
    - emotion: (字串) 承受行動者(object)當下可能產生的情緒，例如 "happy", "angry", "sad", "annoyed", "neutral"。
    - importance_score: (整數 1-10) 評估這件事對承受者的重要性。
        - 1-2分：日常閒聊（例如打招呼、問天氣）。
        - 3-5分：有趣的對話或輕微的抱怨。
        - 6-8分：強烈的情感波動（例如被稱讚、被嚴厲批評、得知重大八卦）。
        - 9-10分：改變一生的創傷或極度狂喜（極少出現）。
    """

    print(f"🕵️‍♂️ [記憶提取中] 分析 {subject_id} 對 {object_id} 的行為...")
    
    try:
        # 呼叫 Gemini (使用 Flash 模型即可，因為任務單純且需要快速)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"對話紀錄：\n{context_text}",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2, # 溫度調低，我們需要穩定的 JSON 輸出
                response_mime_type="application/json", # 強制回傳 JSON
            )
        )
        
        # 解析 Gemini 回傳的 JSON 結構
        event_data = json.loads(response.text)
        
        # 組裝要存入 MongoDB 的完整記憶文件
        memory_document = {
            "owner_id": object_id,         # 這段記憶是屬於誰的
            "subject": subject_id,
            "object": object_id,
            "action": event_data.get("action", "發生了未知的互動"),
            "emotion": event_data.get("emotion", "neutral"),
            "importance_score": event_data.get("importance_score", 1),
            "timestamp": datetime.now(timezone.utc),
            "is_reflected": False          # 標記為未反思，留給夜間系統處理
        }
        
        # 寫入資料庫
        result = memories_collection.insert_one(memory_document)
        print(f"💾 [記憶已儲存] ID: {result.inserted_id}")
        print(f"   摘要: {memory_document['action']} (重要性: {memory_document['importance_score']}, 情緒: {memory_document['emotion']})")
        
        return memory_document

    except Exception as e:
        print(f"❌ 記憶提取失敗: {e}")
        return None

# === 簡單測試 ===
if __name__ == "__main__":
    test_dialogue_1 = """
    遊客 (tourist_999): 懶豹，你今天怎麼看起來這麼累？
    懶豹 (seal_01): 噗...因為水溫太舒服了，不想動...噗。
    """
    
    test_dialogue_2 = """
    壞豹 (seal_02): 欸懶豹，你是不是又變胖了？剛才企鵝都在笑你游不快。
    懶豹 (seal_01): 噗！？你胡說！我那是骨架大...噗！(生氣地轉頭)
    """

    print("\n--- 測試 1：日常對話 ---")
    extract_and_store_event("tourist_999", "seal_01", test_dialogue_1)
    
    print("\n--- 測試 2：帶有攻擊性的對話 ---")
    extract_and_store_event("seal_02", "seal_01", test_dialogue_2)