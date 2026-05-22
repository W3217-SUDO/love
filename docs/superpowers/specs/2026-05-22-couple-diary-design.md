# 双人协作健康/亲密日记 Web App — 设计文档

**版本**: v1.0
**日期**: 2026-05-22
**作者**: 与用户协同 brainstorming
**状态**: 待用户复核 → 进入 writing-plans

---

## 1. 项目目标

为单一情侣（你 + 伴侣，固定 2 人）打造一个仿 [Flo](https://flo.health) 体验、双人协作的私有健康与生活记录网站。

**核心使用场景**：
- 伴侣每日记录经期、症状、心情、亲密行为、排卵迹象
- 你能在自己的端看到她共享的所有数据并做出参与（共同记录、查看趋势）
- 两人一起记录旅行相册、双人日记、亲密生活
- 系统基于多信号（日历 + BBT + LH 试纸 + 黏液 + RHR/HRV）做经期与排卵预测
- 可导入她已有的 Flo / Apple Health 历史数据，避免重录

**非目标**（明确排除）：
- 不是 SaaS：拒绝第三方注册；系统只允许 2 个固定账号
- 不接入第三方账户登录（OAuth）
- 不向外部分析平台 / 广告 / 第三方 API 推送任何数据
- 不做手机原生 App（PWA 即可装到主屏）

---

## 2. 技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| **后端框架** | FastAPI + Uvicorn | 现代异步、类型友好、生态成熟 |
| **模板引擎** | Jinja2 | 服务端渲染；与 HTMX 天然契合 |
| **交互层** | HTMX + Alpine.js | 局部刷新无需 SPA；小巧（合计 < 30 KB） |
| **图表** | Chart.js | 体积小、API 简单、双轴/混合图够用 |
| **PWA** | 原生 manifest + service worker | 装到手机主屏，离线壳 |
| **数据库** | MariaDB 10.11（复用服务器现成） | 已就绪，2 用户负载完全足够 |
| **ORM** | SQLAlchemy 2.x + Alembic | 业界标准 |
| **密码哈希** | Argon2id (argon2-cffi) | 抗 GPU 暴力的当前最优 |
| **图像处理** | Pillow + PyMuPDF | EXIF + 缩略图 + PDF 首页提取 |
| **后台任务** | APScheduler（内嵌进程） | 省去 Celery + Redis；单实例够用 |
| **Web Push** | pywebpush + VAPID | 浏览器原生推送通知 |
| **测试** | pytest + httpx + hypothesis + factory_boy | |
| **代码质量** | ruff（lint+format）+ mypy strict | |
| **部署** | systemd + Nginx + 系统用户隔离 | |

**为什么不选 SPA（Vue/React）**：
- 代码量翻倍 + 维护两套构建
- 1.9 GB 内存服务器跑 Node 构建很挤
- HTMX 已能实现 Flo 那种"点击即时保存"的体验
- 后期想升级到 SPA 时，API 端不需要重写（路由层换前端而已）

**为什么不选 Reflex / NiceGUI**：
- UI 自由度受框架限制，难精确复刻 Flo 风格
- WebSocket 长连接对小内存敏感
- 框架生态不如 FastAPI 成熟

---

## 3. 整体架构

```
┌───────────────────────────────────────────────────────────┐
│  浏览器 / PWA（手机主屏 + 桌面响应式）                          │
│  HTML (Jinja) + HTMX 局部更新 + Alpine.js 本地状态             │
└────────────────┬──────────────────────────────────────────┘
                 │ HTTPS（M1 自签证书 / 域名后切 Let's Encrypt）
                 ▼
       ┌──────────────────┐
       │  Nginx 反代       │  ← 80/443 入口，TLS 终结，静态资源
       │  （新装）          │
       └─────────┬────────┘
                 │ proxy_pass 127.0.0.1:8000
                 ▼
       ┌────────────────────────────────────┐
       │  FastAPI + Uvicorn  (systemd)       │
       │  ────────────────────────────────   │
       │  • Jinja2 模板（HTML 片段 + HTMX）   │
       │  • SQLAlchemy 2.x + Alembic         │
       │  • Argon2 + 服务端 session          │
       │  • Pillow / PyMuPDF 上传管线         │
       │  • APScheduler（预测推送 / 备份）    │
       └─────┬────────────────┬─────────────┘
             │                │
             ▼                ▼
     ┌──────────────┐   ┌──────────────────────┐
     │  MariaDB     │   │  本地文件存储         │
     │  127.0.0.1   │   │  /data/uploads/...    │
     │  (couple_    │   │  缩略图 + 原图        │
     │   diary)     │   │  (chmod 700)         │
     └──────────────┘   └──────────────────────┘
```

**关键决策**：
1. 单体应用：M1-M3 全在一个 FastAPI 进程
2. Nginx **新装**（仅作反代 + TLS），不动宝塔的 8888
3. MariaDB **复用**现成实例 + 独立账号 + **仅监听 127.0.0.1**（当前是 0.0.0.0，部署时加固）
4. 文件存本地（不上 OSS），方便备份与查看
5. 会话用服务端 cookie + sessions 表（不上 JWT）
6. 后台任务用 APScheduler 内嵌（不上 Celery / Redis）

---

## 4. 模块划分

```
/opt/couple_diary/
├── app/
│   ├── main.py                  # FastAPI app + 路由挂载 + lifespan
│   ├── config.py                # 环境变量
│   ├── db.py                    # SQLAlchemy session
│   ├── deps.py                  # 通用依赖：current_user / partner / csrf
│   ├── cli.py                   # 命令行：init-couple, generate-vapid, backup-now
│   │
│   ├── modules/
│   │   ├── auth/                # 登录、邀请绑定、会话
│   │   ├── cycle/               # 经期日志 + 预测器（策略模式）
│   │   ├── daily_log/           # Flo 全套标签 catalog + 日打勾
│   │   ├── diary/               # 文字+图片日记
│   │   ├── trip/                # 旅行相册
│   │   ├── timeline/            # 「今天」聚合 + 历史时间线
│   │   ├── media/               # 上传、压缩、缩略图、PDF
│   │   ├── chart/               # 图表数据 JSON 端点
│   │   ├── import_/             # Apple Health / Flo CSV 导入 worker
│   │   ├── health/              # BBT/RHR/HRV/Sleep 记录
│   │   └── settings/            # 偏好、可见性、备份触发、推送订阅
│   │
│   ├── templates/
│   │   ├── base.html            # 全站骨架 + PWA meta
│   │   ├── components/          # 复用片段（标签、卡片、模态、底部 nav）
│   │   └── pages/               # 路由对应页面
│   │
│   └── static/
│       ├── css/                 # Flo 主题（粉桃）
│       ├── js/                  # HTMX + Alpine + Chart.js
│       ├── icons/               # PWA 图标
│       └── manifest.webmanifest
│
├── alembic/                     # 数据库迁移
├── tests/
├── scripts/
│   ├── bootstrap.sh             # 服务器首次部署
│   └── deploy.sh                # 更新部署 + 自动回滚
├── docs/
│   ├── runbook.md               # 灾难恢复手册
│   └── superpowers/specs/       # 本文档所在
├── pyproject.toml
└── README.md

# 外部存储（不在仓库）
/data/uploads/{user_id}/{YYYY}/{MM}/{sha256[:2]}/{sha256}.{ext}
/data/backups/db/{YYYYMMDD}.sql.gz
/data/backups/uploads-mirror/...
/var/log/couple_diary/app.log
```

**模块边界规则**：
- 每个模块包含 `router.py` / `service.py` / `models.py` / `schemas.py` / 模块内 templates
- 模块间**只通过 service 层调用**，不直接 import 别人的 models
- 共享上下文通过 `deps.py` 注入（`current_user`, `current_partner`, `current_couple`）
- 一个模块 = 一个可独立重写的子树

---

## 5. 数据模型

### 5.1 核心实体关系

```
users  ─┬→  couples            (单 row，记录 2 人绑定)
        ├→  invite_tokens      (一次性，绑定后失效)
        ├→  user_settings      (主题/通知/可见性)
        ├→  sessions           (服务端 session)
        └→  push_subscriptions (Web Push 订阅)

users  →  cycle_settings        (avg_cycle_length, avg_period_length, mode)
users  →  periods               (start_date, end_date, notes)
              └→ cycle_attachments → media   (排卵试纸 / 报告)

users  →  daily_entries         (一人每日一条主记录)
              └→ daily_tags        (entry_id, category, tag_key, value)
              └→ daily_attachments → media

users  →  bbt_readings          (date, temp_c, measure_time,
                                 method ∈ {oral, vaginal, axillary, wrist, other})

users  →  health_metrics        (date, rhr_bpm, hrv_sdnn_ms, sleep_*, source)
                                (UNIQUE: user_id, date, source — 多源共存)

users  →  diary_entries         (markdown body, visibility)
              └→ diary_media → media

users  →  trips                 (title, start/end date, location, cover_media_id)
              └→ trip_members      (user_id; 2 行：双方都是成员)
              └→ trip_media → media (caption, taken_at, sort_order)

users  →  media                 (id, owner_id, kind, original_path, thumb_path,
                                 size, mime, sha256, exif_taken_at, exif_lat, exif_lng)

users  →  import_jobs           (source, filename, status, summary_json)
users  →  audit_log             (action, target_type, target_id, ts)
```

### 5.2 关键设计决策

**(a) Media 单表 + 各模块独立 link 表（不用 polymorphic）**
- `media` 只存文件本体（路径、EXIF、SHA256）
- 每个消费方有自己的 link 表（`diary_media` 等）
- 类型安全、查询简单、级联清晰

**(b) Flo 标签用「Python 常量目录文件」而非「标签管理表」**
- `app/modules/daily_log/catalog.py` 定义 ~80 个 tag_key + i18n 名称 + emoji
- 数据库只存 `(entry_id, category, tag_key, value)`
- 改标签 = 改代码 + 一次 Alembic migration（如有删除旧数据）
- 避免"标签管理"这种空 CRUD 页面

**(c) 可见性默认值**
| 数据 | 默认 |
|---|---|
| 经期 / 排卵 / BBT / LH | 双方可见 ✓ |
| 健康指标 RHR/HRV/Sleep | 双方可见 ✓ |
| 心情 / 症状 / 分泌物 | 双方可见 ✓ |
| 亲密标签 | 双方可见 ✓ |
| 旅行 | 双方可见 ✓ |
| 日记 | 默认 `private`，可手动 `shared` |
| 上传文件 | 跟随宿主记录（医疗报告可单独标 private） |

**(d) 唯一性约束**
- `(user_id, date)` 在 `daily_entries`、`bbt_readings` 唯一
- `(user_id, start_date)` 在 `periods` 唯一
- `couples` 表只允许一行（应用层强制）
- `(user_id, date, source)` 在 `health_metrics` 唯一（多源可共存）

---

## 6. 页面 & 用户流

### 6.1 全局导航
**移动端** 底部 tab bar：
```
🏠 今天    📅 日历    ➕ 记录    📓 日记    ✈️ 旅行   👥 我们
```
（`➕ 记录` 是中央凸起按钮，弹出标签 sheet）

**桌面端** 左侧 sidebar：同样 6 项，配头像 + 在一起天数。

### 6.2 路由表

| 路径 | 功能 | 谁能看 |
|---|---|---|
| `/` | **今天**：日期+周期 D 几+阶段、圆环、今日标签、TA 的今天、健康一览、排卵预测、最近日记/旅行预览 | 自己 + 共享 |
| `/login` `/logout` | 认证 | 公开 |
| `/bind?token=XXX` | 首次伴侣绑定 | token 持有者 |
| `/calendar` | 经期月历 + 预测层 + 排卵窗口 | 双方 |
| `/cycle/log` | 经期开始/结束打点 | 双方 |
| `/bbt/log` | BBT 快速录入（数字键盘 sheet） | 自己 |
| `/log/today` `/log/{date}` | Flo 标签 sheet（点击即时保存） | 双方 |
| `/diary` `/diary/{id}` `/diary/new` `/diary/{id}/edit` | 日记 CRUD | 按 `visibility` |
| `/trip` `/trip/{id}` `/trip/new` `/trip/{id}/edit` | 旅行相册 CRUD | 双方 |
| `/me` | 在一起天数、合照墙、重要日子 | 双方 |
| `/me/settings` | 可见性 / 主题 / 通知 | 仅自己 |
| `/me/backup` | 备份下载/恢复 | 仅自己 |
| `/me/import` | Apple Health / Flo CSV 导入 + 进度查看 | 仅自己 |
| `/media/{id}` `/media/{id}/thumb` | 鉴权后文件流 | 按宿主可见性 |
| `/charts/*.json` | 图表数据（cycle / mood / symptoms / bbt / health） | 按可见性 |
| `/healthz` | 探活 | 公开 |

**HTMX 内部片段端点**（不在以上表中，命名约定 `/{module}/_fragment/{name}` 或 `/today/partner-card` 等）：
- `/today/partner-card` — 「TA 的今天」聚合卡片（30s 轮询）
- `/today/predictor-card` — 排卵预测卡片
- `/log/today/tag/{tag_key}/toggle` — 标签切换
- `/diary/_fragment/list?page=N` — 日记列表分页
- `/me/import/_fragment/status/{job_id}` — 导入进度

这些端点只返回 HTML 片段（无 layout），鉴权同主路由。

### 6.3 三个关键交互模式
1. **HTMX 即时保存** — 点标签 → POST → 后端写库 → 返回新片段替换。无显式提交按钮。
2. **抽屉式 sheet（移动） / 居中模态（桌面）** — 同一段模板，CSS `@media` 决定形态。
3. **乐观 UI + 服务端校验** — 标签先视觉变色（Alpine.js），再 POST；失败回滚。

### 6.4 首次部署 / 伴侣绑定流程
```
你 SSH 上服务器：
  $ python -m app.cli init-couple --he 你名 --she 伴侣名
  ✓ 生成 invite token：
    - 你：     ABC123  → https://站点/bind?token=ABC123
    - 伴侣：   XYZ789  → https://站点/bind?token=XYZ789

你打开第一条链接 → 设置密码 → 你的账号生效
把第二条链接发给伴侣 → 她设置密码 → 自动绑定 couple
之后 /login 用用户名+密码登录
注册接口不存在 — 系统封闭
```

### 6.5 关键页面草图（today.html 逻辑结构）

```
┌─────────────────────────────────────────┐
│  〈     今天 · 2026.05.22       〉      │
│              月经周期第 20 天             │
├─────────────────────────────────────────┤
│         ╭─────────╮                      │
│         │   D20   │                      │
│         │  黄体期  │   ← 圆环（点 → 日历） │
│         ╰─────────╯                      │
├─────────────────────────────────────────┤
│ 🎯 排卵预测                              │
│   预计排卵：5/24（后天）  置信度：高 ●●●○○│
│   依据：LH 阳性 + 蛋清状黏液              │
├─────────────────────────────────────────┤
│ 📊 健康一览                              │
│   RHR  62↑+3   HRV  48↓-12%             │
│   睡眠 6h42m   BBT  36.55℃ 🔺            │
├─────────────────────────────────────────┤
│  今天的标签                       [➕]   │
│  💗 爱抚   😊 快乐   ✈️ 旅行             │
├─────────────────────────────────────────┤
│  伴侣的今天 (TA)            [刷新 30s]   │
│  D20·黄体期  💗 爱抚  😊 快乐            │
├─────────────────────────────────────────┤
│  最近日记 / 最近旅行 ...                  │
└─────────────────────────────────────────┘
[🏠][📅][➕][📓][✈️][👥]
```

---

## 7. 关键逻辑

### 7.1 经期 / 排卵预测（多信号融合，策略模式）

**Signal 列表**（按优先级，每个独立可用）：

| Signal | 输入 | 用途 | 置信度 |
|---|---|---|---|
| **LHSignal** | `daily_tags.排卵测试 = 阳性/晕线` | 排卵前 24-36h 实时预警 | 极高 |
| **BBTSignal** | `bbt_readings` 时序 | 排卵后事后确认（三步法） | 高 |
| **MucusSignal** | `daily_tags.分泌物 = 蛋清状` | 接近排卵预警 | 中 |
| **RHRSignal** | `health_metrics.rhr_bpm` 时序 | 黄体期/排卵后辅证 | 中 |
| **HRVSignal** | `health_metrics.hrv_sdnn_ms` 时序 | 同上 + 经期临近 | 中 |
| **CalendarSignal** | `periods` 历次记录 | 兜底基线 | 低-中 |

```python
class Signal(Protocol):
    def evaluate(self, user_id, target_date) -> SignalResult: ...
    # → (predicted_ovulation, confidence_0_1, evidence_text, source)

class CombinedPredictor:
    """优先级合并 — 实时信号 > 事后锁定 > 趋势辅证 > 日历兜底"""
    def predict(self, user_id, target_date):
        # 详细融合规则见 §7.2
```

**BBT 三步法**（标准 FAM）：
- `covering_line = mean(BBT[-6:])`
- 找一天 T1 满足 `T1 > covering + 0.2℃`
- 紧接 T2、T3 也 `> covering`，且至少一天 `> covering + 0.2℃`
- 则**排卵 = T1 前一天**
- 第 3 天 BBT 仍高 = 安全期开始

**RHR/HRV 偏移检测**：
- baseline = `median(metric in 当前周期卵泡期)`
- RHR 抬升 ≥3 bpm 持续 2 天 → 黄体期信号，置信 0.55
- HRV 较 baseline 下降 ≥15% 持续 2 天 → 同上 / 经期临近，置信 0.50

**Sleep 不入预测器**（噪音大），仅作为：
- PMS / 经前不适关联指标
- 自动补全 daily_tag `睡眠差`（深睡 <15% 或 总时长 <6h）

### 7.2 优先级融合规则
```
1. LH 阳性在 36h 内              → "排卵 24-36h 内"，confidence=0.95
2. BBT 三步法已确认               → "排卵已发生于 D X"，confidence=0.85
3. 蛋清状黏液 + 卵泡期晚期 + LH 阴 → "approaching"，confidence=0.6
4. RHR/HRV 双偏移                 → 辅证已排卵 / 黄体期，confidence=0.55
5. 兜底：日历预测                 → 给浮动带（±cycle_std）
```

UI 卡片可展开「查看依据」，列出每个 Signal 的当前贡献。

### 7.3 周期阶段状态机
```
月经期 (D1..period_end)
  → 卵泡期 (排卵前)
  → 易孕窗口 (排卵 ±5 天)
  → 排卵日 (来自 BBT / LH)
  → 黄体期 (排卵后到下次经期)

UI 圆环外圈"信号强度"颜色：
  灰  = 仅日历预测
  橙  = LH 预警中
  红  = 排卵确认
  蓝  = 黄体期锁定
```

### 7.4 文件上传管线
```
client picker → POST /media/upload (multipart)
   ├ MIME 白名单：jpeg / png / webp / heic / pdf
   ├ Magic bytes 校验（防伪扩展名）
   ├ 最大 50 MB
   ├ SHA256 → 同 owner 已存在 → 复用 media_id
   ├ 图像：Pillow 解析 EXIF（datetime, GPS）
   │       生成 400×400 + 1200px 长边预览（WebP）
   │       如果 visibility=shared，剥离 GPS
   ├ PDF：PyMuPDF 提取首页缩略图
   └ 落盘：/data/uploads/{user_id}/{YYYY}/{MM}/{sha256[:2]}/{sha256}.{ext}
```
**孤儿清理**：APScheduler 每晚扫描，删除「7 天内无任何 link 引用」的 media + 物理文件。

### 7.5 CSV / Apple Health 导入
```
POST /me/import (Flo CSV / Apple Health export.zip)
  → 创建 import_jobs row (status=pending)
  → APScheduler 每 60s 扫一次 pending 队列，立即开始处理
    （06:00 的全表扫描是兜底，用于卡死/重试场景）：
     ├ Flo CSV：periods.csv → upsert periods（按 start_date 幂等）
     │           symptoms.csv → 映射 tag_catalog → upsert daily_tags
     ├ Apple Health：解压 export.xml → 解析：
     │    - HKCategoryTypeIdentifierMenstrualFlow → periods
     │    - HKCategoryTypeIdentifierSexualActivity → daily_tags
     │    - HKQuantityTypeIdentifierRestingHeartRate → health_metrics
     │    - HKQuantityTypeIdentifierHeartRateVariabilitySDNN → health_metrics
     │    - HKCategoryTypeIdentifierSleepAnalysis → health_metrics
     │    - HKQuantityTypeIdentifierBodyTemperature → bbt_readings
     └ summary_json: {periods: 47, tags: 1203, health: 580, skipped: 15}
前端 /me/import 轮询 status 显示进度条
```
**幂等**：重复导入同文件不会产生重复行。

### 7.6 双人同步（伪实时）
- 不上 WebSocket / SSE（省内存）
- 「今天」/「日历」用 HTMX 周期轮询：
  ```html
  <div hx-get="/today/partner-card"
       hx-trigger="every 30s [document.visibilityState==='visible']"
       hx-swap="outerHTML">
  ```
- 仅 tab 可见时刷新
- 升级路径：未来需要真实时 → 切 SSE（FastAPI 原生）

### 7.7 PWA Web Push
- 浏览器 Push API + VAPID 公私钥
- 用户在 `/me/settings` 点开启 → SW 注册 subscription → 后端存 `push_subscriptions`
- APScheduler 触发：
  - **经期前 2 天**："姨妈快来了，记得准备 🌸"
  - **排卵期开始**："排卵窗口 5 天"
  - **伴侣记重要事件**（开始经期 / 新日记 / 新旅行）→ 推送另一方
- iOS Safari 16.4+ 支持 PWA push（前提：装到主屏）

---

## 8. 隐私 & 安全

### 8.1 身份认证
- Argon2id 哈希
- 服务端 session 表 + cookie（HttpOnly, Secure, SameSite=Lax），30 天滑动续期
- 登录失败：同账号 5 次 → 锁 15min；同 IP 5min 内 20 次 → 锁 30min
- **无注册接口**，仅 invite token 绑定
- 绑定后 invite_tokens 清空
- 可选 TOTP 2FA（计划 M2）

### 8.2 传输加密
**M1 临时方案**（无域名）：
- 自签证书 + Nginx 443
- 浏览器首次访问需手动信任证书（首屏弹警告）
- HSTS 暂不启用（避免被自签锁死）

**M3 / 有域名后**：
- Let's Encrypt（certbot）自动续签
- 启用 HSTS `max-age=31536000`
- HTTP→HTTPS 301
- Mozilla intermediate cipher suite

### 8.3 数据存储加固
| 项 | 当前 | 加固后 |
|---|---|---|
| MariaDB 监听 | `0.0.0.0:3306` | **仅 `127.0.0.1`**（部署时改 my.cnf） |
| 业务库账号 | - | 独立 `couple@127.0.0.1`，强密码，仅本库权限 |
| 应用进程 | root | 非 root `couple` 用户（systemd User=） |
| `/data/uploads/` | - | `chmod 700`，owner=couple |
| 列加密 | - | **不做**（2 用户 + 物理隔离已够，过度设计） |

### 8.4 文件服务鉴权
- 文件**不让 nginx 直接 serve** — URL 泄漏 = 文件公开
- 所有 `/media/{id}` 走 FastAPI → 验 session → 验可见性 → `StreamingResponse`
- 浏览器/CDN 缓存：返回带 HMAC 短期签名（24h 过期），缓存友好且不绕鉴权

### 8.5 输入/输出防御
| 攻击面 | 防御 |
|---|---|
| XSS | Jinja2 autoescape；用户输入永不 `\|safe`；CSP header |
| SQLi | SQLAlchemy ORM 参数化 |
| CSRF | SameSite=Lax + 状态变更 POST 一次性 CSRF token |
| 文件上传 | MIME + Magic bytes + 50MB + 路径用 SHA256（防穿越） |
| 目录穿越 | 路径全后端生成，从不接受用户输入路径 |
| SSRF | 不存在外部 URL 抓取功能 |

### 8.6 可见性双层强制
- 路由依赖 `require_auth()` + `require_partner_visible(ref_type, ref_id)`
- 可见性检查在 **service 层**（不只路由层）
- 「TA 的今天」聚合只读 `visibility=shared OR owner=self`

### 8.7 备份与恢复
**M1（本地）**：
- APScheduler 03:00：`mysqldump --single-transaction couple_diary | gzip > /data/backups/db/{YYYYMMDD}.sql.gz`
- 03:15：`rsync -a --delete /data/uploads/ /data/backups/uploads-mirror/`
- 保留 30 天，超期自动清
- 备份仅 root 可读

**M3（异地）**：
- rclone 推到外部对象存储（COS / OSS / 个人 NAS），客户端加密
- 月度自动恢复演练 → SHA256 校验

### 8.8 操作面
- SSH 仅 key（已配置）
- 服务器装 fail2ban 监 SSH + Nginx 401
- 应用日志：JSON 结构化 → `/var/log/couple_diary/app.log`，logrotate 14 天
- 禁记密码/token/文件原内容；错误日志 filename 用 SHA256 前缀
- 数据导出 `/me/settings → 导出全部` 一键 ZIP
- 数据销毁：一键删除全部 → 要求重输密码 + 24h 冷静期

---

## 9. 错误处理 & 测试

### 9.1 错误处理
**用户面**：
- HTMX 失败 → 返回错误片段（红框 + 文案），原位替换
- 全页错误 → 自定义 404 / 403 / 500 模板（粉桃风格）
- 表单 → Pydantic schema 校验失败 → HTMX 片段返回到对应字段下

**异常体系**：
```python
class AppError(Exception): http_status, code, message
NotFound       → 404
Forbidden      → 403
ValidationErr  → 422
RateLimited    → 429
FileTooLarge   → 413
StorageError   → 500
```
FastAPI exception_handler 统一捕获 → JSON / HTML 双格式响应。

**日志**：
- 结构化 JSON → `/var/log/couple_diary/app.log`
- 每请求：`request_id, user_id, method, path, status, latency_ms`
- 异常：堆栈写日志，**不发到客户端**
- 不记：密码、session token、文件原内容、医疗数据明细

### 9.2 测试策略
**栈**：`pytest + pytest-asyncio + httpx.AsyncClient + pytest-cov + hypothesis + factory_boy`

**层级**：
| 层 | 覆盖目标 |
|---|---|
| 单元（service 纯函数） | ≥80% |
| 集成（route + DB） | ≥60% |
| E2E（Playwright，可选 M3） | 关键 3 路径 |

**测试数据库**：真 MariaDB `couple_diary_test`，每个测试函数事务回滚，方言一致。

**必须覆盖**：
1. 绑定流程：token 一次性、配对、couple 不能多组
2. 登录：正确 / 错误 / 锁定 / session 过期
3. 可见性矩阵：`data_type × owner × viewer × visibility_setting` 参数化全覆盖
4. 经期预测：Hypothesis 属性测试；已知 BBT 案例必命中
5. 文件上传：dedup、MIME 伪造、超大、路径穿越、EXIF GPS 剥离
6. CSV 导入：幂等性 — 同文件二次导入结果一致
7. 备份恢复：dump → 全清 → restore → SHA 校验

**覆盖率门槛**：整体 ≥70%；`auth/` / `cycle/predictor.py` / `media/` ≥90%。

### 9.3 静态质量
- ruff lint + format
- mypy strict（service / models / schemas 必须；templates 不要求）
- pre-commit hook：`ruff format → ruff check → mypy → pytest -x --ff`

### 9.4 可观测性（轻量）
- `/healthz`：DB ping + 磁盘空间 → 200 / 503
- 慢请求日志（>500ms）
- MariaDB slow query log（>500ms）
- v1 不接 Sentry（隐私 + 减依赖）

### 9.5 迁移与回滚
1. `mysqldump` → `/data/backups/pre-deploy/{ts}.sql.gz`
2. `alembic upgrade head`
3. `systemctl restart couple-diary`
4. `curl /healthz` 检查
5. 失败 → 还原 dump → 重启旧版本 → 告警

---

## 10. 部署 & 运维

### 10.1 服务器目录布局
```
/opt/couple_diary/              # 代码
  .venv/
  .env.production              # chmod 600, owner=couple

/data/                          # 数据卷
  uploads/
  backups/{db, uploads-mirror, pre-deploy}/

/var/log/couple_diary/app.log

/etc/systemd/system/couple-diary.service
/etc/nginx/conf.d/couple-diary.conf
```

### 10.2 系统用户 & 权限
```bash
useradd -r -s /usr/sbin/nologin couple
chown -R couple:couple /opt/couple_diary /data /var/log/couple_diary
chmod 700 /data/uploads /data/backups
chmod 600 /opt/couple_diary/.env.production
```

### 10.3 MariaDB 加固 + 业务库
```ini
# /etc/my.cnf.d/server.cnf
[mysqld]
bind-address = 127.0.0.1
```
```sql
CREATE DATABASE couple_diary      CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE couple_diary_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'couple'@'127.0.0.1' IDENTIFIED BY '<strong-pwd>';
GRANT ALL ON couple_diary.* TO 'couple'@'127.0.0.1';
GRANT ALL ON couple_diary_test.* TO 'couple'@'127.0.0.1';
FLUSH PRIVILEGES;
```

### 10.4 systemd 服务
```ini
[Unit]
Description=Couple Diary App
After=network.target mariadb.service

[Service]
Type=simple
User=couple
Group=couple
WorkingDirectory=/opt/couple_diary
EnvironmentFile=/opt/couple_diary/.env.production
ExecStart=/opt/couple_diary/.venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers
Restart=on-failure
RestartSec=5
MemoryMax=600M
TasksMax=200
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/data /var/log/couple_diary
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### 10.5 Nginx 反代（M1 自签证书版）
```nginx
# 生成自签：
# openssl req -x509 -newkey rsa:4096 -nodes \
#   -keyout /etc/nginx/ssl/couple.key -out /etc/nginx/ssl/couple.crt \
#   -days 365 -subj "/CN=150.158.3.104"
# chmod 600 /etc/nginx/ssl/couple.key

server {
    listen 80;
    server_name 150.158.3.104;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name 150.158.3.104;

    ssl_certificate     /etc/nginx/ssl/couple.crt;
    ssl_certificate_key /etc/nginx/ssl/couple.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 自签证书阶段暂不启用 HSTS（避免被锁）
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: blob:; ..." always;

    client_max_body_size 60M;

    location /static/ {
        alias /opt/couple_diary/app/static/;
        expires 30d;
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```
有域名后切换：装 certbot → `certbot --nginx -d your.domain` → 替换证书路径 → 启用 HSTS。

⚠️ 宝塔面板 8888 端口不动；建议改宝塔密码 + 限制访问 IP。

### 10.6 环境变量 `.env.production`
```bash
APP_ENV=production
SECRET_KEY=<openssl rand -hex 32>
DATABASE_URL=mysql+pymysql://couple:<pwd>@127.0.0.1/couple_diary?charset=utf8mb4
DATABASE_TEST_URL=mysql+pymysql://couple:<pwd>@127.0.0.1/couple_diary_test?charset=utf8mb4
UPLOAD_DIR=/data/uploads
BACKUP_DIR=/data/backups
LOG_DIR=/var/log/couple_diary
SESSION_COOKIE_NAME=cdsid
SESSION_MAX_AGE_DAYS=30
COOKIE_SECURE=true
VAPID_PUBLIC_KEY=<generate via cli>
VAPID_PRIVATE_KEY=<generate via cli>
VAPID_SUBJECT=mailto:you@example.com
```

### 10.7 首次部署（`scripts/bootstrap.sh`）
```
1. useradd couple
2. 建 /data 树
3. dnf install python3.11 nginx openssl
4. git clone /opt/couple_diary
5. python -m venv .venv && pip install -e .
6. 生成自签证书 (CN=150.158.3.104)
7. 加固 MariaDB (bind 127.0.0.1) + 建业务库账号
8. 写 .env.production（随机 SECRET_KEY + VAPID）
9. alembic upgrade head
10. python -m app.cli init-couple --he 你名 --she 伴侣名
11. 安装 systemd unit + nginx conf
12. systemctl enable --now couple-diary && systemctl reload nginx
13. 打印 invite token 链接
```

### 10.8 更新部署（`scripts/deploy.sh`）
```bash
cd /opt/couple_diary
git pull
mysqldump --single-transaction couple_diary | gzip > /data/backups/pre-deploy/$(date +%s).sql.gz
.venv/bin/pip install -e .
.venv/bin/alembic upgrade head
systemctl restart couple-diary
sleep 3
curl -fsSk https://127.0.0.1/healthz || {
    echo "Health check failed, rolling back..."
    # git checkout HEAD~1 && pip install -e . && systemctl restart couple-diary
}
```

### 10.9 后台定时任务（APScheduler 内嵌）
- 每 60s — 扫描 import_jobs(status=pending) 并启动 worker（主入口）
- 03:00 — 数据库备份
- 03:15 — 文件 mirror
- 03:30 — 清理孤儿 media（7 天无引用）
- 06:00 — import_jobs 全表扫描兜底（卡死任务重试）
- 09:00 — 每日推送（经期/排卵提醒）
- 每小时 — 健康指标补采（如启用 manual 录入则跳过）

### 10.10 监控（极简）
- 宝塔面板自带 CPU/磁盘/内存告警
- 外部：每分钟 cron `curl --fail -k https://150.158.3.104/healthz`，失败发邮件 / Server酱
- 备份监控：备份完成写 `/var/log/couple_diary/backup-status`；监控脚本 25h 无新行 → 告警

### 10.11 灾难恢复 Runbook
`docs/runbook.md` 记录：
- 服务挂了排查步骤
- 数据库挂了排查
- 磁盘满处理（vacuum 备份 → 清旧日志）
- 还原到某天：`gunzip < /data/backups/db/YYYYMMDD.sql.gz | mysql couple_diary`
- 还原单文件：从 `/data/backups/uploads-mirror/...` 找

---

## 11. 里程碑分解

设计文档**完整覆盖**三个里程碑，**实施时分阶段交付**。每个里程碑结束都能上线使用。

### M1 — MVP（~2 周）
**目标**：你和伴侣每天都能用上的最小可用版本。

**包含**：
- §1-4：项目目标、技术栈、架构、模块骨架
- §5.1-5.2：核心数据表（users / couples / sessions / cycle / daily / diary / media / settings / bbt / health_metrics 主表 + 必要 link 表）
- §6.1-6.2：导航 + 路由表中的 `/`, `/login`, `/bind`, `/calendar`, `/cycle/log`, `/log/today`, `/log/{date}`, `/me`, `/me/settings`, `/healthz`, `/media/{id}`
- §6.4-6.5：绑定流程 + 「今天」页面
- §7.1：经期预测 — 仅 **CalendarSignal + LHSignal + BBTSignal**（MucusSignal 写好不接入，RHR/HRV 留到 M3）
- §7.4：文件上传管线（图像，PDF 留到 M2）
- §8.1-8.6：认证、传输（自签）、存储加固、文件鉴权、输入防御、可见性
- §8.7 M1 部分：本地备份
- §9.1-9.5：错误处理 + 测试基线（pytest 框架 + 关键路径覆盖）
- §10：完整部署 + bootstrap.sh + deploy.sh + systemd + nginx 自签

### M2 — 内容扩展（~1.5 周）
**包含**：
- §5：完整 daily_log 标签 catalog（全部 ~80 个 tag_key）
- §6.2 路由：`/diary/*`（文字 + 图片 + visibility）、`/trip/*`（相册）
- §6.3：抽屉式 sheet 完整体验
- §7.4：PDF 上传支持（医疗报告）
- §7.6：双人同步轮询
- §7.7：PWA Web Push（基础 — 经期提醒）
- 设置页可见性完整可调

### M3 — 智能与导入（~1.5 周）
**包含**：
- §7.1：MucusSignal + RHRSignal + HRVSignal + CombinedPredictor 完整融合
- §7.3：周期阶段状态机 + 信号强度 UI
- §7.5：Apple Health + Flo CSV 完整导入
- §6.2：`/me/import`、`/charts/*`、`/bbt/log` 健康图表页
- §8.7 M3：异地备份（rclone）
- §8.2：有域名后切 Let's Encrypt + HSTS（可与 M3 解耦执行）
- 高级：BBT 双相图、健康指标叠加图、PWA push 全套触发

---

## 12. 开放问题（实施前确认）

无强阻塞 — 以下都有合理默认，部署时再具体填：
- VAPID 密钥用 `python -m app.cli generate-vapid` 自动生成
- 自签证书 CN 默认 `150.158.3.104`，有域名后替换
- 备份用 mysqldump（已有 MariaDB 工具链）
- 时区：服务器 + 应用统一 `Asia/Shanghai`
- 用户名 / 显示名 / 头像在 `init-couple` 时传参，绑定页可改

---

## 附录 A：依赖清单（草案）

```toml
[project]
name = "couple-diary"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "jinja2>=3.1",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "pymysql>=1.1",
    "pydantic>=2.8",
    "pydantic-settings>=2.5",
    "python-multipart>=0.0.9",
    "argon2-cffi>=23",
    "itsdangerous>=2.2",
    "pillow>=10.4",
    "pymupdf>=1.24",
    "apscheduler>=3.10",
    "pywebpush>=2.0",
    "httpx>=0.27",
    "slowapi>=0.1.9",
    "python-dateutil>=2.9",
    "lxml>=5.3",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5",
    "hypothesis>=6",
    "factory-boy>=3.3",
    "ruff>=0.6",
    "mypy>=1.11",
    "types-python-dateutil",
]
```

---

**End of Spec.**
