// backend/src/mqtt_client.js
const mqtt = require('mqtt');

// 連線至本機 MQTT Broker
const client = mqtt.connect('mqtt://127.0.0.1:1883');

client.on('connect', () => {
    console.log('✅ Node.js 已成功連線至 MQTT Broker');
    
    // 訂閱所有海豹相關的行為更新
    client.subscribe('aquarium/seal/#', (err) => {
        if (!err) {
            console.log('🎧 Node.js 正在監聽 aquarium/seal/# 主題...');
        }
    });

    // 模擬：遊客對名叫「懶豹」的海豹說話
    setTimeout(() => {
        const touristMsg = {
            seal_id: 'seal_01',
            tourist_id: 'user_999',
            message: '懶豹，你今天怎麼看起來這麼累？'
        };
        console.log(`\n👤 [遊客發言] 傳送至 Python 引擎:`, touristMsg);
        client.publish('aquarium/tourist/chat', JSON.stringify(touristMsg));
    }, 3000);
});

// 處理來自 Python 的海豹訊息
client.on('message', (topic, message) => {
    const data = JSON.parse(message.toString());
    
    console.log(`\n📥 [收到 Python 訊息] 主題: ${topic}`);
    
    // 這裡未來會將資料透過 WebSocket 廣播給 Vue 前端
    switch (topic) {
        case 'aquarium/seal/chat':
            console.log(`💬 海豹 [${data.seal_id}] 說: ${data.content}`);
            break;
        case 'aquarium/seal/status':
            console.log(`🔄 海豹 [${data.seal_id}] 狀態更新: ${data.status}`);
            break;
        default:
            console.log(`📦 資料:`, data);
    }
});