# Discord Hotmap Bot

一個以 Python + Docker 建置的 Discord 管理型機器人，提供：

- 使用者頻道活躍度分析（`/hotmap`）
- 訊息類型圓餅分析（`/msgtype`）
- 訊息快照品質診斷（`/msgtype_debug`、`/msginspect`）
- 刪除訊息稽核紀錄（`/set_delete_log`、`/delete_log_status`，含回覆追蹤）

---

## 系統架構

- **Bot Runtime**：`discord.py` 非同步事件驅動
- **Data Store**：PostgreSQL（儲存訊息快照、統計來源資料、設定）
- **Deployment**：Docker Compose（`bot` + `db`）
- **Startup Tasks**：
  - 討論串自動加入與掃描
  - 可選歷史回補（backfill）
  - 可選空快照清理（cleanup）

---

## 目錄結構

- `src/main.py`：Bot 主程式、Slash Commands、分析圖表、事件處理
- `src/db.py`：資料表初始化與查詢/寫入邏輯
- `src/config.py`：環境變數與設定載入
- `docker-compose.yml`：容器編排
- `Dockerfile`：Bot 映像建置
- `.env.example`：設定範本

---

## 主要指令

- `/tabetai`
  - 午晚餐抽籤（動畫 + ✅確認 / ❌重抽）
  - 全體成員可用
  - 會記錄個人最近餐點，避免短期重複
  - 每個伺服器初次使用時會載入完整預設餐點清單，之後可由管理員增減

- `/tabetai_clear`
  - 互動式清除個人抽選紀錄（自行選擇要刪除的那一筆）
  - 全體成員可用

- `/tabetai_add meal_name`
  - 新增餐點到伺服器抽選清單
  - 需管理員權限

- `/tabetai_remove meal_name`
  - 移除伺服器抽選清單餐點（可直接輸入名稱，或不帶參數用互動選單移除）
  - 需管理員權限

- `/hotmap @user [days]`
  - 頻道活躍度分析
  - 預設天數由 `HOTMAP_DEFAULT_DAYS` 控制，最大由 `HOTMAP_MAX_DAYS` 控制

- `/msgtype @user [days]`
  - 訊息類型分析（附件 / 貼圖 / 連結 / 表符 / 文字訊息 / 其他）

- `/msgtype_debug @user [days]`
  - 針對 `其他` 類別做細分診斷
  - 會做樣本存取檢查（可存取、已刪除、權限不足等）

- `/msginspect message_id`
  - 逐筆檢查特定訊息
  - 對照 Discord 即時內容與 DB 快照內容

- `/set_delete_log #channel`
  - 設定刪除訊息紀錄頻道

- `/delete_log_status`
  - 檢查刪除紀錄頻道設定與 bot 權限狀態

> 權限規則：
> - `/tabetai`、`/tabetai_clear`：全體可用
> - 其餘管理型指令：需管理員權限

---

## 刪除訊息紀錄內容

- 基本資訊：
  - 發言者（embed 作者列）
  - 頻道（可點擊 `#channel` 直接跳轉）
  - 訊息內容
  - 時間（刪除時間 / 原訊息時間，短格式不顯示星期）
  - `message_id`（footer）

- 回覆追蹤（訊息是回覆時顯示）：
  - 回覆對象（被回覆使用者）
  - 回覆 mention 狀態（開啟 / 關閉 / 未知）
  - 回覆訊息摘要（引用顯示）
  - 原始訊息連結（可直接跳到被回覆訊息）

- 媒體與表情：
  - 附件清單與預覽圖（可用時）
  - 貼圖資訊與可開啟連結
  - 自訂表情符號清單

---

## 環境變數

### 必要

- `DISCORD_TOKEN`
- `DATABASE_URL`

### 分析與回補

- `HOTMAP_DEFAULT_DAYS`（預設查詢天數）
- `HOTMAP_MAX_DAYS`（最大查詢天數）
- `HOTMAP_INGEST_LOG_INTERVAL_SEC`（吞吐監控 log 週期）
- `HOTMAP_HISTORY_BACKFILL_ON_STARTUP`（啟動時是否回補）
- `HOTMAP_HISTORY_BACKFILL_DAYS`（回補天數）

### 啟動清理（可選）

- `HOTMAP_CLEANUP_ON_STARTUP`（是否在啟動時清理空快照）
- `HOTMAP_CLEANUP_DAYS`（清理時間範圍，最近 N 天）

---

## 使用方式

1. 建立環境檔：
   - 將 `.env.example` 複製為 `.env`
2. 填入必要設定（至少 `DISCORD_TOKEN`、`DATABASE_URL`）
3. 建置並啟動：
   - `docker compose up --build -d`
4. 觀察啟動與同步狀態：
   - `docker compose logs -f bot`

---

## 權限與設定重點

- Discord Developer Portal 需開啟：
  - `MESSAGE CONTENT INTENT`
  - （視需求）`SERVER MEMBERS INTENT`
- 刪除紀錄頻道至少需：
  - `View Channel`
  - `Send Messages`
  - `Embed Links`
- 若需覆蓋 private thread 資料，bot 必須可加入並具備讀取歷史訊息權限。

---

## 維運建議

- 生產環境建議固定保留最近一段時間資料（例如 30~90 天）
- 大型社群請定期檢查：
  - PostgreSQL 容量與索引膨脹
  - 回補與清理任務耗時
  - Bot 權限是否被頻道覆寫
