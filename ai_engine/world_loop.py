import time
import json
import random
from datetime import datetime
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler
import paho.mqtt.client as mqtt

from reflection_engine import run_reflection_cycle
from llm_handler import generate_seal_initiation, generate_seal_response, generate_seal_monologue

# 初始化 MongoDB
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['aquarium_db']
seals_collection = db['seals']

# 初始化 MQTT Client (用來廣播狀態改變)
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.connect("127.0.0.1", 1883, 60)
mqtt_client.loop_start()

def evaluate_attendance(seal_data, online_seals_ids):
    p = seal_data.get("personality", {"O":50, "C":50, "E":50, "A":50, "N":50})
    state = seal_data.get("state", {})
    social_graph = seal_data.get("social_graph", {})

    base_rate = 35 + (p.get("C", 50) * 0.3)
    mood = state.get("mood_value", 0)
    mood_factor = mood * (1 + (p.get("N", 50) / 100.0))

    social_pull = 0
    for online_id in online_seals_ids:
        if online_id in social_graph:
            social_pull += (social_graph[online_id] * 0.5)

    fatigue = state.get("fatigue", 0)
    is_online = state.get("is_online", False) # 取得當前狀態

    # 計算基礎意願
    willingness_score = base_rate + mood_factor + social_pull - fatigue
    
    # 💡 修正二：加入狀態慣性 (Status Inertia)
    if is_online:
        # 已經在水族館了，給予留下的強大加分 (懶得回家)
        willingness_score += 25
    else:
        # 正在家裡休息，給予繼續躺著的強大扣分 (懶得開機出門)
        willingness_score -= 15

    random_variance = random.uniform(-10, 15) + (p.get("E", 50) * 0.15)
    final_score = willingness_score + random_variance

    return final_score > 50

def world_tick():
    """
    世界心跳 (World Tick)：
    1. 增減疲勞值
    2. 根據上下班意願改變狀態
    3. 透過 MQTT 廣播改變
    """
    print(f"\n🌍 [世界時間流動] {datetime.now().strftime('%H:%M:%S')} - 檢查所有海豹狀態...")
    
    # 取得目前所有在線上的海豹 ID
    online_seals = list(seals_collection.find({"state.is_online": True}))
    online_ids = [seal["seal_id"] for seal in online_seals]

    all_seals = list(seals_collection.find())
    
    for seal in all_seals:
        seal_id = seal["seal_id"]
        state = seal.get("state", {})
        is_online = state.get("is_online", False)
        fatigue = state.get("fatigue", 0)

        # 1. 調整疲勞值
        if is_online:
            fatigue = min(100, fatigue + random.randint(5, 15)) # 上班會累
        else:
            fatigue = max(0, fatigue - random.randint(10, 20))  # 休息會恢復體力

        state["fatigue"] = fatigue

        # 2. 評估是否上下班
        should_be_online = evaluate_attendance(seal, online_ids)

        # 如果狀態發生改變，或者疲勞值爆表強迫下班
        if fatigue >= 95 and is_online:
            print(f"⚠️ {seal['name']} 體力透支，強制下班！")
            should_be_online = False

        # 判斷狀態是否「發生改變」 (避免 online -> online 的重複廣播)
        status_changed = (is_online != should_be_online)
        state["is_online"] = should_be_online

        # 更新資料庫
        seals_collection.update_one(
            {"seal_id": seal_id},
            {"$set": {"state": state}}
        )

        # --- 處理狀態改變的廣播與下班碎碎念 ---
        if status_changed:
            if should_be_online:
                # 上班的趣味廣播
                status_text = random.choice(["伸了個懶腰，游進了展覽池", "打卡上班！", "噗通一聲跳進水裡", "帶著滿滿活力出現了"])
            else:
                # 下班的趣味廣播
                status_text = random.choice(["覺得累了，偷偷下班溜走", "游回後台睡覺了", "包袱款款下班去", "消失在水草堆中"])
                
                # 💡 觸發下班前的碎碎念
                print(f"💭 [{seal['name']}] 準備下班，正在心裡嘀咕...")
                monologue_msg = generate_seal_monologue(seal_id)
                print(f"💬 {seal['name']} 下班前碎碎念: {monologue_msg}")
                
                # 廣播自言自語
                mqtt_client.publish("aquarium/seal/chat", json.dumps({
                    "seal_id": seal_id,
                    "target_id": "self",
                    "content": monologue_msg
                }, ensure_ascii=False))

            print(f"📢 廣播動態: {seal['name']} {status_text} (疲勞值: {fatigue})")
            
            # 廣播給前端的 Payload
            payload = {
                "seal_id": seal_id,
                "status_text": status_text,      # 趣味文字
                "is_online": should_be_online,   # 保留布林值讓前端 Vue.js 容易判斷顯示/隱藏
                "fatigue": fatigue
            }
            mqtt_client.publish("aquarium/seal/status", json.dumps(payload, ensure_ascii=False))

    # 💡 修正一：在此處「重新」撈取真正的線上名單！
    # 確保剛剛被判定下班的海豹 (is_online 變成 False) 不會混在裡面
    current_online_seals = list(seals_collection.find({"state.is_online": True}))
    
    # 使用更新後的 current_online_seals 來進行社交判定
    if len(current_online_seals) > 0:
        for initiator in current_online_seals:
            initiator_id = initiator["seal_id"]
            e_score = initiator.get("personality", {}).get("E", 50)
            
            # 1. 決定今天是否要開口 (包含自言自語或找人)
            chat_probability = 0.05 + (e_score / 100.0) * 0.25 
            
            if random.random() < chat_probability:
                
                potential_targets = [s for s in current_online_seals if s["seal_id"] != initiator_id]
                
                # 2. 決定行為模式：找人 vs 自言自語
                # 如果沒有其他人在線上，強迫自言自語
                if not potential_targets:
                    wants_to_talk_to_other = False
                else:
                    # 外向度 E 越高，越傾向找人搭話 (最高 80% 機率找人，最少也有 20% 機率自言自語)
                    talk_to_other_prob = 0.2 + (e_score / 100.0) * 0.6
                    wants_to_talk_to_other = random.random() < talk_to_other_prob

                if wants_to_talk_to_other:
                    # --- 分支 A：找豹搭話 ---
                    weights = []
                    for target in potential_targets:
                        affinity = initiator.get("social_graph", {}).get(target["seal_id"], 0)
                        weight = max(5, affinity + 100) 
                        weights.append(weight)
                    
                    target = random.choices(potential_targets, weights=weights, k=1)[0]
                    target_id = target["seal_id"]
                    
                    print(f"🎯 [社交觸發] {initiator['name']} 決定去找 {target['name']} 搭話！")
                    initiation_msg = generate_seal_initiation(initiator_id, target_id)
                    print(f"💬 {initiator['name']} 對 {target['name']} 說: {initiation_msg}")
                    
                    mqtt_client.publish("aquarium/seal/chat", json.dumps({
                        "seal_id": initiator_id,
                        "target_id": target_id,
                        "content": initiation_msg
                    }, ensure_ascii=False))
                    
                    # 目標對象回應
                    reply_msg = generate_seal_response(target_id, initiator_id, initiation_msg)
                    print(f"💬 {target['name']} 回應 {initiator['name']}: {reply_msg}")
                    
                    mqtt_client.publish("aquarium/seal/chat", json.dumps({
                        "seal_id": target_id,
                        "target_id": initiator_id,
                        "content": reply_msg
                    }, ensure_ascii=False))
                
                else:
                    # --- 分支 B：自言自語 ---
                    print(f"💭 [社交觸發] {initiator['name']} 覺得無聊，開始自言自語。")
                    monologue_msg = generate_seal_monologue(initiator_id)
                    print(f"💬 {initiator['name']} 碎碎念: {monologue_msg}")
                    
                    # 廣播自言自語，target_id 設為 null 或 "self"，前端可以用不同的氣泡框(例如雲朵形狀)來渲染
                    mqtt_client.publish("aquarium/seal/chat", json.dumps({
                        "seal_id": initiator_id,
                        "target_id": "self", 
                        "content": monologue_msg
                    }, ensure_ascii=False))

def night_cycle():
    """夜間週期：觸發記憶反思與社交圖譜更新"""
    print(f"\n🌙 [夜間週期] 水族館閉館，海豹們開始在夢中反思今天的記憶...")
    run_reflection_cycle()
    
    # 反思完可以給所有海豹一點心情恢復
    seals_collection.update_many({}, {"$inc": {"state.mood_value": 5}})
    print("✨ 反思結束，大家的負面情緒稍微平復了一些。")

# === 排程器設定 ===
if __name__ == "__main__":
    scheduler = BackgroundScheduler()

    # 為了測試方便，我們把時間縮短：
    # 每 2.5 分鐘執行一次「世界心跳」
    scheduler.add_job(world_tick, 'interval', minutes=2.5)
    
    # 每 60 分鐘執行一次「夜間反思」
    # 若要設定特定時間，可用: trigger='cron', hour=0, minute=0
    scheduler.add_job(night_cycle, 'interval', minutes=60)

    print("⏳ 世界引擎已啟動！等待排程觸發... (按 Ctrl+C 結束)")
    scheduler.start()

    try:
        # 保持主程式運行
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 關閉世界引擎...")
        scheduler.shutdown()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()