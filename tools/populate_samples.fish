#!/usr/bin/env fish

# 远程 KV 服务地址
set BASE_URL "https://mem-kv.bitsflow.org/dashboard"

# 样本数据 1：新闻与天气
set INFO1 "# 今日要闻
## 全球资讯
- 空间站补给任务圆满完成
- 新技术突破提升电池效率
- 国际气候峰会今日开幕

## 当地天气
气温: 22°C / 15°C
天气: 多云转晴
风力: 东北风 2 级

## 提醒事项
下午 3 点 团队周会
记得给阳光房通风"

# 样本数据 2：个人看板与格言
set INFO2 "# 个人看板
## 项目进度
- 墨水屏固件: 90% (优化中)
- 自动化录音机: 已上线
- 知识库维护: 进行中

## 每日格言
\"Stay hungry, stay foolish.\"
\"The best way to predict the 
future is to create it.\"

## 加密货币
BTC: \$51,234.56 (-1.2%)
ETH: \$2,987.12 (+0.5%)"

echo "正在推送样本数据到 info1..."
curl -X POST -H "Content-Type: text/plain" -d "$INFO1" "$BASE_URL/info1"

echo "正在推送样本数据到 info2..."
curl -X POST -H "Content-Type: text/plain" -d "$INFO2" "$BASE_URL/info2"

echo "推送完成！请刷新墨水屏查看效果。"
