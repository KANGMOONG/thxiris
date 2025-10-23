# Iris Bot Project PRD

## 1. Project Overview
- Iris SDK based KakaoTalk chatbot that aggregates financial data, AI generation, and community utilities.
- `irispy.py` hosts the bot event loop, dispatching user commands to feature modules living under `bots/`.
- External REST APIs (Binance, Upbit, Bithumb, Naver, Google Gemini/Imagen) provide realtime market data and AI responses.
- Persistent user state (for example coin portfolios or ban lists) lives in Iris `PyKV` storage.

## 2. User Scenarios
- **General user** requests: cryptocurrency snapshots (`!coin`, `!binance`, `!kimchi`), bundled reports (`!three` style commands), stock snapshots (`!stock <ticker>`), or AI content (`!gi prompt`, `!analyze` on image replies).
- **Investor** workflows: register holdings via `!coinadd <symbol> <amount> <avg>`; check portfolios with `!coin` or favorites via `!favlist`.
- **Operator** tools: moderate chats (`!ban`, `!unban`), execute Python snippets (`!ipy`, `!iev`), monitor nickname changes (background thread).
- **New member** greetings: automatic welcome/farewell replies including media (`res/welcome.jpeg`).

## 3. Functional Requirements
- **Cryptocurrency**
  - Fetch Binance candles and render Binance-style PNG charts (`bots/bicharttest.py`, `bots/bicharttest2.py`).
  - Query Upbit/Bithumb tickers, kimchi premium, and USD/KRW rates; compute user PnL using `PyKV` (`bots/coin.py`, `bots/ThreeIdoit.py`).
- **Stocks**
  - Retrieve Naver Finance metadata, realtime data, and chart image; compose an information card with Pillow (`bots/stock.py`).
- **AI / Content**
  - Google Gemini: text-to-image, image-to-image, and image moderation (`bots/gemini.py`).
  - Imagen: additional image generation pipeline (`bots/imagen.py`).
  - GPT URL summarizer (`bots/gpt_url_summary.py`), lyrics finder (`bots/lyrics.py`), text overlay images (`bots/text2image.py`), meme responses (`bots/replyphoto.py`, `bots/test_img.py`).
- **Operations**
  - Ban control via decorators (`helper/BanControl.py`), nickname change detection (`bots/detect_nickname_change.py`).
  - Support utilities and experiments (`bots/excel_test.py`, `bots/naverglobal.py`, `bots/globalstock.py`, `bots/stocktest.py`, `bots/check_test.py`).

## 4. Non-Functional Requirements
- Graceful handling of third-party API failures with user-friendly replies and logging.
- Use PNG/JPEG outputs for chart assets; leverage fonts under `res/`.
- Secrets (Gemini key, Imagen cookies) populate environment variables as guided in `README.MD`.
- Ensure thread safety where nickname detection thread interacts with the bot runtime.

## 5. Architecture
- **Application layer**: `irispy.py` orchestrates message, member, and error events.
- **Service layer**: individual `bots/*.py` modules encapsulate command logic and external integrations.
- **Data layer**: Iris `PyKV` store for user state; remote REST APIs for market and AI data.
- **Assets**: `res/` directory for static images and fonts; `res/temppic/` for temporary outputs.

## 6. Key Module Responsibilities
- `irispy.py`: command routing, KakaoLink setup, background nickname watcher, event handling.
- `bots/bicharttest.py`: Binance mobile-style candlestick chart generator.
- `bots/bicharttest2.py`: Binance web-style chart renderer with header info bar.
- `bots/coin.py`: comprehensive coin commands (Upbit, Binance, kimchi premium, exchange rate, portfolio CRUD).
- `bots/ThreeIdoit.py`: bundled coin reports combining Upbit and Bithumb data.
- `bots/stock.py`: Naver Finance driven stock info card generator.
- `bots/gemini.py`: Gemini integration with streaming responses and safety configuration.
- `bots/imagen.py`: Imagen API wrapper for alternative image generation.
- `bots/gpt_url_summary.py`: fetch and summarize external pages via GPT.
- `bots/lyrics.py`, `bots/favoritecoin.py`, `bots/text2image.py`, `bots/replyphoto.py`, `bots/test_img.py`, `bots/excel_test.py`, `bots/naverglobal.py`, `bots/globalstock.py`, `bots/stocktest.py`, `bots/check_test.py`: auxiliary response features and experiments.
- `helper/BanControl.py`: admin-only ban/unban logic backed by `PyKV`.
- `res/*.otf|ttc`: typography used by chart/image generators.
- `README.MD`: installation, environment configuration, deployment notes, change log.
- `requirements.txt`: Python dependency manifest.
- `test.py`, `testlocal.py`: local smoke or ad-hoc testing scripts.

### 6.1 `bots/coin.py` Detailed Flow
- `get_coin_info`: top-level dispatcher matching user commands (e.g., `!coin`, `!binance`, `!kimchi`, `!usd`, `!coin-add`, `!coin-remove`, `!coin-list`) and routing to helper functions.
- `get_upbit` / `get_upbit_korean`: fetch single KRW markets from Upbit, resolve Korean names when needed, and append user PnL details from `PyKV` if the coin is registered.
- `get_my_coins`: retrieve all holdings from `PyKV`, query Upbit tickers in batch, compute evaluation amount, invested capital, and percent gain, then reply with a consolidated report.
- `get_upbit_all`: list all KRW markets ordered by signed change rate to provide a market-wide snapshot.
- `get_binance`: iterate Binance 24h ticker data, normalize cross pairs, convert to KRW using the latest USD rate, and report price/change plus kimchi premium adjustment.
- `get_kimchi_premium`: compare Binance BTCUSDT against Upbit KRW-BTC to calculate the kimchi premium and present both USD and KRW valuations.
- `usd_to_krw`: convert arbitrary USD amounts using the Naver currency API and reply with formatted KRW equivalents.
- `coin_add` / `coin_remove`: validate symbols against Upbit, then mutate `PyKV` (`coin.<user_id>`) entries to persist or delete holdings.
- Shared utility `get_USDKRW` feeds exchange rates to multiple functions; failures are caught to reply with informative error messages while logging exceptions.

### 6.2 Cross-Module Relationships & Process Logic
- **Command Dispatch (`irispy.py`)**
  - Central match/case dispatcher that maps raw chat commands to feature handlers across `bots/`.
  - Decorators (`@has_param`, `@is_admin`, `@is_not_banned`, `@is_reply`) guard access before delegating.
  - Maintains shared resources: global `Bot` instance, `IrisLink` for media replies, background nickname watcher (`bots/detect_nickname_change.py`).
- **Feature Modules**
  - `bots/coin.py` ↔ `PyKV`: stores per-user holdings under `coin.<user_id>`, reused by `get_coin_info` variants.
  - `bots/ThreeIdoit.py` reuses coin utilities to bundle fixed tickers, combining Upbit and Bithumb APIs.
  - `bots/stock.py` consumes Naver endpoints and `res/*.otf` fonts to build composite PNGs, then replies through the dispatcher.
  - `bots/gemini.py`, `bots/imagen.py`, `bots/text2image.py` form the AI stack; all return via `chat.reply_media`, and depend on environment variables defined in `README.MD`.
  - `bots/replyphoto.py`, `bots/test_img.py`, `bots/excel_test.py` act as utility responders, accessing static assets in `res/`.
- **State & Moderation**
  - `helper/BanControl.py` updates `PyKV` key `ban`, while `@is_not_banned` in `irispy.py` reads it to short-circuit prohibited users.
  - `bots/detect_nickname_change.py` runs in a separate thread but shares the bot URL for callbacks.
- **Execution Sequence**
  1. Incoming chat event → `irispy.py` matches command.
  2. Access checks pass → designated module fetches external data (Binance/Upbit/Naver/Gemini…).
  3. Module post-processes via Pandas/NumPy/Matplotlib/Pillow or streams AI responses.
  4. Replies (`chat.reply` / `chat.reply_media`) propagate back through Iris to the Kakao client.
  5. Optional state writes occur through `PyKV`, enabling future contextual replies.

### 6.3 Text Diagram
```
User Message
    ↓
irispy.py (event dispatcher)
    ↓
┌────────────────────────────┐
│ Feature Modules            │
│                            │
│  • bots/coin.py ─────┐     │
│  • bots/stock.py     │     │
│  • bots/gemini.py    │     │
│  • bots/imagen.py    │     │
│  • bots/text2image.py│     │
│  • bots/ThreeIdoit.py│     │
└──────────────┬───────┘     │
               │             │
        External APIs        │
   (Binance, Upbit, Naver,   │
    Gemini/Imagen, etc.)     │
               │             │
      Processed response     │
               ↓             │
        chat.reply(*) ←──────┘
               ↓
         KakaoTalk user

State Storage (PyKV)
 ├─ coin.<user_id>  ← bots/coin.py, bots/ThreeIdoit.py
 └─ ban             ← helper/BanControl.py / decorators

Assets (res/)
 ├─ Fonts (OTF/TTC) ← bots/stock.py, bots/text2image.py
 └─ Images (JPG/PNG)← bots/replyphoto.py, bots/test_img.py
```

## 7. Data Flow
1. Iris bot receives a message event.
2. Command dispatcher routes to the matching module function.
3. Module performs input validation via decorators, calls external APIs, converts data (Pandas/NumPy), and renders text or images (Matplotlib/Pillow).
4. Responses are returned through `chat.reply` or `chat.reply_media`.
5. Persistent state reads/writes use `PyKV` with namespaced keys (for example `coin.<user_id>`).
6. Errors bubble to `@bot.on_event("error")` for logging.

## 8. API Integrations
- Binance REST: `/api/v3/klines`, `/api/v3/ticker/24hr`, `/api/v3/ticker/price`.
- Upbit REST: `/v1/market/all`, `/v1/ticker`.
- Bithumb REST: `/v1/market/all`, `/v1/ticker`.
- Naver Finance REST and image endpoints.
- Naver currency search API for USD/KRW.
- Google Gemini via `google-genai` SDK (streaming).
- Imagen unofficial web API (cookie based).

## 9. Dependencies
- Core Python libs: `requests`, `pandas`, `numpy`, `mplfinance`, `matplotlib`, `Pillow`, `pytz`, `beautifulsoup4`, `yfinance`.
- Iris SDK: `iris`, `iris.decorators`, `iris.bot`, `iris.kakaolink`.
- Listed explicitly in `requirements.txt`.

## 10. File Tree (condensed)
```
.
|- bots/
|  |- __init__.py
|  |- bicharttest.py
|  |- bicharttest2.py
|  |- check_test.py
|  |- coin.py
|  |- detect_nickname_change.py
|  |- excel_test.py
|  |- favoritecoin.py
|  |- gemini.py
|  |- globalstock.py
|  |- gpt_url_summary.py
|  |- gpt_url_summary_test.py
|  |- imagen.py
|  |- lyrics.py
|  |- naverglobal.py
|  |- pyeval.py
|  |- replyphoto.py
|  |- stock.py
|  |- stocktest.py
|  |- test_img.py
|  |- text2image.py
|  |- ThreeIdoit.py
|- helper/
|  |- __init__.py
|  |- BanControl.py
|- res/
|  |- temppic/.gitignore
|  |- *.jpeg|jpg|png
|  |- *.otf|ttc
|- irispy.py
|- README.MD
|- requirements.txt
|- test.py
|- testlocal.py
```

## 11. Risks and Mitigations
- **External API instability**: add retries, better error surfacing to users.
- **String formatting issues**: audit f-strings for encoding/format bugs, enforce ascii fallbacks.
- **File overwrite risks**: parameterize output paths for chart/image generators.
- **Secret expiration**: implement startup validation for required environment variables.
- **Data schema changes**: document `PyKV` structure and plan for migration scripts.

## 12. Future Improvements
1. Centralize exception handling and introduce structured logging (file or external service).
2. Provide an auto-generated `!help` summary using the command map.
3. Expand automated tests covering key commands and image generation.
4. Externalize configuration (API base URLs, chart save paths) into a settings module.
5. Consider rate-limit aware caching for high-traffic API calls.
