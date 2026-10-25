# 生活数据解析规则（ZCode 执行）

每次定时任务或用户要求时，读取 `E:\life-os\inbox\telegram\` 和 `E:\life-os\inbox\band\` 里**未处理**的内容，按以下规则解析后**追加**到 `E:\life-os\data\`。历史行永不修改，只追加。已处理的消息文件移入 `inbox\processed\`，防止重复入库。

## 识别与写入规则

1. **餐食照片**（inbox 里的 jpg + 说明文字）→ 识别食物、估算热量和蛋白质 → 追加 `diet.jsonl`
   格式：`{"date":"YYYY-MM-DD","time":"HH:MM","meal":"早餐|午餐|晚餐|加餐","items":["…"],"kcal":0,"protein_g":0,"source":"photo"}`
2. **文本提到吃饭**（如"午饭 一碗牛肉面"）→ 同上，`source` 为 `"text"`
3. **体重**（如"体重72.5"）→ 追加 `weight.csv`：`date,weight_kg,body_fat_pct`（体脂率没说就留空）
4. **心情/状态**（如"今天有点丧"）→ 追加 `mood.csv`：`date,mood_1to5,energy_1to5,note`
5. **账单文件**（支付宝 `alipay_record*.csv` / 微信支付账单CSV）→ 逐笔解析分类后追加 `transactions.csv`：`date,amount,category,merchant,platform`
6. **手环数据文件**（Gadgetbridge 自动导出到 `inbox\band\`）→ 解析后追加 `sleep.csv` 和 `steps.csv`
7. 与生活数据无关的消息（/start、闲聊、乱码）不写库

## 账单分类关键词

- 餐饮：外卖|食堂|餐厅|饭|面|烧烤|火锅|海底捞|肯德基
- 奶茶咖啡：喜茶|瑞幸|星巴克|茶百道|Manner|蜜雪|咖啡|奶茶
- 交通：地铁|公交|滴滴|单车|打车|加油
- 购物：京东|淘宝|天猫|拼多多|Apple
- 娱乐：会员|游戏|电影|Steam|视频|音乐
- 日用：超市|盒马|便利店|屈臣氏
- 通讯：话费|流量|运营商
- 医疗：药|医院|诊所
- 匹配不到 → 其他

## 每日汇总（定时任务）

每晚 22:30：

1. 解析当天 inbox 新内容入 `data\`
2. 用最新数据重新生成 `E:\life-os\dashboard\index.html`
3. 生成日报并通过 bot 发回用户 Telegram（token 读 `scripts\config.json`，chat_id 用 config 里的 `allowed_chat_id`）：
   - 昨夜睡眠时长与得分、今日步数（若有）
   - 今日饮食热量合计 vs 目标（默认 2000 kcal）
   - 今日支出笔数与合计
   - 一句观察（趋势或异常，如"本周第三次睡眠不足6小时"）

发送方式：`curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" -d chat_id=<ID> -d text="<日报>"`

## 纪律

- 所有写入**只追加**；日期一律 `YYYY-MM-DD`，时间 24 小时制
- CSV 新行必须与表头列数一致；JSONL 一行一个 JSON 对象；UTF-8 编码
- 看不准的内容（如照片模糊）在 JSON 里加 `"estimate": true`，不要编造精度
