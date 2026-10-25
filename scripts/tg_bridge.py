#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tg-bridge：Telegram → life-os 桥。

在 Windows 上后台运行，长轮询收取 Telegram bot 消息（文本/照片/文件），
原样落地到 E:\life-os\inbox\telegram\日期\，供 ZCode 解析入库。
电脑关机期间消息由 Telegram 服务器缓存，启动后自动补收。

零第三方依赖，仅需 Python 3.7+。
用法：先在 config.json 填入 bot_token，然后 python tg_bridge.py
"""
import json
import os
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
INBOX = os.path.join(ROOT, "inbox", "telegram")
LOGS = os.path.join(ROOT, "logs")
CONFIG = os.path.join(BASE, "config.json")

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

    text = (msg.get("text") or "").strip()
    if text in ("/start", "/help", "start", "帮助"):
        try:
            api(token, "sendMessage", {
                "chat_id": chat_id,
                "text": "生活记录桥已就绪。直接发：\n"
                        "· 餐食照片或「午饭 牛肉面一碗」→ 饮食\n"
                        "· 「体重72.5」→ 体重\n"
                        "· 支付宝/微信账单CSV → 记账\n"
                        "· 「今天有点丧」→ 心情\n"
                        "处理结果每晚汇总发回这里。"})
        except Exception:
            pass
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
