#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tg-bridge：Telegram → life-os 桥。

在 Windows 上后台运行，长轮询收取 Telegram bot 消息（文本/照片/文件），
原样落地到 E:\life-os\inbox\telegram\日期\，供 ZCode 解析入库。
电脑关机期间消息由 Telegram 服务器缓存，启动后自动补收。

零第三方依赖，仅需 Python 3.7+。
用法：先在 config.json 填入 bot_token，然后 python tg_bridge.py
"""
import csv
import datetime
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
INBOX = os.path.join(ROOT, "inbox", "telegram")
LOGS = os.path.join(ROOT, "logs")
DATA = os.path.join(ROOT, "data")
CONFIG = os.path.join(BASE, "config.json")
BAND_DB = os.path.join(ROOT, "inbox", "band", "Gadgetbridge.db")

HELP_TEXT = (
    "生活记录桥已就绪 🐟\n\n"
    "📌 记录（直接发消息即可）：\n"
    "· 餐食照片或「午饭 牛肉面一碗」→ 饮食\n"
    "· 「体重72.5」→ 体重\n"
    "· 支付宝/微信账单CSV文件 → 记账\n"
    "· 「今天有点丧」→ 心情\n\n"
    "🔧 指令：\n"
    "/today — 今日数据一览\n"
    "/week — 最近7天趋势\n"
    "/report — 昨日日报（立即生成）\n"
    "/status — 系统状态\n"
    "/help — 本帮助"
)

CFG = {}
OPENER = urllib.request.build_opener()


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        os.makedirs(LOGS, exist_ok=True)
        with open(os.path.join(LOGS, "tg_bridge.log"), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def api(token, method, data=None, timeout=70):
    url = "https://api.telegram.org/bot%s/%s" % (token, method)
    if data is None:
        req = urllib.request.Request(url)
    else:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def download(token, file_id, dest):
    r = api(token, "getFile", {"file_id": file_id})
    path = r["result"]["file_path"]
    url = "https://api.telegram.org/file/bot%s/%s" % (token, path)
    with OPENER.open(url, timeout=120) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def send_text(token, chat_id, text):
    try:
        api(token, "sendMessage", {"chat_id": chat_id, "text": text})
    except Exception as e:
        log("sendMessage 失败: %s" % e)


def csv_rows(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def diet_rows():
    p = os.path.join(DATA, "diet.jsonl")
    out = []
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
    return out


def band_latest():
    if not os.path.exists(BAND_DB):
        return "无数据库文件"
    try:
        tmp = os.path.join(tempfile.gettempdir(), "tg_bridge_gb.db")
        shutil.copyfile(BAND_DB, tmp)
        con = sqlite3.connect(tmp)
        row = con.execute("SELECT MAX(TIMESTAMP) FROM MI_BAND_ACTIVITY_SAMPLE").fetchone()
        con.close()
        os.remove(tmp)
        if not row or not row[0]:
            return "无样本"
        return time.strftime("%m-%d %H:%M", time.localtime(row[0]))
    except Exception as e:
        return "读取失败(%s)" % e


def day_kcal(rows, day):
    return sum(float(r.get("kcal") or 0) for r in rows if r.get("date") == day)


def day_expense(rows, day):
    n = 0
    total = 0.0
    for r in rows:
        if r.get("date") == day:
            n += 1
            try:
                total += float(r.get("amount") or 0)
            except ValueError:
                pass
    return n, total


def steps_row(day):
    for r in csv_rows("steps.csv"):
        if r.get("date") == day:
            return r
    return None


def today_text():
    day = time.strftime("%Y-%m-%d")
    lines = ["📊 今日一览 %s" % day]
    s = steps_row(day)
    lines.append("🚶 步数：%s" % (s["steps"] + " 步" if s and (s.get("steps") or "").strip() else "暂无"))
    sl = csv_rows("sleep.csv")
    if sl and (sl[-1].get("duration_h") or "").strip():
        lines.append("💤 最近一晚（%s）：%s 小时" % (sl[-1].get("date", "?"), sl[-1]["duration_h"]))
    else:
        lines.append("💤 睡眠：暂无数据")
    diet = [r for r in diet_rows() if r.get("date") == day]
    if diet:
        lines.append("🍽 饮食：%d 笔 / %s 千卡" % (len(diet), "%.0f" % day_kcal(diet, day)))
    else:
        lines.append("🍽 饮食：今日无记录")
    n, total = day_expense(csv_rows("transactions.csv"), day)
    if n:
        lines.append("💸 支出：%d 笔 / %.2f 元" % (n, total))
    else:
        lines.append("💸 支出：今日无记录")
    w = csv_rows("weight.csv")
    if w and w[-1].get("date") == day:
        lines.append("⚖️ 体重：%s kg" % w[-1].get("weight_kg"))
    return "\n".join(lines)


def week_text():
    lines = ["📈 最近7天趋势"]
    steps_rows = {r.get("date"): r for r in csv_rows("steps.csv")}
    sleep_rows = {r.get("date"): r for r in csv_rows("sleep.csv")}
    diet = diet_rows()
    tx = csv_rows("transactions.csv")
    days_steps = days_sleep = days_kcal = 0
    tot_steps = kcal_sum = sleep_sum = 0.0
    exp_n = 0
    exp_sum = 0.0
    for i in range(7):
        d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        s = steps_rows.get(d)
        if s and (s.get("steps") or "").strip():
            tot_steps += int(float(s["steps"]))
            days_steps += 1
        k = day_kcal(diet, d)
        if k > 0:
            kcal_sum += k
            days_kcal += 1
        n, t = day_expense(tx, d)
        exp_n += n
        exp_sum += t
        r = sleep_rows.get(d)
        if r and (r.get("duration_h") or "").strip():
            try:
                sleep_sum += float(r["duration_h"])
                days_sleep += 1
            except ValueError:
                pass
    if days_steps:
        lines.append("🚶 步数：%d 天有记录，日均 %.0f 步" % (days_steps, tot_steps / days_steps))
    else:
        lines.append("🚶 步数：无记录")
    lines.append("💤 睡眠：%s" % ("平均 %.1f 小时/晚（%d 晚）" % (sleep_sum / days_sleep, days_sleep) if days_sleep else "无记录"))
    lines.append("🍽 饮食：%s" % ("平均 %.0f 千卡/天" % (kcal_sum / days_kcal) if days_kcal else "无记录"))
    lines.append("💸 支出：%d 笔 / %.2f 元" % (exp_n, exp_sum) if exp_n else "💸 支出：无记录")
    if days_sleep and sleep_sum / days_sleep < 6:
        lines.append("⚠️ 平均睡眠不足6小时，今晚早点睡")
    elif days_steps and tot_steps / days_steps < 4000:
        lines.append("⚠️ 日均步数偏低，多动一动")
    else:
        lines.append("整体节奏不错，继续保持 ✊")
    return "\n".join(lines)


def report_text():
    y = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    lines = ["🌅 %s 日报" % y]
    s = steps_row(y)
    if s and (s.get("steps") or "").strip():
        lines.append("🚶 步数：%s 步 / %s 公里 / %s 千卡" % (s.get("steps"), s.get("distance_km") or "?", s.get("calories") or "?"))
    else:
        lines.append("🚶 步数：无记录")
    sl = [r for r in csv_rows("sleep.csv") if r.get("date") == y]
    if sl:
        r = sl[-1]
        lines.append("💤 睡眠：%s 小时（深 %s / 浅 %s / REM %s）" % (
            r.get("duration_h") or "?", r.get("deep_h") or "?",
            r.get("light_h") or "?", r.get("rem_h") or "?"))
    else:
        lines.append("💤 睡眠：无数据")
    diet = [r for r in diet_rows() if r.get("date") == y]
    if diet:
        lines.append("🍽 饮食：%d 笔 / %.0f 千卡" % (len(diet), day_kcal(diet, y)))
    else:
        lines.append("🍽 饮食：无记录")
    n, total = day_expense(csv_rows("transactions.csv"), y)
    if n:
        lines.append("💸 支出：%d 笔 / %.2f 元" % (n, total))
    else:
        lines.append("💸 支出：无记录")
    return "\n".join(lines)


def status_text():
    lines = ["🩺 系统状态 %s" % time.strftime("%Y-%m-%d %H:%M")]
    counts = [
        ("steps.csv", len(csv_rows("steps.csv"))),
        ("sleep.csv", len(csv_rows("sleep.csv"))),
        ("transactions.csv", len(csv_rows("transactions.csv"))),
        ("weight.csv", len(csv_rows("weight.csv"))),
        ("mood.csv", len(csv_rows("mood.csv"))),
        ("diet.jsonl", len(diet_rows())),
    ]
    for name, c in counts:
        lines.append("· %s：%d 条" % (name, c))
    lines.append("· 手环最新样本：%s" % band_latest())
    n = 0
    if os.path.isdir(INBOX):
        for d in os.listdir(INBOX):
            p = os.path.join(INBOX, d)
            if os.path.isdir(p):
                n += len([f for f in os.listdir(p) if f.endswith(".json")])
    lines.append("· 收件箱待处理：%d 条" % n)
    return "\n".join(lines)


def handle_command(token, chat_id, text):
    cmd = text.split()[0].split("@")[0].lower()
    if cmd in ("/start", "/help", "start", "帮助"):
        send_text(token, chat_id, HELP_TEXT)
    elif cmd == "/today":
        send_text(token, chat_id, today_text())
    elif cmd == "/week":
        send_text(token, chat_id, week_text())
    elif cmd == "/report":
        send_text(token, chat_id, report_text())
    elif cmd == "/status":
        send_text(token, chat_id, status_text())
    else:
        send_text(token, chat_id, "没有这个指令，发 /help 查看可用指令")


def save(update, token):
    msg = update.get("message")
    if not msg:
        return
    chat_id = msg["chat"]["id"]
    allowed = CFG.get("allowed_chat_id")
    if allowed and chat_id != allowed:
        log("跳过陌生 chat %s（建议核对 allowed_chat_id）" % chat_id)
        return
    if allowed is None:
        log("提示：把你的 chat_id=%s 填入 config.json 的 allowed_chat_id 可屏蔽陌生人" % chat_id)

    text = (msg.get("text") or "").strip()
    if text.startswith("/") or text in ("帮助", "start"):
        handle_command(token, chat_id, text)
        log("指令 %s 已响应（不落地）" % text.split()[0])
        return

    day = time.strftime("%Y-%m-%d")
    folder = os.path.join(INBOX, day)
    os.makedirs(folder, exist_ok=True)
    ts = msg.get("date", int(time.time()))
    rec = {
        "update_id": update["update_id"],
        "chat_id": chat_id,
        "from": (msg.get("from") or {}).get("first_name", ""),
        "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
        "text": msg.get("text"),
    }
    has_file = False
    if "photo" in msg:
        ph = msg["photo"][-1]
        fname = "%d_%s.jpg" % (ts, ph["file_unique_id"])
        download(token, ph["file_id"], os.path.join(folder, fname))
        rec["photo"] = fname
        has_file = True
    if "document" in msg:
        doc = msg["document"]
        fname = "%d_%s" % (ts, doc.get("file_name", "file"))
        fname = fname.replace("/", "_").replace("\\", "_")
        download(token, doc["file_id"], os.path.join(folder, fname))
        rec["document"] = fname
        has_file = True

    n = update["update_id"]
    with open(os.path.join(folder, "%d.json" % n), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)

    log("已保存 update %d%s" % (n, "（含文件）" if has_file else ""))


def main():
    global CFG, OPENER
    if not os.path.exists(CONFIG):
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump({"bot_token": "粘贴BotFather给的token", "allowed_chat_id": None},
                      f, ensure_ascii=False, indent=2)
        print("已生成 %s，请填入 bot_token 后重新运行" % CONFIG)
        sys.exit(1)
    with open(CONFIG, encoding="utf-8") as f:
        CFG = json.load(f)
    token = CFG.get("bot_token", "")
    if "粘贴" in token or ":" not in token:
        print("请先在 %s 里填入有效的 bot_token（找 @BotFather /newbot 创建）" % CONFIG)
        sys.exit(1)

    proxy = CFG.get("proxy")
    if proxy:
        OPENER = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
        log("使用代理 %s" % proxy)

    log("tg-bridge 启动，开始轮询（关机期间的消息会自动补收；Ctrl+C 退出）")
    try:
        api(token, "deleteWebhook", {})
    except Exception:
        pass
    offset = None
    while True:
        try:
            params = {"timeout": 50, "allowed_updates": ["message"]}
            if offset is not None:
                params["offset"] = offset
            r = api(token, "getUpdates", params, timeout=70)
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                save(u, token)
        except KeyboardInterrupt:
            log("退出")
            break
        except Exception as e:
            log("error: %s" % e)
            time.sleep(5)


if __name__ == "__main__":
    main()
