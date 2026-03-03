# 🦭 Seal Aquarium AI Agents

這是一個基於多智能體系統 (Multi-Agent System) 打造的 2D 網頁沙盒專案。在這個水族館中，每一隻 AI 海豹都擁有獨特的個性（靈魂文檔）、記憶與作息。牠們會自主決定是否要「上班」（出現在畫面上）、彼此之間會隨機聊天，並且能與造訪網頁的遊客進行即時互動。

## Features

* **自主 AI 靈魂 (Autonomous Agents):** 每隻海豹由 LLM 驅動，擁有獨自的 System Prompt（性格、背景）與短期/長期記憶。
* **動態作息系統 (Dynamic Schedule):** 海豹會根據疲勞度、心情或隨機事件，自主決定上線（出現）或下線（消失）。
* **Agent-to-Agent 社交:** 兩隻海豹在 2D 空間中靠近時，會觸發隨機對話，並在畫面上顯示聊天氣泡。
* **Human-to-Agent 互動:** 遊客可以點擊特定的海豹，展開 1 對 1 的專屬對話，海豹會以符合其個性的語氣回應。
* **無縫擴充:** 隨時可以生成新的「靈魂資料」寫入資料庫，水族館就會迎來新的海豹同事。

## Architecture

本專案採用微服務概念拆分模組，確保前端渲染、即時通訊與 AI 思考邏輯互不干擾：

1. **Frontend (Vue.js):** 負責網頁 UI 與 2D 畫面的渲染。透過 WebSocket 與後端保持連線，即時更新海豹座標與對話狀態。
2. **Backend (Node.js):** 作為遊戲與通訊伺服器。管理所有網頁遊客的 WebSocket 連線，並透過 MQTT 與 AI 引擎溝通。
3. **AI Engine (Python):** 世界的大腦。運行常駐迴圈 (World Loop)，負責呼叫 LLM API 產生對話、計算海豹行為邏輯，並透過 MQTT 發布狀態變更。
4. **Message Broker (MQTT):** 負責 Node.js 與 Python 之間低延遲、高頻率的訊息傳遞 (Pub/Sub)。
5. **Database (MongoDB):** 儲存海豹的設定檔 (Profile/Soul)、狀態 (Status)、位置 (Position) 以及對話記憶 (Memory)。

## Getting Started

*(待補充：環境建置與啟動指令)*

### 系統需求
* Node.js (v18+)
* Python (3.10+)
* MongoDB
* MQTT Broker (如 Eclipse Mosquitto)

## 發展路線圖 (Roadmap)

- [ ] **Phase 1: 基礎建設** - 建立 MongoDB Schema、完成 Node.js 與 Python 的 MQTT 通訊。
- [ ] **Phase 2: 靈魂注入** - 撰寫 Python AI 腳本，串接 LLM API，讓單一海豹能根據 Prompt 產出對話。
- [ ] **Phase 3: 視覺化** - 完成 Vue.js 前端 2D 渲染，實作 WebSocket 廣播海豹移動與對話。
- [ ] **Phase 4: 社交與作息** - 加入 Agent 間的互動偵測與自主上下班邏輯。
