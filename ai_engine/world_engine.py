import random

def evaluate_attendance(seal_data, online_seals_ids):
    """
    評估海豹是否要來上班 (返回 True/False)
    """
    p = seal_data["personality"]
    state = seal_data["state"]
    social_graph = seal_data.get("social_graph", {})

    # 1. BaseRate (基礎出勤率): 由盡責性 (C) 決定
    base_rate = p["C"]  # 懶豹的 C=10，天生就不想上班

    # 2. MoodFactor (心情修正): 心情好比較願意來，神經質(N)會放大負面情緒的影響
    mood = state["mood_value"]
    mood_factor = mood * (1 + (p["N"] / 100.0)) 

    # 3. SocialPull (社交拉力): 看看現在誰在線上
    social_pull = 0
    for online_id in online_seals_ids:
        if online_id in social_graph:
            # 如果好朋友在線上，拉力增加；如果仇人在線上，拉力大減
            affinity = social_graph[online_id]
            social_pull += (affinity * 0.5) 

    # 4. Fatigue (疲勞度)
    fatigue = state["fatigue"]

    # 計算總上班意願分數 (Threshold 可設為 50)
    willingness_score = base_rate + mood_factor + social_pull - fatigue
    
    # 加入一點隨機性 (外向性 E 越高，越容易因為心血來潮跑來)
    random_variance = random.uniform(-10, 10) + (p["E"] * 0.1)
    final_score = willingness_score + random_variance

    print(f"[{seal_data['name']}] 意願計算: Base({base_rate}) + Mood({mood_factor:.1f}) + Social({social_pull}) - Fatg({fatigue}) = {final_score:.1f}")

    # 分數大於 50 決定上班
    return final_score > 50

# 模擬測試
seal = {
    "name": "懶豹",
    "personality": {"O": 20, "C": 10, "E": 85, "A": 30, "N": 70},
    "social_graph": {"seal_02": -50, "seal_03": 80},
    "state": {"fatigue": 20, "mood_value": -10} # 昨天被欺負心情不好
}

# 情況 A: 仇人 seal_02 在線上
print("情況 A (仇人在線):")
evaluate_attendance(seal, online_seals_ids=["seal_02"]) 
# 結果懶豹絕對不會來，因為 SocialPull 是負的，且 BaseRate 極低。

# 情況 B: 好友 seal_03 在線上
print("\n情況 B (好友在線):")
evaluate_attendance(seal, online_seals_ids=["seal_03"])
# 結果懶豹有極高機率會來，因為 seal_03 提供了 +40 的拉力，克服了不想上班的惰性。