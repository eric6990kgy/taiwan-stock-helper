# Personal Investment OS（個人投資作業系統）

*[English version](README.md)*

單人使用的「投資組合管理 + 股票研究 + 投資分析」系統，用來追蹤台股個股持倉與一個
全球 ETF / 機器人理財配置。完整產品範疇請參考架構審查文件（對話紀錄 / PRD）。
這份 README 只記錄「實際做出來的東西」。

外部六個台股/量化相關 GitHub 專案的研究性比較（用來決定 Phase 6 的優先順序——
三大法人、融資融券、月營收、技術指標）請見
[`docs/Personal_Investment_OS_Integration_Report.pdf`](docs/Personal_Investment_OS_Integration_Report.pdf)。

每個 Phase 的逐日開發歷程——做了什麼、為什麼這樣決定、review 抓到的 bug，以及
沒有變成正式功能的非正式研究（回測、策略調整）——請見
[`DEVLOG.md`](DEVLOG.zh-TW.md)（中文版）。

## 現況：Phase 12 已完成 —— Gemini 多代理人研究團隊

整套系統已可從瀏覽器端到端使用。除了 Phase 7 的綜合評分、逐項訊號讀取、LINE
通知之外，系統會對一份真實的 20 檔觀察名單跑「每日只顯示變動」的掃描，把每次
狀態變化分類成條件式語氣的推薦（**絕不是**「買/賣」），並且在顯示任何一則「考慮
加碼」的推薦*之前*，一定先過 Phase A 的風險/回撤閘門檢查——不是事後才補檢查
（Phase 8）。到了 Phase 12，每一則推薦還會額外附上三個 Gemini agent（基本面
研究員、技術面研究員、投資組合經理人）各自的結構化研究意見——附掛在同一個決定性
判斷旁邊，絕不取代它——並有一個 KPI 頁面追蹤每個 agent 自己講的話事後到底準不準。
細節見下方「已實作（Phase 12）」。

## 市場資料

- **資料來源**：[FinMind](https://finmind.github.io/)（`backend/app/providers/finmind_provider.py`），
  在完整比較過 TWSE/TPEx 官方 OpenAPI、Fugle、Yahoo Finance/yfinance、TEJ、CMoney
  之後選定（完整比較與理由見專案歷史中的 Phase 5 Discovery Report）。若 FinMind
  未來無法使用，官方 TWSE/TPEx OpenAPI 是已記錄的備援方案。
- **資料使用限制**：FinMind 自己的專案條款限制*資料本身*（不是client程式碼，
  程式碼是 Apache-2.0）只能用於教育/非商業用途。**這個系統是個人、單人使用、
  非商業性質——不要新增任何會轉散布或將這個整合取得的資料變現的功能**，除非先
  重新檢視 FinMind 的條款。
- **如何更新資料**：Settings →「Update Market Data」（手動點擊），或透過
  **Windows 工作排程器**每天自動跑一次（`PersonalInvestmentOS-DailyUpdate`，
  19:00——選這個時間是因為 FinMind 的三大法人/融資融券資料集通常這時候已經結算
  完畢）。目前系統內部仍然沒有內建的排程器/cron——是作業系統觸發
  `backend/scripts/daily_update.py`，這個腳本會建立跟按鈕完全一樣的
  `MarketDataIngestionService` 並呼叫 `.update_all()`（不篩選任何股票代號）。
  每次執行都會在 `backend/logs/daily_update.log` 新增一行記錄
  （status/succeeded/failed/warnings），確保無人值守時失敗不會真的悄無聲息。
  管理這個排程任務可用 `schtasks /query /tn PersonalInvestmentOS-DailyUpdate` 和
  `schtasks /delete /tn PersonalInvestmentOS-DailyUpdate`。無論哪種觸發方式，都會
  抓取每一個 STOCK/ETF 資產的股價、基本面、股利、估值比率（P/E、P/B、股息率）、
  三大法人、融資融券、月營收，然後跑 Phase 8 的每日推薦掃描；種子（demo）資產
  第一次收到真實資料時會自動把 `is_demo_data` 改成 `false`，舊的 `MOCK` 來源資料
  列會保留原地（用 `source` 欄位區分，不會被刪除）。
- **已知資料來源限制**：`TaiwanStockMarketValue`（市值/流通股數）需要 FinMind
  付費方案——這裡用的免費方案會讓這些欄位回傳 `null`，而不是讓整次更新失敗。
- **選用**：在 `backend/.env` 設定 `FINMIND_API_TOKEN`（免費在 finmindtrade.com
  註冊）可以把速率限制從每小時 300 次提高到 600 次。不設定也能用，只是限制較低。

## 後端安裝

```bash
cd backend
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS/Linux

cp .env.example .env   # 預設用本機 sqlite 檔案，不用改

./.venv/Scripts/python -m alembic upgrade head     # 建立 investment_os.db
./.venv/Scripts/python -m app.database.seed        # 載入示範資料
./.venv/Scripts/python -m pytest tests/ -v         # 執行測試

./.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# 開啟 http://127.0.0.1:8000/docs 使用互動式 Swagger UI
```

## 前端安裝

```bash
cd frontend
npm install

cp .env.example .env   # 若後端不是用預設埠號，在這裡設定 VITE_API_URL

npm run dev             # http://127.0.0.1:5173，需要後端已啟動
npm run test             # vitest —— 元件測試 + API 整合測試
npm run build            # 正式環境建置（tsc -b && vite build）
```

## 已實作（Phase 1）

- **資料表結構**（`backend/app/models/`）：`users`、`accounts`、`assets`、
  `transactions`、`watchlist`、`investment_thesis`、`price_history`、
  `fundamentals`，以及一個保留但暫未使用的 `fx_rates` 表，供未來多幣別支援用。
- **Migration**（`backend/alembic/`）：從第一天就用 Alembic 管理schema——從不
  直接對正式 DB 做 `create_all()`。
- **種子資料**（`backend/app/database/seed.py`）：PRD 第 37 節的示範資料集——
  7 檔台股、全球 ETF 基金、一個現金帳戶、模擬股價歷史 + 基本面資料、涵蓋每一種
  交易類型的範例交易、一筆觀察名單、一份投資論點。每個資產都標記
  `is_demo_data=True`；每筆股價/基本面資料都帶有 `source`（`MOCK` 或 `MANUAL`）——
  這是測試用假資料，不是真實市場資料。
- **測試**（`backend/tests/`）：29 個測試，涵蓋每個 CHECK 限制、每個 UNIQUE
  限制、外鍵約束、種子資料完整性，針對一個直接從 models 建出來的記憶體內 SQLite
  資料庫執行。

## 已實作（Phase 2）

- **交易重播**（`app/analytics/cost_basis.py`）：`replay_transactions()` 和
  `calculate_positions()` 純粹從一串 `TransactionInput` 推導出加權平均成本、
  已實現損益、剩餘股數/成本——內部會依時間排序，所以無論輸入順序如何，補登
  過去日期的交易都能正確重新計算。
- **估值**（`app/analytics/valuation.py`）：市值、未實現損益、報酬率，同時實作
  `TRANSACTION_BASED` 和 `MANUAL_MARKET_VALUE` 兩種慣例。
- **投資組合彙總**（`app/analytics/portfolio.py`）：每個持倉的投組權重，以及
  `PortfolioSummary` 彙整（投入資金、市值、未實現/已實現損益、股利、手續費、
  交易稅、總報酬）。
- **總共 67 個測試**（Phase 2 新增 38 個）——完整的公式與邊界情況拆解見對話
  歷史中的 Phase 2 報告。
- `app/analytics/` 裡完全沒有 import FastAPI、SQLAlchemy 或任何跟 DB/HTTP
  有關的東西——用 grep 驗證過，不只是靠慣例。

## 已實作（Phase 3）

- **分層後端**（`app/api/routes` → `app/services` → `app/repositories` /
  `app/analytics` / `app/providers` → `app/models`）：routes 只是很薄的控制層，
  所有業務規則都放在 services，所有財務計算仍然來自 Phase 2 那個沒被動過的
  `app/analytics` 套件。
- **MarketDataProvider 抽象層**（`app/providers/`）：`MockMarketDataProvider`
  從本機 DB 提供股價/基本面/公司資訊——之後換成真的資料供應商只要改
  `app/api/deps.py` 裡的一個 factory function，不需要動 route 或 service
  程式碼。
- **39 個 REST endpoint**，涵蓋帳戶、資產、交易、投資組合、持倉、研究、基本面、
  股價、觀察名單、投資論點、分析（資產配置/績效/風險）、選股器、CSV 匯入匯出。
- **只允許台幣、不足股數保護**都放在 `TransactionService`，不是 DB 限制或
  route 邏輯——每一次新增/修改/刪除都會先用
  `app.analytics.cost_basis.replay_transactions()` 重播一次結果再真正提交。
- **Decimal 安全序列化**：每一個金額/數量欄位都透過共用的 `DecimalStr` 型別
  序列化成 JSON 字串，絕不用 JS 浮點數。
- **總共 133 個測試**（Phase 3 新增 66 個 API 整合測試，加上 Phase 1-2 的 67
  個，全部維持不動且通過）。

## 已實作（Phase 4）

- **6 個頁面**（`frontend/src/pages/`）：Dashboard、Portfolio、Transactions、
  Research、Watchlist、Settings——用 `react-router-dom` 路由，全部透過
  `@tanstack/react-query` 串接正式運作的 FastAPI。
- **Decimal 安全顯示**（`frontend/src/utils/decimal.ts`）：每一個金額/百分比/
  股數都透過 `decimal.js` 格式化，絕不用 `Number()`/`parseFloat`——API 的
  `DecimalStr` 承諾一路延續到畫面上。
- **React 裡零財務計算**——畫面上每個數字都是 API 的原始欄位或是純粹的格式化
  （顯示用的四捨五入、千分位）。成本基礎、損益、權重全部來自後端。
- **共用元件**（`frontend/src/components/`）：`QueryState`（每個頁面統一的
  loading/error/empty 呈現方式）、`AllocationChart`/`PriceChart`（Recharts）、
  `SummaryCard`、`Money`/`Percent`/`Shares`、demo 資料標籤與狀態標籤、`Modal`。
- **35 個前端測試**（Vitest + Testing Library + MSW）：格式化工具函式、
  `QueryState` 的四種呈現狀態、以及針對模擬 API 的頁面層級整合測試（包含在
  新增交易表單裡「股數不足」錯誤路徑的呈現）。
- 正式環境建置通過（`tsc -b && vite build`）；133 個後端測試全部維持綠燈、
  沒被改動。

## 已實作（Phase 5B）

- **`FinMindProvider`**（`app/providers/finmind_provider.py`）：對 FinMind
  真實 API 實作完整的 `MarketDataProvider` 介面（欄位對應是對照真實回應驗證
  過的，不是憑文件猜測）——是整個程式庫裡唯一知道 FinMind 回應格式的檔案。
- **介面擴充**新增 `get_dividends()` 和 `get_valuation()`；
  `MockMarketDataProvider`（仍然是系統裡每個一般讀取用的介面）從本機 DB
  實作這兩個方法，讓 provider 的邊界保持乾淨——FinMind 特有的資料結構不會
  滲透到 services 或 repositories。
- **資料表結構**：新增 `dividends` 表（市場整體的除息日曆，跟使用者自己的
  DIVIDEND 交易不同）；`price_history` 新增 `adjusted_close`、`trading_value`、
  `pe_ratio`、`pb_ratio`、`dividend_yield`；`assets` 新增 `shares_outstanding`
  和 `listing_status`。
- **`MarketDataIngestionService`**（`app/services/market_data_service.py`）：
  混合式資料擷取架構裡手動觸發的那一半（Settings → API → FinMind → 驗證 →
  正規化 → repositories → SQLite）。單一股票失敗絕不會讓整批中止；碰到速率
  限制會停止繼續抓取，但會明確回報所有剩下沒抓到的股票，絕不悄悄漏掉；用
  同一個日期/期別/除息日重新擷取會 upsert，不會產生重複資料。
- **驗證**（`app/services/market_data_validation.py`）：每次寫入 DB 前都會做
  OHLC 合理性檢查，跟 `app.analytics` 完全獨立。
- **Settings 介面**：「Update Market Data」按鈕，顯示狀態、處理的資產數、
  成功/失敗的股票及原因、驗證警告、最新資料日期、資料來源。
- **62 個新測試**（56 個後端，把後端總數拉到 193；6 個前端，把前端總數拉到
  41——總共 234 個測試）。

## 已實作（Phase 6）

- **三大法人**（`institutional_flows` 表）：每日三大法人買/賣/淨額（股數），
  以 `(asset, date)` 為鍵。FinMind 原始的五個分類
  （`Foreign_Investor`、`Foreign_Dealer_Self`、`Investment_Trust`、
  `Dealer_self`、`Dealer_Hedging`）被歸併成慣用的外資/投信/自營商三分法——
  詳細歸併方式見 `InstitutionalFlowDTO` 的文件字串，注意任何分類缺少其中一個
  類別時會回傳 `None`，而不是回傳一個不完整加總的數字。
- **融資融券**（`margin_trading` 表）：每日融資融券，以 `(asset, date)` 為鍵。
  **所有欄位單位都是「張」（1,000 股）**，已對照 FinMind 的即時 API 並比對
  TWSE 官方公布的融資餘額同一股票/日期驗證過（見 `MarginTradingDTO` 的文件
  字串）——不要當成股數。
- **月營收**（`monthly_revenue` 表）：以 `(asset, revenue_year,
  revenue_month)` 為鍵——是*營收所屬*的月份，不是 FinMind 的 `date` 欄位
  （那是公告月份）。年增率/月增率是讀取時計算（`ResearchService._revenue_growth`），
  不會持久化儲存；比較期間缺資料或會導致除以零時回傳 `None`，絕不假造成 0%。
- **技術指標**（`app/analytics/technical.py`）：SMA、EMA、Wilder's RSI、
  MACD、布林通道、台灣慣例 KD（2/3 舊值 + 1/3 新值平滑，不是課本上的標準
  stochastic）、ATR（已實作，尚未接進 API 回應）。全是純函式——沒有 DB/HTTP/
  FastAPI 的 import，由自動化測試強制驗證
  （`tests/unit/test_analytics_independence.py`），跟 Phase 2 的計算引擎有
  一樣的獨立性保證。每個函式都是索引對齊且不會有前視偏誤：`result[i]` 只依賴
  `input[0..i]`，每個指標都有專門的「不前視」測試驗證過。都是從
  `price_history` 即時計算——沒有快取表。
- **Research API 擴充**：`GET /api/research/{ticker}/institutional`、
  `/margin`、`/revenue`、`/technical`（最後這個可以帶一個選填的 `as_of` 日期，
  計算「以歷史某天為準」的指標，同樣不會前視）。每個回應都帶有 `source`
  （`FINMIND` 或 `CALCULATED`），確保計算出來的指標絕不會被誤呈現成資料
  供應商提供的原始數據。
- **選股器擴充**：新增 `foreign_net_buy_gt`、`rsi_lt`/`rsi_gt`、
  `above_sma_20` 篩選條件，每個結果也新增
  `foreign_net_buy`/`rsi_14`/`above_sma_20` 欄位。底層資料還沒有時回傳
  `None`（不是假造的數值）。
- **資料擷取擴充**：`MarketDataIngestionService` 新增三個 best-effort 區塊
  （三大法人/融資融券/月營收），跟基本面/股利用同一套模式——單一資料集失敗
  絕不會擋住其他資料集，而 `RateLimitError` 仍然會讓整批停止，不會被吸收成
  單一股票的警告。
- **Research 頁面**：K 線 + 成交量圖（`lightweight-charts`，取代 Phase 4
  的折線圖），加上新的技術指標、三大法人、融資融券/月營收區塊——都能從既有的
  股票選擇器進入，不需要改動導覽結構。
- **88 個新後端測試**（把總數拉到 281）和 **12 個新前端測試**（把總數拉到
  53——總共 334 個）。新的 Alembic migration（`b1e14c304976`）已在乾淨的 DB
  上驗證過。

## 這個階段確立的關鍵架構決策

- **持倉是依 `(account_id, asset_id)` 動態推導出來的**，從不直接儲存——
  `transactions` 是唯一的真實來源（詳細的成本基礎運算見 `Transaction` 的
  文件字串）。
- **`Asset.valuation_method`**（`TRANSACTION_BASED` vs
  `MANUAL_MARKET_VALUE`）讓全球 ETF 基金可以用同一套 schema 表示，不用另外
  設計第二套結構——慣例說明見 `Asset` 的文件字串。
- **V1 只支援台幣。** `fx_rates` 已經存在於 schema 裡，這樣 V2 加多幣別支援
  時不用再跑一次 migration，但目前還沒有任何東西會寫入這個表；單一貨幣是在
  service 層強制（Phase 3 之後），不是靠 DB 限制。
- **所有金額/數量欄位都是 `NUMERIC`**，對應到 Python 的 `Decimal`——絕不用
  `float`。
- 計算引擎（Phase 2）不會 import 任何 FastAPI 或 SQLAlchemy 的東西，所以它
  能被未來的規則/訊號引擎或是以 Claude 為基礎的分析服務重複使用，不需要重構。

## 已實作（Phase A —— 風險引擎 + Benchmark）

實作**個股訊號引擎規格書**（2026-09-14 確認）裡的風險硬性限制與 benchmark/
alpha 需求——這是 Phase 2 計算引擎特地保留可重用性、留給未來訊號引擎用的
第一塊拼圖（見下方「關鍵架構決策」）。在 `/api/analytics` 新增三個
endpoint：

- **`GET /api/analytics/risk`**（擴充）—— `position_limit_violations` 和
  `sector_limit_violations` 現在會比較每個 STOCK 持倉的權重是否超過確認過的
  硬性限制（`position_limit_pct` 15%、`sector_limit_pct` 30%）。**只針對
  個股這塊資產**（`asset_type == "STOCK"`）：權重是佔「僅個股」小計的比例，
  不是佔總資產淨值的比例——早期版本是拿全部資產（包含現金和全球 ETF 基金）
  來比較，結果把*刻意*的被動配置標記成「集中度風險」。這完全是搞反了；這些
  限制的目的是監督這個系統自己選股的行為，不是監督整個帳戶。詳見
  `app/analytics/risk_limits.py` 和 `tests/api/test_analytics.py` 裡對應的
  回歸測試。
- **`GET /api/analytics/drawdown`** —— 投資組合從高點的回撤幅度，對照確認過
  的兩段式斷路器（`-15%` → `PAUSE_NEW_POSITIONS`、`-25%` → `HARD_STOP`）。
  從既有的 `transactions` + `price_history` 回溯重建出完整的權益曲線
  （`app/analytics/history.py`）——不需要每日快照工作就能馬上開始使用，也不用
  等未來資料累積。還沒有交易歷史時回傳 `null`。
- **`GET /api/analytics/benchmark`** —— 投資組合報酬 vs. 一個設定好的被動
  benchmark（`BENCHMARK_TICKER`，預設 `0050`）在同一個時間窗口的表現，以及
  算出來的 alpha（`app/analytics/benchmark.py`）。因為使用者本身已經直接持有
  大盤曝險，這才是個股操作真正該追求的成功指標——超越已經被動持有的部分，
  不是單純的勝率。
  - **一次性設定**：benchmark 股票代號必須先存在為一個有真實股價歷史的
    `Asset`，跟其他資產一樣——`POST /api/assets`
    （`{"ticker": "0050", "name": "元大台灣50", "asset_type": "ETF",
    "market": "TWSE", "currency": "TWD"}`），然後跑一次「Update Market
    Data」。在那之前這個 endpoint 會回傳 `benchmark_return_pct: null`，
    並附上說明原因的 `note`，絕不會假造一個數值。

風險限制與 benchmark 股票代號都可以透過環境變數設定
（`RISK_POSITION_LIMIT_PCT`、`RISK_SECTOR_LIMIT_PCT`、
`RISK_DRAWDOWN_PAUSE_PCT`、`RISK_DRAWDOWN_STOP_PCT`、`BENCHMARK_TICKER`——
見 `app/config.py`）；15%/30%/-15%/-25% 這些預設值是跟使用者確認過的工程
預設值，不是寫死的硬性需求。

**36 個新測試**（28 個後端單元測試/API 測試，這個階段沒有前端變動）——
`tests/unit/test_risk_limits.py`、`tests/unit/test_history.py`、
`tests/unit/test_benchmark.py`，以及 `tests/api/test_analytics.py` 的新增
測試。

**這個階段沒做的事**：規格書裡精簡過的 20 檔觀察名單（從 41 檔依流動性+
分散度篩到 20 檔，已經套用在另一個獨立的 看盤台 artifact 自己的觀察名單裡）
還沒有種進*這個*系統自己的 `assets`/`watchlist` 表，所以這裡的 `sector`
分組目前反映的還是實際買了什麼（demo 資料裡的 2 檔台股），不是那 20 檔
候選池。上面三個 endpoint 都還沒有前端介面。沒有每日/排程評估——這些都是
拉取式（呼叫 endpoint、拿到今天的狀態），跟 V1 其他部分一樣是手動刷新模式。

## 已實作（Phase 7 —— 綜合評分 + 訊號引擎 + LINE 通知）

- **綜合評分**（`app/analytics/scoring.py`、
  `app/services/scoring_service.py`，新的 `scores` 表）：四個風格子分數
  （價值/成長/動能/品質），每個 0-100 或 `null`（當輸入資料缺失時）——絕不會
  假造一個 50 分的「中性」。市場多空判讀（`BULL`/`BEAR`/`NEUTRAL`，來自
  TAIEX 自己的 SMA50/SMA60 關係）決定用哪一套權重表把子分數合併成一個綜合
  分數，且能感知 `None`（缺失的子分數會被剔除，剩下的權重重新正規化）。
  **每一個門檻值/權重都是 V1 的暫定值**——方向上合理，但還沒有用這個市場
  自己的報酬資料做過實證驗證。每次「Update Market Data」執行時，每個資產
  計算並儲存一次（`GET /api/research/{ticker}/score`、`/scores` 查歷史）；
  新增的 `INDEX` 資產型別追蹤 TAIEX，純粹用於多空判讀（絕不會是投資組合裡的
  持倉）。
- **確定性訊號引擎**（`app/analytics/signals.py`、
  `app/services/signal_service.py`）：8 個獨立的 BULLISH/BEARISH/NEUTRAL/
  UNAVAILABLE 訊號——`PRICE_ABOVE_SMA20`/`60`、`RSI_BULLISH`、
  `MACD_BULLISH`（技術面）、`FOREIGN_NET_BUYING`/
  `INVESTMENT_TRUST_NET_BUYING`（三大法人，過去5日淨額）、
  `REVENUE_GROWTH_POSITIVE`/`_ACCELERATING`（基本面），以及
  `COMPOSITE_SCORE`（讀取上面已經計算好的綜合評分，絕不會重新計算）。
  **一個訊號不是投資建議**——BULLISH/BEARISH 描述的是指標本身的讀數，絕不是
  「買/賣」指令；資料不足時是 UNAVAILABLE（絕不假造成 NEUTRAL）。是即時
  計算、不會持久化儲存（`GET /api/research/{ticker}/signals`，可選填
  `as_of`）——不會有前視偏誤，每種訊號類型都有專屬測試用帶日期的序列驗證過。
  `overall_status` 是對所有非 UNAVAILABLE 訊號做不加權多數決（V1，已記錄
  在文件裡）。
- **LINE 通知**（`app/services/line_notifier.py`）：執行仍然 100% 手動——
  這只會在「Update Market Data」執行後，當某個資產有任何訊號是
  BULLISH/BEARISH 時發送 LINE 訊息；要不要行動、要不要下單完全由你自己
  決定。**這個程式庫裡沒有任何東西會呼叫、也永遠不會呼叫券商 API。** 用的是
  LINE Messaging API 的 `broadcast` endpoint（LINE Notify 已於 2025-03-31
  停止服務）——個人單人 bot 廣播給「所有加它為好友的人」其實就只有你，不需要
  公開 webhook。每個資產一則整合訊息（非中性訊號 + 綜合評分/多空判讀），
  沒有任何要回報的資產不會發送。Best-effort：沒設定
  `LINE_CHANNEL_ACCESS_TOKEN` 就會靜默停用；發送失敗會記錄成一筆
  `validation_warnings`，絕不會擋住整批資料擷取。**一次性設定**：在
  [LINE Developers Console](https://developers.line.biz/console/) 建立
  一個免費的 LINE 官方帳號/Messaging API channel，用手機把這個 bot 加為
  好友，把 channel access token 放進 `backend/.env` 的
  `LINE_CHANNEL_ACCESS_TOKEN`。排程（例如每日自動執行而不只是手動點擊
  「Update Market Data」）這個階段明確不在範圍內。
- **Research 頁面**：新增綜合評分區塊（子分數長條圖、多空判讀標籤、趨勢圖）
  和訊號區塊（依分類分組、一個「整體」標籤、可展開查看每個訊號的數值/門檻/
  說明）——兩個都能從既有的股票選擇器進入。
- **這個階段沒做的事**：沒有 `signals`/`signal_history` 表（設計上就是即時
  計算，見上面——沒有 `/signals/history` endpoint）；選股器沒有訊號狀態篩選；
  LINE 通知沒有排程（只有手動「Update Market Data」觸發）；沒有任何
  AI/LLM/RAG 層、沒有自動下單、沒有任何形式的券商 API 整合。
- **115 個新後端測試**（把總數拉到 432）和 **16 個新前端測試**（把總數拉到
  69——總共 501 個）。新的 Alembic migration（`986c58d676b5`，新增 `scores`
  表和 `INDEX` 資產型別）已在乾淨的 DB 上驗證過。

## 已實作（Phase 8 —— 風險閘門推薦引擎）

在這個系統裡直接實作外部**個股訊號引擎規格書**的**Phase B**
（「個股推薦引擎規格書」）—— 看盤台（一個獨立的、以 Artifact 為基礎的
儀表板）同時作為呈現介面和資料來源都被退役（它每次刷新都要即時重新查詢
Claude 分析每一檔股票，這正是這個系統改用確定性 FinMind API 方式想避免的
token 成本）。它原本的 20 檔候選觀察名單已經從它自己的資料庫拉出來，變成
這裡真正的候選池（`scripts/seed_watchlist_20.py`）。

- **策略版本化**（`app/models/strategy_version.py`、
  `app/services/strategy_service.py`）：訊號引擎可調整的參數（SMA週期、
  RSI週期、三大法人觀察窗、綜合評分門檻——`app/analytics/signal_rules.py`）
  是一筆版本化、可稽核的紀錄，不是寫死的常數。永遠只有一個版本是 `ACTIVE`。
  一個提案如果跟目前啟用版本的*參數名稱完全相同*（只是數值不同）算「小
  變動」，會立即自動套用；如果新增或移除了某個參數則算「大變動」，會排進
  待確認佇列（`PendingStrategyChange`）——絕不會悄悄自動升級。每個版本/提案
  都可以附帶一個 walk-forward 命中率回測
  （`app/analytics/signal_backtest.py`，逐日重播真實股價歷史，只用當天
  能取得的資料——跟看盤台自己那套 client-side 回測概念一樣，用 Python
  重新實作）。
- **每日只顯示變動的掃描**（`app/services/recommendation_service.py`）：
  對觀察名單裡每個資產，用目前啟用策略的規則計算今天的訊號，並跟上次掃描
  的結果（`SignalSnapshot`）比對差異——狀態沒變的股票絕不會產生
  `Recommendation` 紀錄。跟既有的手動「Update Market Data」流程綁在一起
  （這個階段仍然沒有排程器）。
- **風險閘門是事前檢查，不是事後補救**：每一則 `CONSIDER_INCREASE`
  推薦都會在建立*之前*先過 Phase A 的 `/api/analytics/risk` 和
  `/api/analytics/drawdown` 檢查。已經達到或超過 15%/30% 限制的股票/產業，
  或投資組合處於 `PAUSE_NEW_POSITIONS`/`HARD_STOP` 回撤狀態，會被標記
  `risk_blocked` 並附上原因——用的是今天實際的持倉/產業權重，因為這些推薦
  本來就沒有下單數量，沒辦法推算出一個假設性的交易後權重。
  `CONSIDER_DECREASE`/`WATCH` 永遠不會被閘門擋住（減碼/觀察永遠允許）。
  LINE 通知（Phase 7）現在改成每建立一則 `Recommendation` 才發送一次——只在
  狀態真的變化時，不是每次執行都發。
- **只用條件式語氣**：推薦只會是 `WATCH`/`CONSIDER_INCREASE`/
  `CONSIDER_DECREASE`——絕不是「買/賣」的斷言,跟 Phase 7 訊號的原則一樣。
- **新頁面**：Recommendations（依分類分組的列表，被風險閘門擋住的項目在
  視覺上明顯不同，可展開查看觸發的訊號細節）和 Strategy（目前啟用版本的
  規則、版本歷史、待確認佇列附回測前後對照與確認/拒絕按鈕）。
- **這個階段沒做的事**：沒有自主 agent 提出策略變更（那是外部規格書自己的
  Phase C——這個階段是人透過 `POST /api/strategy/versions` 提出變更，這個
  階段交付的是版本化/佇列的基礎設施），沒有排程器（只有手動觸發，跟系統
  其他部分一致）。
- **37 個新後端測試**（把總數拉到 469）和 **10 個新前端測試**（把總數拉到
  79——總共 548 個）。新的 Alembic migration（`3f4678288422`，新增
  `strategy_versions`/`signal_snapshots`/`recommendations`/
  `pending_strategy_changes`）已在乾淨的 DB 上驗證過。

## 維運修復（2026-09-16，Phase 8 之後）

- **Transactions 頁面的刪除不會再悄悄失敗** —— 一次被「股數不足」重播檢查
  （或其他任何錯誤）拒絕的刪除操作，現在會在該筆資料旁邊顯示錯誤訊息，
  而不是什麼都沒發生。
- **找到並修好兩個影響正式環境的資料完整性 bug**，都在原始的示範資料集裡，
  根源都是 `seed.py` 的假資料在這 7 檔股票有真實資料進來之後從未被完全
  取代——完整根因分析見 `DEVLOG.md`。兩個都從 Phase 7 上線以來，一直在
  悄悄把錯誤的數值餵進 Research 和 Recommendations 頁面，不只是影響回測：
  - 14 筆過期的週末 `MOCK` 股價紀錄（假資料把每個*日曆*日都填滿，包含
    週末；真實資料擷取只會碰交易日）——已刪除，連同用這些資料算出來的
    `Score` 紀錄一起刪除。
  - 7 筆過期的 `Fundamentals(period="TTM", source="MOCK")` 紀錄，因為用
    字串排序會排在真實的季度期別*之後*（`"TTM" > "2026Q2"` 當字串比較），
    結果被誤判為「最新一期」，導致每個示範股票都出現假的約 -90% 營收成長
    數字——已刪除。
- **存在非正式的回測/策略調整研究**（正向 vs. 反向訊號操作、基本面篩選、
  獲利因子/回撤分析）——見 `DEVLOG.md` 裡 2026-09-16 的條目。全部都只是
  對著系統真實訊號引擎做的草稿式探索；**沒有任何一項是正式上線的功能**，
  也沒有任何 `StrategyVersion` 因此被更改過。

## 已實作（Phase 12 —— Gemini 多代理人研究團隊）

附掛在 Phase 8 決定性引擎旁邊的敘事研究層——絕不取代它。每天掃描產生的
每一筆 `Recommendation`，都會由三個 Gemini agent 各自產生一份研究意見：

- **基本面研究員、技術面研究員、投資組合經理人**
  （`app/services/agent_research_service.py`）：每個角色有自己的結構化
  輸出 Pydantic schema（`FundamentalCallSchema`/`TechnicalCallSchema`/
  `PortfolioManagerCallSchema`）——一個 `call`（BULLISH/BEARISH/
  NEUTRAL/UNAVAILABLE，沿用 Signal 自己的詞彙）、一個 `confidence`
  （0-100），以及該角色專屬的 3-4 個固定、有標籤的一句話欄位（例如基本面
  研究員的 `revenue_trend`/`profitability`）——不是一段自由發揮的長文字，
  這是第一次真實掃描的輸出讀起來像一整篇文章之後改的。基本面/技術面
  兩個角色直接沿用 `ResearchService` 既有的資料存取方法（不新增查詢）；
  投資組合經理人額外看得到另外兩個角色自己的輸出，加上決定性
  `Recommendation` 已經做出的 action/風控結果——當成它可以評論或不同意、
  但永遠不能改變的固定背景資訊。
- **`GeminiClient`**（`app/services/gemini_client.py`）：跟
  `LineNotifier` 一樣「沒設定就停用」的模式——沒設定 `GEMINI_API_KEY`
  就是 no-op。遇到 `429`/`503` 會重試一次（先等 5 秒、再等 15 秒）——
  Gemini 免費層把 `gemini-3.8-flash` 限制在每分鐘 5 次請求，一次掃描只要
  有幾檔股票變化 × 3 個角色，一次爆發性送出就會超過這個上限。
- **KPI 直接沿用 Phase 10 的資料，沒有另外做一次評分**
  （`app/services/agent_performance_service.py`、
  `GET /api/agent-performance/summary`）：每個角色的 `call` 拿去跟決定性
  引擎自己的 call 已經在比對的同一個 `RecommendationOutcome.actual_direction`
  比對。
- **刻意不讓 LLM 碰**：風控/合規維持既有的 Phase A 規則引擎——讓 LLM 把關
  財務決定，會重新引入這整個專案從第一個階段就刻意設計避開的幻覺風險。
- **Recommendations 頁**：每個角色的分析在既有的展開列裡顯示成一張標籤
  卡片（判斷徽章、信心度、欄位內容、`key_risk` 用紅色標示）。**Review
  頁**：新增「Agent Performance」區塊，每個角色一張命中率卡片，跟上面
  決定性引擎的卡片一樣，樣本不足就老實顯示「insufficient sample」。
- **找到並修好一個真的會影響測試隔離性的 bug**：一旦本機 `.env` 裡有真的
  `GEMINI_API_KEY`，任何沒有明確替換掉 Gemini client 的測試，都會在跑
  `pytest` 時真的打出去、真的被計費——修法是加一個 `get_gemini_client()`
  依賴注入介面，再加一個 `tests/conftest.py` 裡的全域 `autouse` fixture，
  不管本機 `.env` 內容是什麼，一律強制停用。
- **新增 24 個後端測試**（總數拉到 536）；前端測試改寫以符合新的卡片
  格式（總數維持 113 個）。兩個新的 Alembic migration（`a3ea98c9cdec`
  新增 `agent_analyses`；`40ca7918d59f` 把 `rationale` 改成 `details`）
  都在乾淨的 DB 上驗證過。
- **這個階段沒做的事**：沒有總經/新聞感知角色（需要即時工具呼叫——這會
  真的違背這個專案「決定性、可重現、不依賴即時網路」的原則）；agent
  沒有記憶自己對同一檔股票過去講過什麼；沒有依照 agent 自己的 KPI 動態
  調整信任度（KPI 資料已經有了，還沒有任何東西拿它來做事）。

## 還沒做的事

市場資料擷取可以手動執行（Settings →「Update Market Data」）或透過作業
系統層級的 Windows 工作排程器每天跑一次——見上面的「市場資料」——但系統
內部仍然沒有排程器/cron；LINE 通知和 Phase 8 的每日掃描都只是搭著任何一種
觸發方式順便執行。沒有任何形式的自動交易。沒有通用的歷史時間序列績效功能
（Phase A 的權益曲線是專門為回撤/benchmark 打造的——見上面，不是一個可重用
的 `/api/analytics/performance-over-time`）。沒有市值/股息率選股器篩選條件
（schema 已經有 `shares_outstanding`，但免費版 FinMind 沒辦法填入資料），
沒有 CSV 匯入匯出介面（endpoint 存在，還沒有前端），沒有帳戶新增/編輯介面。
富邦 Nano 證券沒有官方 API/匯出/Open Banking 路徑（Phase 5 Discovery
Report 已確認）——它的持倉是透過既有的 `MANUAL_MARKET_VALUE` 模式追蹤，
跟全球 ETF 基金一樣。

到 Phase 12 為止：沒有自主 agent 迭代策略版本（個股訊號引擎規格書自己的
Phase C——這個階段提出變更是人/API 操作，不是背景工作），除了上面的
walk-forward 命中率檢查之外沒有其他回測功能（沒有完整的交易模擬器），
沒有公開資訊觀測站的重大訊息資料（FinMind 沒有這個
資料集——需要第二個對接 TWSE/TPEx 自己 OpenAPI 的資料來源，依 Phase 5
Discovery Report 已記錄的備援方案），沒有即時資料，沒有借券/產業鏈/
ETF 專屬資料集。完整的優先順序排名見專案歷史裡的 Phase 6 報告，訊號引擎
路線圖見個股訊號引擎規格書。
