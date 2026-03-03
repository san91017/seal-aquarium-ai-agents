# ai_engine/mqtt_handler.py
import paho.mqtt.client as mqtt
import json
import time
# 匯入我們剛剛寫好的 LLM 與資料庫處理模組
from llm_handler import generate_seal_response

BROKER_ADDRESS = "127.0.0.1"
BROKER_PORT = 1883

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("✅ Python AI 引擎已成功連線至 MQTT Broker")
        # 訂閱遊客的對話主題
        client.subscribe("aquarium/tourist/chat")
        print("🎧 Python 正在監聽 aquarium/tourist/chat 主題...")
    else:
        print(f"❌ 連線失敗，錯誤碼: {reason_code}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        seal_id = data.get('seal_id')
        tourist_id = data.get('tourist_id')
        user_message = data.get('message')
        
        print(f"\n📥 [收到遊客訊息] 主題: {msg.topic}")
        print(f"👤 遊客 [{tourist_id}] 對 海豹 [{seal_id}] 說: {user_message}")
        
        # --- 核心整合區塊 ---
        print(f"🧠 [AI 思考中] 正在讀取 MongoDB 並呼叫 Gemini...")
        
        # 呼叫 LLM 處理邏輯，這裡會自動處理記憶讀寫與 API 呼叫
        reply_content = generate_seal_response(seal_id, tourist_id, user_message)
        
        # 組裝要回傳給 Node.js 的資料
        reply_msg = {
            "seal_id": seal_id,
            "content": reply_content
        }
        
        print(f"🦭 [AI 回應] {reply_content}")
        print(f"📢 發布回應至 Node.js (aquarium/seal/chat)")
        client.publish("aquarium/seal/chat", json.dumps(reply_msg, ensure_ascii=False))
        # --------------------
        
    except json.JSONDecodeError:
        print("❌ 解析 JSON 失敗")
    except Exception as e:
        print(f"❌ 處理訊息時發生錯誤: {e}")

# 初始化 MQTT 客戶端
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

print("啟動 Python AI 引擎...")
client.connect(BROKER_ADDRESS, BROKER_PORT, 60)

# 啟動背景執行緒處理網路收發
client.loop_start()

try:
    # 這裡的 World Loop 先保持輕量，維持程式運行
    # 未來可以在這裡加入定時檢查海豹體力、觸發下班的腳本
    while True:
        time.sleep(10)
        
except KeyboardInterrupt:
    print("\n關閉 Python AI 引擎...")
    client.loop_stop()
    client.disconnect()