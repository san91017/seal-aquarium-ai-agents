from pymongo import MongoClient

# 連線至本地端 MongoDB
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['aquarium_db']
seals_collection = db['seals']
memories_collection = db['memories']

# 定義情緒權重字典
EMOTION_WEIGHTS = {
    "happy": 1.5,
    "excited": 2.0,
    "grateful": 2.0,
    "neutral": 0.1,
    "annoyed": -1.0,
    "sad": -1.5,
    "angry": -2.0,
    "fearful": -2.5
}

def clamp_score(score, min_val=-100, max_val=100):
    """將分數限制在指定範圍內"""
    return max(min_val, min(max_val, score))

def run_reflection_cycle():
    """
    執行反思週期：找出所有未反思的記憶，更新社交圖譜，並將記憶標記為已反思。
    """
    print("🌙 [反思系統啟動] 開始處理未消化的記憶...")
    
    # 1. 找出所有尚未反思的記憶
    unreflected_memories = list(memories_collection.find({"is_reflected": False}))
    
    if not unreflected_memories:
        print("🛏️ 今晚沒有需要反思的記憶，大家睡得很安穩。")
        return

    processed_count = 0

    # 2. 逐筆處理記憶
    for memory in unreflected_memories:
        owner_id = memory.get("owner_id")
        subject_id = memory.get("subject") # 對他做出行為的人
        emotion = memory.get("emotion", "neutral")
        importance = memory.get("importance_score", 1)
        action_desc = memory.get("action", "未知事件")

        # 排除自己對自己做的行為 (通常不需要因此增減自己的好感度)
        if owner_id == subject_id:
            memories_collection.update_one({"_id": memory["_id"]}, {"$set": {"is_reflected": True}})
            continue

        # 3. 計算好感度變動量
        weight = EMOTION_WEIGHTS.get(emotion.lower(), 0.1) # 預設給一點點正面權重
        delta = importance * weight

        # 4. 取得該海豹目前的社交圖譜
        seal = seals_collection.find_one({"seal_id": owner_id})
        if not seal:
            continue
        
        social_graph = seal.get("social_graph", {})
        current_score = social_graph.get(subject_id, 0) # 如果是陌生人，預設為 0
        
        # 計算新分數並 Clamp
        new_score = clamp_score(current_score + delta)

        # 5. 更新 MongoDB 中的海豹設定
        # 這裡動態構建 update query，例如 {"social_graph.seal_02": -16}
        update_query = {
            f"social_graph.{subject_id}": new_score
        }
        seals_collection.update_one(
            {"seal_id": owner_id},
            {"$set": update_query}
        )

        # 6. 將記憶標記為已反思
        memories_collection.update_one(
            {"_id": memory["_id"]},
            {"$set": {"is_reflected": True}}
        )

        # 印出日誌方便觀察
        direction = "📈 增加" if delta > 0 else "📉 減少"
        print(f"[{seal.get('name', owner_id)} 的反思] 想起了 {subject_id} '{action_desc}'")
        print(f"   -> 情緒: {emotion} (重要性 {importance})")
        print(f"   -> 對 {subject_id} 的好感度 {direction}: {current_score:.1f} -> {new_score:.1f}\n")
        
        processed_count += 1

    print(f"✅ [反思系統結束] 共處理了 {processed_count} 筆記憶。")

# === 簡單測試 ===
if __name__ == "__main__":
    # 假設資料庫中已經有我們上一階段用 extract_and_store_event 存進去的記憶
    # 直接執行這個腳本，看看好感度會不會產生變化
    run_reflection_cycle()
    
    # 驗證一下懶豹對 seal_02 的好感度是否被扣分了
    seal = seals_collection.find_one({"seal_id": "seal_01"})
    if seal and "social_graph" in seal:
        print("\n📊 懶豹目前的社交圖譜 (Social Graph):")
        print(seal["social_graph"])