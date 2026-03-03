# ai_engine/db_init.py
from pymongo import MongoClient
from datetime import datetime, timezone

# 連線至本地端 MongoDB Community Server (預設 port 27017)
client = MongoClient('mongodb://localhost:27017/')

# 選擇或建立資料庫與 Collection
db = client['aquarium_db']
seals_collection = db['seals']


def create_seal_profile():
    # 定義波波的初始資料
    seal_data = {
        "seal_id": "seal_01",
        "name": "懶豹",
        "sprite_id": "seal_lazy_fat_gray",
        "soul_prompt": (
            "你是一隻叫*懶豹*的胖海豹。"
            "你講話很慢，如果有人問你問題，你通常會先抱怨一下再回答。"
            "你很喜歡吃魚，尤其是鮭魚，但你也會吃其他種類的魚。你不太喜歡運動，覺得游泳已經夠累了。"
            "你很懶，討厭上班，喜歡抱怨水溫太冷，覺得水族館的薪水太少。"
        ),
        "state": {
            "is_online": False,  # 預設先沒上班，等 World Loop 喚醒牠
            "mood": "sleepy",
            "energy": 100,
            "last_updated": datetime.now(timezone.utc)
        },
        "position": {
            "x": 0.0,
            "y": 0.0,
            "target_x": 0.0,
            "target_y": 0.0
        },
        "recent_memories": []
    }

    # 使用 update_one 搭配 upsert=True，確保重複執行腳本時只會更新，不會產生重複資料
    result = seals_collection.update_one(
        {"seal_id": seal_data["seal_id"]},
        {"$set": seal_data},
        upsert=True
    )

    if result.upserted_id:
        print(f"✅ 成功誕生新海豹：{seal_data['name']}")
    else:
        print(f"🔄 海豹資料已更新：{seal_data['name']}")


if __name__ == "__main__":
    create_seal_profile()

    # 驗證提取資料
    seal = seals_collection.find_one({"seal_id": "seal_01"})
    print("\n目前的資料庫紀錄：")
    print(f"ID: {seal['seal_id']}, 名字: {seal['name']}, 狀態: {seal['state']['is_online']}")