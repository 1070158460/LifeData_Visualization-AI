# Life-OS · 个人生活数据系统

把饮食、运动、睡眠、财务、体重、心情等生活数据统一落到**本地文件夹**，用 Telegram 随手记录，由 AI 自动解析入库、生成可视化看板和每晚日报。

> 数据 100% 留在本机（`E:\life-os`），不上云、不依赖任何第三方托管。AI 只在你要求分析时接触单条内容。

## 架构

```
手机（Telegram，双机登录皆可）
  │  消息 / 餐食照片 / 账单CSV / 体重 / 心情
  │  （电脑关机时消息在 Telegram 服务器排队，开机补收，不丢）
  ▼
tg-bridge（Windows 后台小程序，零依赖 Python）
  ▼
inbox\telegram\日期\（原始消息+文件落地）
  ▼
AI 解析（按 docs\parse-rules.md，规则可自定义）
  ├─ 追加写入 data\（生活数据库，CSV/JSONL，只追加）
  ├─ 重新生成 dashboard\index.html 可视化看板
  └─ 每晚 22:30 定时日报，经 bot 发回手机

小米手环 → 安卓 Gadgetbridge 自动导出
        → Syncthing 双向同步 → inbox\band\ → 同样进入 AI 解析
```

核心思想：**手机是入口，电脑是处理器**。日常只需要在手机 Telegram 里发消息，其余全自动。

## 功能

- **饮食**：拍照或一句话（`午饭 牛肉面一碗`）→ AI 识别估算热量/蛋白质
- **财务**：支付宝/微信账单 CSV 直接转发给 bot → 自动分类记账
- **运动/睡眠/心率**：手环数据每日自动同步（无需手动操作）
- **体重/心情**：一句话记录（`体重72.5` / `今天有点丧`）
- **每晚日报**：睡眠、步数、热量、支出汇总 + 趋势观察，推送到手机
- **可视化看板**：`dashboard\index.html`，本地浏览器打开即看

## 目录结构

```
life-os/
├── README.md               本文件
├── LICENSE                 MIT
├── .gitignore              排除隐私与运行时数据
├── config.example.json     桥配置模板（复制为 scripts/config.json 使用）
├── start_syncthing.bat     一键启动电脑端 Syncthing
├── docs/
│   ├── SETUP.md            安装配置指南（新手从这里开始）
│   ├── USAGE.md            日常使用手册（装好后看这个）
│   ├── parse-rules.md      AI 解析 inbox → data 的规则（换AI就交接这份文件）
│   └── data-example/       data 文件格式示例
├── scripts/
│   ├── tg_bridge.py        Telegram 桥（核心，零第三方依赖）
│   └── start_bridge.bat    一键启动桥
├── dashboard/
│   └── index.html          可视化看板（内置演示数据，部署后由 AI 按真实数据重绘）
└── data/                   生活数据库（运行时目录，你的真实数据，已被 .gitignore 排除）
    └── inbox/              原始落地处（同上，不入库）
```

`tools/`（adb、Syncthing 便携版、token_extractor 等）为本地第三方工具，不入库，获取方式见 SETUP.md。

## 快速开始

安装见 **[docs/SETUP.md](docs/SETUP.md)**，装好后的日常用法见 **[docs/USAGE.md](docs/USAGE.md)**。最短路径：

1. **网络**：国内需要能访问 Telegram 的代理（Clash 系列均可），记下本地代理端口
2. **建 bot**：Telegram 找 @BotFather → `/newbot` → username 必须以 `bot` 结尾 → 拿到 token
3. **配桥**：`config.example.json` 复制为 `scripts/config.json`，填 token 和代理 → 双击 `scripts\start_bridge.bat` → 手机给 bot 发 `/start` → 看到"生活记录桥已就绪"即通
4. **手环**（可选）：手机装 [Gadgetbridge](https://codeberg.org/Freeyourgadget/Gadgetbridge)（F-Droid）→ 按下方"手环认证密钥"拿到 key → 配对 → 设置自动导出到同步目录
5. **同步**：手机装 Syncthing-Fork，与电脑配对，共享 Gadgetbridge 导出目录 ↔ `inbox\band\`
6. **自动化**：让 AI 助手（ZCode / Claude Code 等支持定时任务的 Agent）按 `docs/parse-rules.md` 每晚解析并出日报

## 手环认证密钥（Mi Band 4/5/6 必看）

手环绑过官方 App（小米运动/Zepp Life）后，Gadgetbridge 配对需要认证密钥：

- **方法一（官方推荐）**：[Xiaomi-cloud-tokens-extractor](https://github.com/PiotrMachowski/xiaomi-cloud-tokens-extractor) 登录小米账号提取
- **方法二**：手机装 [HuaFetch](https://github.com/Keddnyo/HuaFetch) 登录小米账号获取
- 密钥输入 Gadgetbridge 时**加 `0x` 前缀**
- **不要**从官方 App 解绑（会使密钥失效）；不用官方 App 时直接停用它即可
- 更详细说明见 [Gadgetbridge 官方文档](https://gadgetbridge.org/basics/pairing/huami-xiaomi-server)

## 数据格式

| 文件 | 格式 | 关键列 |
|---|---|---|
| `sleep.csv` | CSV | date, bedtime, wakeup, duration_h, deep_h, light_h, rem_h, score |
| `steps.csv` | CSV | date, steps, distance_km, calories |
| `weight.csv` | CSV | date, weight_kg, body_fat_pct |
| `mood.csv` | CSV | date, mood_1to5, energy_1to5, note |
| `diet.jsonl` | JSONL | date, time, meal, items[], kcal, protein_g, source |
| `transactions.csv` | CSV | date, amount, category, merchant, platform |

所有文件**只追加**，历史不可变——这让数据天然可审计，也方便任何工具二次分析。

## 隐私

- 所有数据只存本机这个文件夹，`config.json`（含 bot token）与 `inbox/`、`logs/` 已被 `.gitignore` 排除，**不会**进入 git 仓库
- 账单 CSV、照片等敏感原件在解析后移入 `inbox\processed\`，不要把整个文件夹上传到网盘
- 如需公开自己的部署，请只公开代码与样例数据

## 致谢

- [Gadgetbridge](https://codeberg.org/Freeyourgadget/Gadgetbridge)（GPL-3.0）— 开源手环 companion
- [Syncthing](https://syncthing.net)（MPL-2.0）— 开源文件同步
- [Xiaomi-cloud-tokens-extractor](https://github.com/piotrmachowski/xiaomi-cloud-tokens-extractor) — 密钥提取

## License

[MIT](LICENSE)
