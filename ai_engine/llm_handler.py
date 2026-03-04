# ai_engine/llm_handler.py
import os
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv
from google import genai
from google.genai import types
from memory_extractor import extract_and_store_event

# 載入環境變數中的 API Key
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 初始化 Gemini 客戶端
client = genai.Client(api_key=GEMINI_API_KEY)

# 連線至本地端 MongoDB
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['aquarium_db']
seals_collection = db['seals']

def generate_seal_response(seal_id: str, tourist_id: str, user_message: str) -> str:
    """
    讀取海豹記憶、呼叫 Gemini 產生回應，並更新記憶至資料庫。
    """
    # 1. 從 MongoDB 取得海豹資料
    seal_data = seals_collection.find_one({"seal_id": seal_id})
    if not seal_data:
        return "（海豹不在水族館裡...）"

    # 提取靈魂設定與當前狀態
    soul_prompt = seal_data.get("soul_prompt", "你是一隻普通的海豹。")
    state = seal_data.get("state", {})
    mood = state.get("mood", "neutral")
    energy = state.get("energy", 100)

    # 動態組合 System Instruction：把當前狀態也告訴 AI
    dynamic_system_instruction = (
        f"{soul_prompt}\n"
        f"[系統提示] 你現在的心情是：{mood}，體力值是：{energy}/100。\n"
        f"請以第一人稱扮演這隻海豹來回應遊客。"
    )

    # 2. 重建歷史對話紀錄 (History)
    # Gemini 接受的歷史紀錄格式為 types.Content(role='user'|'model', parts=[types.Part.from_text(...)])
    recent_memories = seal_data.get("recent_memories", [])
    contents = []
    
    for memory in recent_memories:
        # 將資料庫的 'assistant' 轉換為 Gemini 的 'model'
        role = "model" if memory["role"] == "assistant" else "user"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=memory["content"])]
            )
        )
        
    # 將遊客最新的一句話加入 contents 陣列的最後
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)]
        )
    )

    # 3. 呼叫 Gemini API (使用反應最快的 flash 模型)
    print(f"🧠 [Gemini] 正在思考 {seal_data['name']} 的回應...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=dynamic_system_instruction,
            temperature=0.7, # 稍微提高一點溫度，讓對話更有變化性
        )
    )
    
    assistant_reply = response.text
    
    # --- 新增這段：非同步或背景觸發記憶提取 ---
    full_dialogue = f"遊客 ({tourist_id}): {user_message}\n海豹 ({seal_id}): {assistant_reply}"
    # 將對話交給記憶提取器壓縮儲存
    extract_and_store_event(subject_id=tourist_id, object_id=seal_id, context_text=full_dialogue)
    # ----------------------------------------
    
    return assistant_reply

# === 簡單測試 ===
if __name__ == "__main__":
    test_seal_id = "seal_01"
    test_tourist = "tourist_abc"
    
    # 模擬遊客連續說兩句話，測試記憶是否正常運作
    print("\n👤 遊客: 嗨懶豹，你今天好嗎？")
    reply1 = generate_seal_response(test_seal_id, test_tourist, "嗨懶豹，你今天好嗎？")
    print(f"🦭 懶豹: {reply1}")
    
    print("\n👤 遊客: 我剛才說了什麼？")
    reply2 = generate_seal_response(test_seal_id, test_tourist, "我剛才說了什麼？")
    print(f"🦭 懶豹: {reply2}")