# ai_engine/mqtt_handler.py
import paho.mqtt.client as mqtt
import json
import time

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
        print(f"\n📥 [收到遊客訊息] 主題: {msg.topic}")
        print(f"👤 遊客 [{data['tourist_id']}] 對 海豹 [{data['seal_id']}] 說: {data['message']}")
        
        # 這裡未來會觸發 LLM 思考，並產出回應
        # 模擬 LLM 思考延遲後回應
        time.sleep(2)
        reply_msg = {
            "seal_id": data['seal_id'],
            "content": "噗...因為水溫太舒服了，不想動...噗。"
        }
        print(f"\n🧠 [AI 思考完畢] 發布回應至 Node.js")
        client.publish("aquarium/seal/chat", json.dumps(reply_msg, ensure_ascii=False))
        
    except json.JSONDecodeError:
        print("❌ 解析 JSON 失敗")

# 初始化 MQTT 客戶端 (使用 MQTTv5 協議以支援較新特性)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

print("啟動 Python AI 引擎...")
client.connect(BROKER_ADDRESS, BROKER_PORT, 60)

# 啟動背景執行緒處理網路收發
client.loop_start()

try:
    # 模擬 World Loop (世界時間流動)
    while True:
        # 模擬：系統讓海豹「波波」打卡上班
        status_msg = {
            "seal_id": "bobo_01",
            "status": "online",
            "mood": "sleepy"
        }
        print("\n📢 [World Loop] 發布海豹狀態更新")
        client.publish("aquarium/seal/status", json.dumps(status_msg, ensure_ascii=False))
        
        # 每 10 秒觸發一次世界事件
        time.sleep(10)
        
except KeyboardInterrupt:
    print("\n關閉 Python AI 引擎...")
    client.loop_stop()
    client.disconnect()