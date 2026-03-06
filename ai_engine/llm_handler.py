# ai_engine/llm_handler.py
import os
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv
from google import genai
from google.genai import types
from memory_extractor import extract_and_store_event # 引入上一階段的記憶提取器

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['aquarium_db']
seals_collection = db['seals']

def _get_personality_prompt(personality: dict) -> str:
    """將 OCEAN 數值 (0-100) 轉換為 LLM 能理解的性格描述"""
    traits = []
    
    # E: 外向性
    e = personality.get("E", 50)
    if e > 70: traits.append("你非常外向聒噪，喜歡主動延續話題。")
    elif e < 30: traits.append("你很內向寡言，回答通常很簡短，甚至有點句點王。")
    
    # A: 親和性
    a = personality.get("A", 50)
    if a > 70: traits.append("你極度友善、有同理心，說話溫柔。")
    elif a < 30: traits.append("你講話很酸、喜歡嘲諷，不容易妥協。")
    
    # C: 盡責性
    c = personality.get("C", 50)
    if c > 70: traits.append("你個性嚴謹，對話很有條理，討厭混亂。")
    elif c < 30: traits.append("你生性慵懶散漫，對話常常沒有重點或想轉移話題。")
    
    # N: 神經質
    n = personality.get("N", 50)
    if n > 70: traits.append("你很神經質，容易焦慮、大驚小怪或過度反應。")
    elif n < 30: traits.append("你情緒非常穩定，天塌下來也無所謂的語氣。")

    # O: 開放性
    o = personality.get("O", 50)
    if o > 70: traits.append("你充滿好奇心，對新奇的事物或八卦非常感興趣。")
    elif o < 30: traits.append("你思想保守，對新事物不感興趣，喜歡重複安穩的日常。")

    return " ".join(traits)

def _get_relationship_prompt(social_graph: dict, interlocutor_id: str) -> str:
    """根據好感度分數 (-100 ~ 100) 決定對話態度"""
    score = social_graph.get(interlocutor_id, 0) # 找不到預設為 0 (陌生人)
    
    if score > 60:
        return f"你非常喜歡這個對象 (好感度 {score}/100)，他是你的摯友！語氣要極度熱情、親暱，甚至可以分享秘密。"
    elif score > 20:
        return f"你對這個人印象不錯 (好感度 {score}/100)，是個熟人，語氣友善自然。"
    elif score < -60:
        return f"你極度痛恨這個對象 (好感度 {score}/100)，他是你的死對頭！語氣要充滿敵意、不耐煩，甚至可以直接開罵或拒絕回答。"
    elif score < -20:
        return f"你有點討厭這個人 (好感度 {score}/100)，語氣冷淡、敷衍，想快點結束對話。"
    else:
        return f"你對這個人沒有特別的感覺 (好感度 {score}/100)，就像一般的點頭之交。"

def generate_seal_initiation(initiator_id: str, target_id: str) -> str:
    """讓一隻海豹主動向另一隻海豹搭話"""
    
    initiator_data = seals_collection.find_one({"seal_id": initiator_id})
    target_data = seals_collection.find_one({"seal_id": target_id})
    
    if not initiator_data or not target_data:
        return ""

    soul_prompt = initiator_data.get("soul_prompt", "")
    personality = initiator_data.get("personality", {})
    social_graph = initiator_data.get("social_graph", {})
    
    personality_desc = _get_personality_prompt(personality)
    relationship_desc = _get_relationship_prompt(social_graph, target_id)
    target_name = target_data.get("name", "那隻海豹")

    # 針對「主動搭話」設計的 System Instruction
    initiation_instruction = f"""
    【核心設定】{soul_prompt}
    【深層性格】{personality_desc}
    【當前對象】你現在看到了「{target_name}」。{relationship_desc}
    
    【最高指令】
    請根據你對他的好感度與你自己的性格，主動向他說一句話（搭話）。
    只需要一句簡短的話即可（不要自言自語，要明確是對他說的）。
    如果好感度低，你可以挑釁或抱怨；如果好感度高，你可以熱情問候或分享八卦。
    【長度限制】只需要一句極為簡短的話，絕對不要超過 20 個中文字。
    """

    print(f"🗣️ [{initiator_data['name']}] 正在思考如何向 [{target_name}] 搭話...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents="請主動開口說一句話：",
        config=types.GenerateContentConfig(
            system_instruction=initiation_instruction,
            temperature=0.7,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
    )
    
    initiation_msg = response.text
    
    # 將主動搭話的記憶存入自己的腦海中
    now = datetime.now(timezone.utc)
    seals_collection.update_one(
        {"seal_id": initiator_id},
        {"$push": {
            "recent_memories": {
                "$each": [{"role": "assistant", "interlocutor": target_id, "content": initiation_msg, "timestamp": now}],
                "$slice": -10
            }
        }}
    )
    
    return initiation_msg

def generate_seal_monologue(seal_id: str) -> str:
    """讓海豹根據當下狀態自言自語 (碎碎念)"""
    
    seal_data = seals_collection.find_one({"seal_id": seal_id})
    if not seal_data:
        return ""

    soul_prompt = seal_data.get("soul_prompt", "")
    personality = seal_data.get("personality", {})
    state = seal_data.get("state", {})
    
    personality_desc = _get_personality_prompt(personality)
    mood = state.get("mood_value", 0)
    fatigue = state.get("fatigue", 0)

    # 針對「自言自語」設計的 System Instruction
    monologue_instruction = f"""
    【核心設定】{soul_prompt}
    【深層性格】{personality_desc}
    【當前狀態】你的疲勞值是 {fatigue}/100，心情值是 {mood}/100。
    
    【最高指令】
    請根據你現在的性格、心情和疲勞度，自言自語說一句簡短的話（碎碎念）。
    你現在沒有在跟任何人對話，只是發出感嘆、抱怨、或者表達當下的感受。
    【長度限制】請控制在 10 到 15 個中文字內，越短越好。
    """

    print(f"💭 [{seal_data['name']}] 正在心裡嘀咕...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents="請自言自語一句話：",
        config=types.GenerateContentConfig(
            system_instruction=monologue_instruction,
            temperature=0.6,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
    )
    
    monologue_msg = response.text
    
    # 將自言自語存入自己的短期記憶，讓他記得自己剛剛在想什麼，避免重複講一樣的話
    now = datetime.now(timezone.utc)
    seals_collection.update_one(
        {"seal_id": seal_id},
        {"$push": {
            "recent_memories": {
                "$each": [{"role": "assistant", "interlocutor": "self", "content": f"(自言自語) {monologue_msg}", "timestamp": now}],
                "$slice": -10
            }
        }}
    )
    
    return monologue_msg

def generate_seal_response(seal_id: str, interlocutor_id: str, user_message: str) -> str:
    """讀取海豹記憶與性格、呼叫 Gemini 產生回應，並更新記憶至資料庫。"""
    
    seal_data = seals_collection.find_one({"seal_id": seal_id})
    if not seal_data:
        return "（海豹不在水族館裡...）"

    # --- 1. 提取並組裝所有動態狀態 ---
    soul_prompt = seal_data.get("soul_prompt", "你是一隻普通的海豹。")
    state = seal_data.get("state", {})
    mood = state.get("mood_value", 0)
    energy = state.get("fatigue", 0) # 疲勞度
    
    # 呼叫輔助函式解析性格與人際關係
    personality = seal_data.get("personality", {})
    social_graph = seal_data.get("social_graph", {})
    
    personality_desc = _get_personality_prompt(personality)
    relationship_desc = _get_relationship_prompt(social_graph, interlocutor_id)

    # 動態組合超級 System Instruction
    dynamic_system_instruction = f"""
    【核心設定】
    {soul_prompt}
    
    【深層性格 (OCEAN)】
    {personality_desc}
    
    【當前生理與心理狀態】
    你現在的疲勞值是：{energy}/100 (越高越累)。
    你現在的心情值是：{mood}/100 (負數代表心情差，正數代表心情好)。
    
    【人際關係偵測】
    對話對象 ID：{interlocutor_id}
    你的態度：{relationship_desc}
    
    【最高指令】
    請綜合以上所有資訊，以第一人稱扮演這隻海豹來回應。
    【長度限制】你的回覆必須非常簡短，請控制在 30 個中文字以內。
    """

    # --- 2. 處理歷史紀錄 ---
    recent_memories = seal_data.get("recent_memories", [])
    contents = []
    for memory in recent_memories:
        role = "model" if memory["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=memory["content"])]))
        
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

    # --- 3. 呼叫 Gemini ---
    print(f"\n🧠 [Gemini 載入靈魂] 正在套用 {seal_data['name']} 的性格與關係網...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=dynamic_system_instruction,
            temperature=0.7, # 稍微調高溫度，讓情緒表現更豐富
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
    )
    assistant_reply = response.text

    # --- 4. 非同步更新記憶與觸發事件提取 ---
    now = datetime.now(timezone.utc)
    new_memory_entries = [
        {"role": "user", "interlocutor": interlocutor_id, "content": user_message, "timestamp": now},
        {"role": "assistant", "interlocutor": interlocutor_id, "content": assistant_reply, "timestamp": now}
    ]

    seals_collection.update_one(
        {"seal_id": seal_id},
        {"$push": {"recent_memories": {"$each": new_memory_entries, "$slice": -10}}}
    )
    
    # 將這段對話傳給事件提取器，讓它去判斷這件事重不重要
    full_dialogue = f"對方 ({interlocutor_id}): {user_message}\n海豹 ({seal_id}): {assistant_reply}"
    extract_and_store_event(subject_id=interlocutor_id, object_id=seal_id, context_text=full_dialogue)

    return assistant_reply

# === 簡單測試 ===
if __name__ == "__main__":
    test_seal_id = "seal_01"
    
    # 測試 A: 面對討厭的 seal_02 (假設我們在資料庫裡把 seal_01 對 seal_02 的好感度設為 -50)
    seals_collection.update_one({"seal_id": test_seal_id}, {"$set": {"social_graph.seal_02": -50}})
    print("\n[情境 A] 仇人 seal_02 來搭話")
    reply_a = generate_seal_response(test_seal_id, "seal_02", "懶豹，你今天怎麼又在偷懶？")
    print(f"🦭 懶豹: {reply_a}")
    
    # 測試 B: 面對喜歡的 seal_03 (假設好感度 80)
    seals_collection.update_one({"seal_id": test_seal_id}, {"$set": {"social_graph.seal_03": 80}})
    print("\n[情境 B] 摯友 seal_03 來搭話")
    reply_b = generate_seal_response(test_seal_id, "seal_03", "懶豹！我帶了小魚乾來找你玩！")
    print(f"🦭 懶豹: {reply_b}")