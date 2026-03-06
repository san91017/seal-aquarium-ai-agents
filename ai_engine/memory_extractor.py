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
    # 使用 f-string 動態注入 Subject 和 Object，明確劃分角色
    system_instruction = f"""
    你是一個心理學與記憶提取專家。你的任務是將水族館中發生的對話，轉化為其中一方的「第一人稱結構化記憶」。
    
    【角色設定】
    - 發起行動者 (Subject): {subject_id}
    - 形成記憶者/承受者 (Object): {object_id}
    
    【輸出格式要求】
    請仔細閱讀對話紀錄，並以 JSON 格式輸出 {object_id} 腦海中的記憶。必須包含以下欄位：
    
    1. "action": (字串) 請以 {object_id} 的「第一人稱視角 (我)」來簡述這個事件。例如：「{subject_id} 嘲笑我太胖」、「{subject_id} 關心我累不累」。句子必須精簡。
    2. "emotion": (字串) 評估 {object_id} 承受此事件後產生的情緒。請嚴格僅從以下選出最符合的一個: "happy", "angry", "sad", "annoyed", "grateful", "neutral"。
    3. "importance_score": (整數 1-10) 此事件對 {object_id} 的重要程度：
        - 1-2分：無聊的日常閒聊、打招呼。
        - 3-5分：一般的資訊交換、小玩笑或輕微的抱怨。
        - 6-8分：明顯的情緒波動（被大聲讚美、被嚴重侮辱、得知大八卦）。
        - 9-10分：極度深刻的事件（改變人生觀、極度創傷）。

    【記憶提取範例】
    對話紀錄：
    卡爾 (carl_03): 喂，波波，你今天是不是又胖了一圈啊？
    波波 (bobo_01): 噗！？你才胖！你這隻討厭鬼離我遠一點...噗！
    
    如果你正在為 Object = bobo_01, Subject = carl_03 提取記憶，你的輸出應該是：
    {{
        "action": "carl_03 嘲笑我又胖了一圈",
        "emotion": "angry",
        "importance_score": 4
    }}
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
                thinking_config=types.ThinkingConfig(thinking_budget=0),
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