# 安装配置指南

预计 30–60 分钟（含手环）。Windows 关机期间：Telegram 消息在服务器排队、手环数据在手机 Syncthing 里排队，电脑上线后自动补收，**数据不丢**。

## 前提

- 电脑：Windows + Python 3.7+（`python --version` 能出版本号）
- 网络：国内环境需要能访问 Telegram 的代理（Clash 系列，记下本地代理端口，如 `7897`）
- 手机：Android（手环全自动采集需 Android；iPhone 也可作为 Telegram 记录入口）

## 第一步：创建 Telegram bot（5分钟）

1. Telegram 找 **@BotFather** → 发 `/newbot`
2. 名字随意（如 `生活记录`）
3. username **必须以 `bot` 结尾**（如 `my_life_log_bot`），否则报"无效"——这是最常见的坑
4. 成功后 BotFather 消息里 `Use this token to access the HTTP API:` 后面的 `数字:字母` 就是 token

## 第二步：配置并启动桥（5分钟）

1. 把 `config.example.json` 复制为 `scripts\config.json`
2. 填入 `bot_token` 和 `proxy`（本地代理地址；无代理环境可删掉 proxy 字段）
3. 双击 `scripts\start_bridge.bat`（窗口保持开着，可最小化）
4. 手机给 bot 发 `/start`，收到"生活记录桥已就绪"即打通
5. 把日志里显示的 `chat_id` 数字填回 config.json（防陌生人乱写），重启 bat
6. 开机自启（可选）：Win+R 输入 `shell:startup`，把 start_bridge.bat 的快捷方式放进去

## 第三步：手环全自动采集（15分钟，可选）

1. Android 装 [Gadgetbridge](https://codeberg.org/Freeyourgadget/Gadgetbridge)（F-Droid）
   - 手环同一时间只能连一个 App：配对前停用官方"小米运动/Zepp Life"
2. 手环曾绑过官方账号的，需要**认证密钥**才能配对（见 README"手环认证密钥"一节）
   - 密钥填入时加 `0x` 前缀；**不要**从官方 App 解绑（会使密钥失效）
3. Gadgetbridge 设置里开启**自动导出**：间隔每天，目录选一个固定文件夹
4. 手机和电脑都装 Syncthing（电脑端绿色版放 `tools\`，双击根目录 `start_syncthing.bat`）
   - 两边互扫设备二维码配对
   - 共享文件夹：手机端指向自动导出目录，电脑端指向 `inbox\band\`
5. 之后手环数据每天自动出现在电脑上

嫌折腾的替代方案：继续用官方 App，每周手动导出或截图发给 bot（半自动）。

## 第四步：账单导入（每月1次，30秒）

- 支付宝：我的 → 账单 → 右上角··· → 开具交易流水证明 → 用于个人对账 → 邮箱收 CSV
- 微信：我 → 服务 → 钱包 → 账单 → 常见问题 → 下载账单 → 用于个人对账
- 收到 CSV 后在手机上直接转发给 bot

## 第五步：AI 自动化（10分钟）

本项目设计为与 AI 编程助手（ZCode / Claude Code 等支持定时任务者）协作：

- **解析规则**：`docs\parse-rules.md`（识别、格式、分类关键词、日报模板），AI 按此处理 `inbox\` 并追加 `data\`
- **每晚定时任务**：解析当天消息 → 更新 `dashboard\index.html` → 日报经 bot 发回手机
- **随问随答**：数据都在本地 CSV/JSONL，AI 可直接回答"这个月外卖花了多少"之类问题

## 常见问题

- **BotFather 说 username 无效**：必须以 `bot` 结尾，且全网唯一
- **桥收不到消息**：检查代理是否可用（`curl -x http://127.0.0.1:7897 https://api.telegram.org` 应有响应）
- **Gadgetbridge 配对手环失败**：密钥问题见 README；密钥失效多因解绑或恢复出厂（会换 MAC）
- **Flyme 等国产系统 adb 装应用被拦**：开发者选项里打开"USB 安装"
- **Syncthing 连接走中继**：一方代理软件拦截了局域网流量，属正常，小文件无感
