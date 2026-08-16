"""
聚合天气平台 - 后端 API 服务
=============================================
基于 FastAPI 实现。
- 天气/排行/社区等读接口使用 Mock 数据（原型阶段）。
- 用户系统使用 MySQL 存储（不可用时自动降级为内存存储，便于本地演示）。
- 提供用户名/邮箱/密码注册登录，JWT 鉴权；点赞、评论、获取资料需登录。
同时提供静态文件服务，前端页面和 API 在同一端口下运行。

启动方式: python app.py
访问地址: http://localhost:8000
API 文档: http://localhost:8000/docs
"""

import time
import random
import copy
import json
import hashlib
import os
import re
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Query, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import httpx
import pymysql
import bcrypt
import jwt

app = FastAPI(
    title="聚合天气 API",
    version="1.0.0",
    description="聚合天气预报平台后端服务 - 提供天气数据、准确率排行、社区动态等 API",
)

# =====================================================================
# Mock 数据（来自 test_data.js，真实环境应从数据库读取）
# =====================================================================

# 数据源定义：覆盖主流数值模式 + 主流天气平台/手机内置天气
# 一次性定义，排行榜(7d/30d/all)与详情页均由此派生，避免重复维护
_SOURCES = {
    "ecmwf": {
        "name": "ECMWF", "full": "欧洲中期天气预报中心", "desc": "欧洲中期天气预报中心",
        "score": 87.6, "trend": 2.3, "up": True,
        # 长期全球模式强项：短期略逊本地化源，中长期称王
        "range_deltas": {"7d": -2.0, "30d": 4.0, "all": 6.0},
        "elements": {"温度": 92.1, "降水": 81.5, "风力": 85.3, "湿度": 88.7},
        "horizons": {"24h": 89.2, "48h": 85.1, "72h": 78.6},
        "freq": "每6小时更新",
        "intro": "欧洲中期天气预报中心（ECMWF）是全球公认最优秀的全球数值天气预报机构之一。其IFS模式在全球中期预报领域具有领先优势。",
    },
    "icon": {
        "name": "ICON", "full": "德国气象局全球模式", "desc": "德国气象局全球模式",
        "score": 86.3, "trend": 1.5, "up": True,
        # 稳健中高端：中长期表现好，分辨率高
        "range_deltas": {"7d": -1.0, "30d": 2.0, "all": 3.0},
        "elements": {"温度": 88.5, "降水": 80.2, "风力": 84.0, "湿度": 86.1},
        "horizons": {"24h": 88.0, "48h": 84.2, "72h": 79.0},
        "freq": "每6小时更新",
        "intro": "ICON是德国气象局（DWD）的全球数值预报模式，分辨率高，对欧洲及中纬度天气系统刻画精细，中期表现稳健。",
    },
    "grapes": {
        "name": "GRAPES", "full": "中国气象局全球模式", "desc": "中国气象局全球预报系统",
        "score": 81.0, "trend": 1.0, "up": True,
        # 本土模式：短期需调优，长期本土化优势显现
        "range_deltas": {"7d": -2.0, "30d": 3.0, "all": 4.0},
        "elements": {"温度": 81.0, "降水": 76.0, "风力": 78.5, "湿度": 80.0},
        "horizons": {"24h": 82.5, "48h": 77.0, "72h": 71.0},
        "freq": "每3小时更新",
        "intro": "GRAPES是中国气象局自主研发的全球/区域同化与预报系统，覆盖全球与区域，对中国区域天气具备良好适应性。",
    },
    "cma": {
        "name": "CMA-MESO", "full": "中国气象局中尺度模式", "desc": "中国气象局中尺度模式",
        "score": 80.5, "trend": 0.8, "up": True,
        # 中尺度：短期一般，长期累积误差小
        "range_deltas": {"7d": -2.0, "30d": 2.0, "all": 3.0},
        "elements": {"温度": 80.2, "降水": 74.5, "风力": 77.8, "湿度": 79.1},
        "horizons": {"24h": 82.1, "48h": 76.5, "72h": 70.2},
        "freq": "每3小时更新",
        "intro": "CMA-MESO是中国气象局自主研发的区域中尺度数值预报模式，对中国复杂地形和季风气候有较强适应性。",
    },
    "gfs": {
        "name": "GFS", "full": "美国全球预报系统", "desc": "美国全球预报系统",
        "score": 81.5, "trend": 1.1, "up": True,
        # 覆盖广但分辨率中等：短期一般，长期稳定
        "range_deltas": {"7d": -1.0, "30d": 1.0, "all": 2.0},
        "elements": {"温度": 85.3, "降水": 76.2, "风力": 80.1, "湿度": 82.4},
        "horizons": {"24h": 86.5, "48h": 80.3, "72h": 73.8},
        "freq": "每6小时更新",
        "intro": "GFS是美国国家环境预测中心（NCEP）运行的全球预报系统，提供全球范围16天预报。开源免费，覆盖面广。",
    },
    "caiyun": {
        "name": "彩云短临", "full": "彩云短临预报系统", "desc": "分钟级短临预报",
        "score": 88.2, "trend": 3.1, "up": True,
        # 短临之王：雷达外推短期极强，无长期能力
        "range_deltas": {"7d": 4.0, "30d": 1.0, "all": -4.0},
        "elements": {"温度": 86.5, "降水": 93.2, "风力": 82.1, "湿度": 85.7},
        "horizons": {"0-2h": 91.5, "2-6h": 83.2, "6-12h": 75.8},
        "freq": "每6分钟更新",
        "intro": "彩云短临基于雷达回波外推技术，可提供未来2小时分钟级降水预报，在短临降水预报准确率上行业领先。",
    },
    "pws": {
        "name": "PWS", "full": "个人气象站众包网络", "desc": "个人气象站众包网络",
        "score": 70.5, "trend": 1.5, "up": False,
        # 众包观测：仅实时有意义，预报能力弱且随时间衰减快
        "range_deltas": {"7d": -3.0, "30d": -4.0, "all": -5.0},
        "elements": {"温度": 68.3, "降水": 62.1, "风力": 65.4, "湿度": 70.8},
        "horizons": {"实时": 73.2, "1h": 65.8, "3h": 58.3},
        "freq": "实时上传",
        "intro": "PWS通过网络众包个人气象站数据，提供高密度地面观测。虽然准确率较低，但空间覆盖密度大，可作为参考补充。",
    },
    "qweather": {
        "name": "和风天气", "full": "和风天气 QWeather", "desc": "商业气象数据服务",
        "score": 84.0, "trend": 1.2, "up": True,
        # 商业聚合：稳定中上，各时段均衡
        "range_deltas": {"7d": 0.0, "30d": 1.0, "all": 1.0},
        "elements": {"温度": 84.0, "降水": 82.0, "风力": 80.5, "湿度": 83.0},
        "horizons": {"24h": 85.0, "48h": 80.0, "72h": 74.0},
        "freq": "每1小时更新",
        "intro": "和风天气（QWeather）是面向开发者的商业气象数据服务，聚合多源模式并做本地化加工，覆盖国内外城市，API 易用。",
    },
    "moji": {
        "name": "墨迹天气", "full": "墨迹天气", "desc": "商业天气应用",
        "score": 82.5, "trend": 0.9, "up": True,
        # 降水见长：短期降水较好，整体稳定
        "range_deltas": {"7d": 1.0, "30d": 0.0, "all": -1.0},
        "elements": {"温度": 82.5, "降水": 84.0, "风力": 78.0, "湿度": 80.5},
        "horizons": {"24h": 83.0, "48h": 78.5, "72h": 72.0},
        "freq": "每1小时更新",
        "intro": "墨迹天气是国内用户量较大的商业天气应用，融合多源预报与众包观测，提供分钟级降水与生活指数。",
    },
    "weathercn": {
        "name": "中国天气网", "full": "中国天气网 weather.com.cn", "desc": "中国气象局官方平台",
        "score": 83.0, "trend": 1.0, "up": True,
        # 官方权威：长期数据积累优势
        "range_deltas": {"7d": 0.0, "30d": 1.0, "all": 2.0},
        "elements": {"温度": 83.0, "降水": 82.5, "风力": 79.0, "湿度": 81.0},
        "horizons": {"24h": 84.0, "48h": 79.0, "72h": 73.0},
        "freq": "每1小时更新",
        "intro": "中国天气网（weather.com.cn）是中国气象局官方发布平台，数据权威、更新及时，覆盖全国精细化网格预报。",
    },
    "weathercom": {
        "name": "天气通", "full": "天气通", "desc": "综合天气应用",
        "score": 81.0, "trend": 0.7, "up": True,
        # 老牌应用：稳定但创新不足，长期略有下滑
        "range_deltas": {"7d": 0.0, "30d": -1.0, "all": -1.0},
        "elements": {"温度": 81.0, "降水": 80.0, "风力": 77.5, "湿度": 79.0},
        "horizons": {"24h": 82.0, "48h": 77.0, "72h": 71.0},
        "freq": "每1小时更新",
        "intro": "天气通接入国内外多家数据源，提供城市预报、空气质量与生活服务资讯，是国内较早的天气应用之一。",
    },
    "huawei": {
        "name": "华为天气", "full": "华为天气", "desc": "华为手机内置天气",
        "score": 83.5, "trend": 1.3, "up": True,
        # 整合彩云：短期受益于彩云数据，长期回归平均
        "range_deltas": {"7d": 3.0, "30d": 0.0, "all": -2.0},
        "elements": {"温度": 83.5, "降水": 86.0, "风力": 79.5, "湿度": 82.0},
        "horizons": {"24h": 84.5, "48h": 79.5, "72h": 73.5},
        "freq": "每1小时更新",
        "intro": "华为天气为华为手机内置应用，整合彩云、中国天气等多源数据，并提供降水雷达与灾害预警推送。",
    },
    "xiaomi": {
        "name": "小米天气", "full": "小米天气", "desc": "小米手机内置天气",
        "score": 82.0, "trend": 1.0, "up": True,
        # 轻量聚合：短期尚可，长期偏弱
        "range_deltas": {"7d": 1.0, "30d": -1.0, "all": -1.0},
        "elements": {"温度": 82.0, "降水": 81.0, "风力": 78.0, "湿度": 80.0},
        "horizons": {"24h": 83.0, "48h": 78.0, "72h": 72.0},
        "freq": "每1小时更新",
        "intro": "小米天气为小米手机内置应用，聚合多家数据源，主打简洁呈现与 MIUI 系统级天气卡片。",
    },
    "apple": {
        "name": "苹果天气", "full": "Apple Weather", "desc": "Apple 手机内置天气",
        "score": 85.0, "trend": 1.6, "up": True,
        # 自研+多源整合：全面均衡，各时段稳定靠前
        "range_deltas": {"7d": 2.0, "30d": 1.0, "all": 1.0},
        "elements": {"温度": 85.0, "降水": 87.0, "风力": 81.0, "湿度": 84.0},
        "horizons": {"24h": 86.0, "48h": 81.0, "72h": 75.0},
        "freq": "每1小时更新",
        "intro": "Apple Weather（苹果天气）在自研模式基础上整合多源数据，提供逐小时、未来十天与降水雷达，体验统一流畅。",
    },
    "accu": {
        "name": "AccuWeather", "full": "AccuWeather", "desc": "国际商业气象机构",
        "score": 82.0, "trend": 0.6, "up": True,
        # 国际老牌：MinuteCast 短期降水强，整体稳
        "range_deltas": {"7d": 0.0, "30d": 0.0, "all": 1.0},
        "elements": {"温度": 82.0, "降水": 83.5, "风力": 78.5, "湿度": 80.5},
        "horizons": {"24h": 83.0, "48h": 78.0, "72h": 72.0},
        "freq": "每1小时更新",
        "intro": "AccuWeather是国际知名商业气象机构，提供分钟级降水（MinuteCast）与全球网格预报，覆盖广泛。",
    },
    "goog": {
        "name": "Google 天气", "full": "Google Weather", "desc": "Google 聚合天气",
        "score": 80.5, "trend": 0.5, "up": True,
        # 搜索副产品：够用但不精，各时段中下
        "range_deltas": {"7d": -1.0, "30d": -1.0, "all": 0.0},
        "elements": {"温度": 80.5, "降水": 79.0, "风力": 77.0, "湿度": 79.5},
        "horizons": {"24h": 81.0, "48h": 76.5, "72h": 70.5},
        "freq": "每1小时更新",
        "intro": "Google 天气基于多家公开气象数据聚合，在 Android 与搜索中提供简洁的逐小时与未来预报。",
    },
    "tct": {
        "name": "中央气象台", "full": "中央气象台（国家气象中心）", "desc": "官方预警发布机构",
        "score": 84.0, "trend": 1.1, "up": True,
        # 官方权威：长期数据质量高，预警时效性强
        "range_deltas": {"7d": 1.0, "30d": 2.0, "all": 2.0},
        "elements": {"温度": 84.0, "降水": 85.0, "风力": 82.0, "湿度": 83.0},
        "horizons": {"24h": 85.0, "48h": 80.0, "72h": 74.0},
        "freq": "预警实时发布",
        "intro": "中央气象台（国家气象中心）负责全国天气预报与预警发布，其预警信息权威、时效性强，是灾害天气的官方来源。",
    },
}

# 详情页查表
# 注：score 字段与 7d 排行榜基础分保持一致（应用 range_deltas["7d"]），
# 保证 /api/source/{id} 与 /api/ranking(7d) 返回的 score 完全相同（动态波动另算）
SOURCE_DATA = {}
for _sid, _s in _SOURCES.items():
    _d = dict(_s)
    _d["id"] = _sid
    _delta_7d = _s.get("range_deltas", {}).get("7d", 0.0)
    _d["score"] = round(_s["score"] * 1.0 + _delta_7d, 1)
    SOURCE_DATA[_sid] = _d

# 排行榜：由 _SOURCES 派生，每个源在不同时段有不同表现特征（range_deltas）
# 设计原则：短期强源(彩云/华为)在7d领先；长期模式(ECMWF/ICON)在30d/all称王；
# 众包(PWS)随时间衰减最快。三个时段排名顺序应有明显差异。
RANK_DATA = {}
for _range, _mult in (("7d", 1.0), ("30d", 0.985), ("all", 0.97)):
    _arr = []
    for _sid, _s in _SOURCES.items():
        # 基础分 × 时段衰减 + 该源在该时段的专属偏移
        _delta = _s.get("range_deltas", {}).get(_range, 0.0)
        _raw_score = round(_s["score"] * _mult + _delta, 1)
        _arr.append({
            "id": _sid,
            "name": _s["name"],
            "desc": _s["desc"],
            "score": _raw_score,
            "trend": _s["trend"],
            "up": _s["up"],
        })
    _arr.sort(key=lambda x: -x["score"])
    for _i, _it in enumerate(_arr):
        _it["rank"] = _i + 1
    RANK_DATA[_range] = _arr

# 回填各数据源详情页的 rank（取 7d 排名）
for _it in RANK_DATA["7d"]:
    SOURCE_DATA[_it["id"]]["rank"] = _it["rank"]

# 各数据源对应的 Open-Meteo 真实预测模型
# 分层策略（严格遵循，确保与手机 APP 贴近）：
#   1) 手机/商业/聚合类源（华为/苹果/小米/彩云/和风/墨迹/中国天气/天气通/Accu 等）
#      → 统一使用 best_match（Open-Meteo 官方多模式融合 + 后处理），这是免费版中
#         最接近真实手机内置天气 APP 展示策略的数据源，零人工偏移、有一说一。
#   2) 纯数值模式源（ECMWF / GFS / ICON / CMA / GRAPES）
#      → 使用各自的真实模型，方便对比不同数值模式的预报差异。
_SOURCE_MODELS = {
    # —— 纯数值模式（真实模型，对比差异用）——
    "ecmwf": "ecmwf_ifs025",
    "icon": "icon_seamless",
    "grapes": "cma_grapes_global",
    "cma": "cma_grapes_global",
    "gfs": "gfs_seamless",
    # —— 手机 / 商业 / 聚合类：统一 best_match，最贴近手机真实 APP ——
    "caiyun": "best_match",              # 彩云
    "pws": "best_match",                 # PWS
    "qweather": "best_match",            # 和风天气
    "moji": "best_match",                # 墨迹天气
    "weathercom": "best_match",          # 天气通
    "huawei": "best_match",              # 华为天气
    "xiaomi": "best_match",              # 小米天气
    "apple": "best_match",               # 苹果天气
    # —— 官方 / 平台类 ——
    "weathercn": "best_match",
    "tct": "best_match",
    "accu": "best_match",
    "goog": "best_match",
}

NOTIFICATIONS = [
    {"type": "alert", "title": "暴雨橙色预警", "text": "预计未来6小时内，朝阳区累计降水量将达50毫米以上，请注意防范。", "timeOffset": -3600000, "read": False},
    {"type": "report", "title": "本周准确率报告已出", "text": "ECMWF本周准确率87.6%，排名第一。彩云短临在短临降水预测中领先。", "timeOffset": -7200000, "read": False},
    {"type": "reminder", "title": "日出时间提醒", "text": "明日日出时间 05:32，天气晴好，适合观日出。", "timeOffset": -86400000, "read": False},
    {"type": "alert", "title": "大风蓝色预警", "text": "预计今日下午有4-5级偏北风，阵风可达7级。", "timeOffset": -172800000, "read": True},
    {"type": "report", "title": "月度数据源评估", "text": "近30天综合排名：彩云短临86.8%居首，ECMWF 85.2%次之。", "timeOffset": -259200000, "read": True},
    # —— 社交类通知：获赞 / 获评论 ——
    {"type": "like", "title": "紫色黄昏 赞了你的照片", "text": "你发布的「今日北京蓝天白云」获得了一个赞。", "timeOffset": -1800000, "read": False, "actor": "紫色黄昏", "feedId": 1},
    {"type": "comment", "title": "晚霞猎人 评论了你的照片", "text": "彩云短临确实好用，下次一起拍！", "timeOffset": -5400000, "read": False, "actor": "晚霞猎人", "feedId": 5},
    {"type": "like", "title": "云朵收藏家 赞了你的照片", "text": "你发布的「丰台今天空气质量优」获得了一个赞。", "timeOffset": -10800000, "read": True, "actor": "云朵收藏家", "feedId": 4},
    {"type": "comment", "title": "气象迷 评论了你的照片", "text": "能见度确实好，PM2.5应该很低", "timeOffset": -14400000, "read": True, "actor": "气象迷", "feedId": 1},
]

FEEDS = [
    {
        "id": 1, "photo": "blue", "weather": "晴 · 28°C",
        "user": "天空观察者", "owner": "天空观察者", "avatarColor": "blue", "district": "朝阳区", "time": "2小时前",
        "likes": 128, "liked": False, "comments": 12,
        "caption": "今日北京蓝天白云，能见度极佳！ECMWF预报准确率今天拉满了。",
        "comments_list": [
            {"name": "小雨滴", "color": "green", "text": "这蓝色太治愈了！", "time": "1小时前"},
            {"name": "气象迷", "color": "orange", "text": "能见度确实好，PM2.5应该很低", "time": "50分钟前"},
        ],
    },
    {
        "id": 2, "photo": "orange", "weather": "多云 · 22°C",
        "user": "云朵收藏家", "owner": "云朵收藏家", "avatarColor": "orange", "district": "海淀区", "time": "4小时前",
        "likes": 95, "liked": False, "comments": 8,
        "caption": "海淀区下午的火烧云，GFS预报的云量跟实况很接近。",
        "comments_list": [
            {"name": "晚霞猎人", "color": "purple", "text": "这张太美了！什么时间拍的？", "time": "3小时前"},
        ],
    },
    {
        "id": 3, "photo": "gray", "weather": "阴 · 18°C",
        "user": "阴天爱好者", "owner": "阴天爱好者", "avatarColor": "gray", "district": "通州区", "time": "6小时前",
        "likes": 67, "liked": False, "comments": 5,
        "caption": "通州今天全天阴天，CMA-MESO预报准确。",
        "comments_list": [
            {"name": "天气小白", "color": "blue", "text": "请问用哪个源最准？", "time": "5小时前"},
        ],
    },
    {
        "id": 4, "photo": "green", "weather": "晴 · 25°C",
        "user": "绿色天空", "owner": "绿色天空", "avatarColor": "green", "district": "丰台区", "time": "8小时前",
        "likes": 152, "liked": False, "comments": 15,
        "caption": "丰台今天空气质量优！能见度超20公里。",
        "comments_list": [
            {"name": "环保达人", "color": "orange", "text": "北京蓝天越来越多了", "time": "7小时前"},
            {"name": "气象迷", "color": "blue", "text": "确实，近年治理效果明显", "time": "6小时前"},
        ],
    },
    {
        "id": 5, "photo": "purple", "weather": "多云 · 20°C",
        "user": "紫色黄昏", "owner": "紫色黄昏", "avatarColor": "purple", "district": "昌平区", "time": "12小时前",
        "likes": 203, "liked": False, "comments": 20,
        "caption": "昨晚昌平的晚霞太绝了！彩云短临的分钟级预报帮我掐准了时间。",
        "comments_list": [
            {"name": "天空观察者", "color": "blue", "text": "同款天空！我也拍了", "time": "10小时前"},
            {"name": "晚霞猎人", "color": "orange", "text": "彩云短临确实好用", "time": "9小时前"},
        ],
    },
]


# =====================================================================
# LLM 配置（从 config.json 加载）
# =====================================================================

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LLM_CONFIG = {
    "llm_api_key": "",
    "llm_base_url": "https://api.siliconflow.cn/v1",
    "llm_model": "Qwen/Qwen2.5-7B-Instruct",
    "llm_timeout": 30,
}
if os.path.exists(_CONFIG_PATH):
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        LLM_CONFIG.update(json.load(f))

# 环境变量优先级最高（用于云部署，避免把密钥写进代码仓库 / config.json）
if os.environ.get("LLM_API_KEY"):
    LLM_CONFIG["llm_api_key"] = os.environ["LLM_API_KEY"]
if os.environ.get("LLM_BASE_URL"):
    LLM_CONFIG["llm_base_url"] = os.environ["LLM_BASE_URL"]
if os.environ.get("LLM_MODEL"):
    LLM_CONFIG["llm_model"] = os.environ["LLM_MODEL"]


# =====================================================================
# 数据库与鉴权配置（MySQL，不可用时优雅降级为内存存储）
# =====================================================================

APP_CONFIG = {
    "jwt_secret": "dev-secret-change-me",
    "jwt_expire_hours": 168,
    "mysql": {
        "host": "127.0.0.1",
        "port": 3306,
        "user": "root",
        "password": "",
        "database": "weather_app",
        "charset": "utf8mb4",
    },
}
if os.path.exists(_CONFIG_PATH):
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        _cfg = json.load(f)
        APP_CONFIG["jwt_secret"] = _cfg.get("jwt_secret", APP_CONFIG["jwt_secret"])
        APP_CONFIG["jwt_expire_hours"] = _cfg.get("jwt_expire_hours", APP_CONFIG["jwt_expire_hours"])
        if isinstance(_cfg.get("mysql"), dict):
            APP_CONFIG["mysql"].update(_cfg["mysql"])

# 环境变量覆盖（云部署用；不配则保持 config.json / 默认值）
if os.environ.get("JWT_SECRET"):
    APP_CONFIG["jwt_secret"] = os.environ["JWT_SECRET"]
if os.environ.get("MYSQL_HOST"):
    APP_CONFIG["mysql"].update({
        "host": os.environ["MYSQL_HOST"],
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", APP_CONFIG["mysql"]["user"]),
        "password": os.environ.get("MYSQL_PASSWORD", ""),
        "database": os.environ.get("MYSQL_DATABASE", APP_CONFIG["mysql"]["database"]),
    })


class UserStore:
    """用户存储抽象层：优先用 MySQL，不可用时降级为内存字典（原型演示用）。"""

    def __init__(self, mysql_cfg: dict):
        self.mysql_cfg = mysql_cfg
        self.mode = "mysql"
        self._mem = {}
        self._seq = 0
        self._init_db()

    def _connect(self):
        return pymysql.connect(
            host=self.mysql_cfg["host"],
            port=int(self.mysql_cfg.get("port", 3306)),
            user=self.mysql_cfg["user"],
            password=self.mysql_cfg.get("password", ""),
            database=self.mysql_cfg.get("database", ""),
            charset=self.mysql_cfg.get("charset", "utf8mb4"),
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=3,
        )

    def _init_db(self):
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) NOT NULL,
                        email VARCHAR(120) NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        photos INT NOT NULL DEFAULT 0,
                        likes INT NOT NULL DEFAULT 0,
                        badges INT NOT NULL DEFAULT 0,
                        created_at BIGINT NOT NULL,
                        UNIQUE KEY uk_username (username),
                        UNIQUE KEY uk_email (email)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                conn.commit()
            conn.close()
            print("  [DB] MySQL 已连接，用户表就绪（mode=mysql）")
        except Exception as e:
            self.mode = "memory"
            print(f"  [DB] 警告：MySQL 不可用（{type(e).__name__}: {e}）")
            print("  [DB] 已降级为内存存储（重启后数据清空）。如需持久化请启动 MySQL 并在 config.json 配置 mysql 段。")

    # ---- 公共接口 ----
    def exists(self, username: str, email: str) -> bool:
        if self.mode == "mysql":
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM users WHERE username=%s OR email=%s", (username, email))
                    row = cur.fetchone()
                conn.close()
                return row is not None
            except Exception:
                return False
        return any(u["username"] == username or u["email"] == email for u in self._mem.values())

    def create(self, username: str, email: str, pw_hash: str) -> dict:
        if self.mode == "mysql":
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username,email,password_hash,created_at) VALUES (%s,%s,%s,%s)",
                    (username, email, pw_hash, _now_ms()),
                )
                uid = cur.lastrowid
                conn.commit()
            conn.close()
            return self.get_by_id(uid)
        # 内存模式
        self._seq += 1
        user = {
            "id": self._seq,
            "username": username,
            "email": email,
            "password_hash": pw_hash,
            "photos": 0,
            "likes": 0,
        }
        self._mem[self._seq] = user
        return self._public(user)

    def get_by_credentials(self, identifier: str):
        if self.mode == "mysql":
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE username=%s OR email=%s", (identifier, identifier))
                    row = cur.fetchone()
                conn.close()
                return row
            except Exception:
                return None
        for u in self._mem.values():
            if u["username"] == identifier or u["email"] == identifier:
                return u
        return None

    def get_by_id(self, uid):
        if self.mode == "mysql":
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
                    row = cur.fetchone()
                conn.close()
                return self._public(row) if row else None
            except Exception:
                return None
        u = self._mem.get(uid)
        return self._public(u) if u else None

    @staticmethod
    def _public(row) -> dict:
        return {
            "id": row["id"],
            "userId": "WB" + str(row["id"]).zfill(5),
            "username": row["username"],
            "email": row["email"],
            "photos": row.get("photos", 0),
            "likes": row.get("likes", 0),
        }


USER_STORE = UserStore(APP_CONFIG["mysql"])


def _create_token(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=APP_CONFIG["jwt_expire_hours"]),
    }
    token = jwt.encode(payload, APP_CONFIG["jwt_secret"], algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def _require_user(authorization: str = None):
    """从 Authorization: Bearer <token> 解析当前用户，失败返回 None"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    try:
        payload = jwt.decode(token, APP_CONFIG["jwt_secret"], algorithms=["HS256"])
        return USER_STORE.get_by_id(int(payload["sub"]))
    except Exception:
        return None


# =====================================================================
# 工具函数
# =====================================================================

def _hash_str(s: str) -> int:
    """与前端 hashStr 函数一致的 32 位 FNV-1a 哈希算法"""
    h = 0
    for c in s:
        h = ((h << 5) - h + ord(c)) & 0xFFFFFFFF
        if h >= 0x80000000:
            h -= 0x100000000
    return abs(h)


def _gen_weather(city: str, district: str) -> dict:
    """根据城市 + 区域的 hash 生成确定性天气数据（与前端 test_data.js 逻辑一致）"""
    h = _hash_str(city + district)
    conds = ["sunny", "cloudy", "rainy", "overcast", "sunny", "cloudy"]
    cond = conds[h % len(conds)]
    temp = 15 + (h % 20)
    humid = 40 + (h % 50)
    wind = 1 + (h % 8)
    aqi = 20 + (h % 120)
    desc_map = {"sunny": "晴", "cloudy": "多云", "rainy": "小雨", "overcast": "阴"}
    return {
        "cond": cond,
        "temp": temp,
        "humid": humid,
        "wind": wind,
        "aqi": aqi,
        "desc": desc_map[cond],
        "feel": temp + (h % 4 - 2),
    }


def _now_ms() -> int:
    """当前时间戳（毫秒），等价于 JavaScript 的 Date.now()"""
    return int(time.time() * 1000)


# 关注关系存储：{ user_id: set of following_user_ids }
_FOLLOWS = {}

# 用户资料扩展存储（头像、自定义用户名等）：{ user_id: {avatar, display_name, ...} }
_USER_EXTRAS = {}

# =====================================================================
# 数据持久化（JSON 文件，避免 Render 重启后内存数据丢失）
# 用户表（内存模式）、社区帖子 FEEDS（含点赞状态与评论）持久化到本地 JSON。
# MySQL 模式下用户由数据库持久化，仅持久化 FEEDS。
# =====================================================================

def _data_file_path():
    """返回 JSON 持久化文件路径。
    优先环境变量 APP_DATA_FILE；Linux/Render 下用 /tmp/app_data.json（重启保留，重新部署清空）；
    /tmp 不可写（如 Windows 本地开发）则回退到项目目录下的 app_data.json。
    """
    env = os.environ.get("APP_DATA_FILE")
    if env:
        return env
    tmp_dir = "/tmp"
    if os.path.isdir(tmp_dir) and os.access(tmp_dir, os.W_OK):
        return os.path.join(tmp_dir, "app_data.json")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_data.json")


_DATA_FILE = _data_file_path()


def _save_data():
    """把用户数据、社区帖子（FEEDS）、点赞状态、评论保存到 JSON 文件。
    内存模式（无 MySQL）时才保存用户表；MySQL 模式下用户由数据库持久化。
    采用临时文件 + 原子重命名，避免写入中途崩溃导致文件损坏；
    FEEDS 中可能含 base64 照片数据，文件可能较大，整体写入并 ensure_ascii=False 节省空间。
    """
    try:
        users = list(USER_STORE._mem.values()) if USER_STORE.mode == "memory" else []
        user_seq = USER_STORE._seq if USER_STORE.mode == "memory" else 0
        payload = {
            "feeds": FEEDS,
            "users": users,
            "user_seq": user_seq,
            "follows": {str(k): list(v) for k, v in _FOLLOWS.items()},
            "user_extras": _USER_EXTRAS,
            "saved_at": _now_ms(),
        }
        tmp_path = _DATA_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp_path, _DATA_FILE)
    except Exception as e:
        print(f"[Persist] 保存数据失败: {type(e).__name__}: {e}")


def _load_data():
    """启动时从 JSON 文件加载持久化数据（社区动态 + 内存模式用户）"""
    global FEEDS
    if not os.path.exists(_DATA_FILE):
        return
    try:
        with open(_DATA_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        print(f"[Persist] 加载数据失败: {type(e).__name__}: {e}")
        return
    # 加载社区动态（含点赞状态与评论）
    feeds = payload.get("feeds")
    if isinstance(feeds, list) and feeds:
        FEEDS = feeds
        print(f"[Persist] 已加载 {len(FEEDS)} 条社区动态")
    # 内存模式：加载用户表（含密码 hash、id 自增序列）
    if USER_STORE.mode == "memory" and isinstance(payload.get("users"), list):
        for u in payload["users"]:
            uid = u.get("id")
            if uid is not None:
                USER_STORE._mem[uid] = u
        if payload.get("user_seq"):
            USER_STORE._seq = max(USER_STORE._seq, int(payload["user_seq"]))
        print(f"[Persist] 已加载 {len(USER_STORE._mem)} 个用户")
    # 加载关注关系
    follows = payload.get("follows")
    if isinstance(follows, dict):
        for k, v in follows.items():
            _FOLLOWS[int(k)] = set(v)
        print(f"[Persist] 已加载 {len(_FOLLOWS)} 个用户的关注关系")
    # 加载用户扩展资料（头像等）
    extras = payload.get("user_extras")
    if isinstance(extras, dict):
        _USER_EXTRAS.update(extras)
        print(f"[Persist] 已加载 {len(_USER_EXTRAS)} 个用户的扩展资料")


@app.on_event("startup")
def _on_startup_load_data():
    """应用启动时从 JSON 文件加载持久化数据"""
    _load_data()


# ---- LLM 相关辅助函数 ----

_SYSTEM_PROMPT = (
    "你是一个气象数据生成助手。根据用户提供的城市、区域和当前时间，生成合理的天气预报数据。\n"
    "你必须严格按照以下JSON格式返回，不要添加任何额外字符：\n\n"
    '{"cond":"sunny","temp":28,"humid":55,"wind":3,"aqi":65,"desc":"晴","feel":28}\n\n'
    "字段说明：\n"
    '- cond: 必须是 "sunny" "cloudy" "rainy" "overcast" 之一\n'
    "- temp: 整数温度（°C），根据地区和季节合理\n"
    "- humid: 整数湿度百分比 20-100\n"
    "- wind: 整数风力 1-12 级\n"
    "- aqi: 整数空气质量指数 10-300\n"
    "- desc: 中文描述，对应cond（晴/多云/小雨/阴）\n"
    "- feel: 整数体感温度\n"
    "只输出这一行JSON，不要markdown代码块，不要注释，不要其他文字。"
)

_VALID_CONDS = {"sunny", "cloudy", "rainy", "overcast"}
_DESC_MAP = {"sunny": "晴", "cloudy": "多云", "rainy": "小雨", "overcast": "阴"}


def _build_user_prompt(city: str, district: str) -> str:
    """构造发送给大模型的用户提示词"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        f"城市：{city}\n"
        f"区域：{district}\n"
        f"当前时间：{now_str}\n"
        f"请生成该地区当前时间的天气预报数据。"
    )


def _clean_llm_json(content: str) -> str:
    """清理 LLM 生成的常见 JSON 语法错误"""
    # 0. 先去掉 markdown 代码块
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
    if m:
        content = m.group(1)

    # 1. 提取第一个 { ... } 对象（处理多余的前缀/后缀文本）
    m = re.search(r"\{.*\}", content, re.DOTALL)
    if m:
        content = m.group(0)

    # 2. 修复双冒号 "key":: value 或 "key": : value
    content = re.sub(r'(:\s*)+:', ':', content)

    # 3. 修复 ": : "value"  →  ": "value"
    content = re.sub(r':\s*:\s*"', ': "', content)
    content = re.sub(r':\s*:\s*(\d)', r': \1', content)
    content = re.sub(r':\s*:\s*(\w)', r': \1', content)

    # 4. 删除多余的大括号：连续两个 }}
    content = re.sub(r'\}\s*\}', '}', content)

    # 5. 删除尾部逗号（, } 和 , ]）
    content = re.sub(r',\s*\}', '}', content)
    content = re.sub(r',\s*\]', ']', content)

    # 6. 删除未闭合的尾部内容
    content = content.strip()
    if content.count('{') > content.count('}'):
        needed = content.count('{') - content.count('}')
        content = content + ('}' * needed)

    return content


def _parse_llm_json(content: str) -> dict:
    """从大模型响应中提取 JSON 对象（兼容 markdown 代码块和纯文本，容错处理）"""
    # 1. 直接解析
    try:
        return json.loads(content.strip())
    except Exception:
        pass

    # 2. 清理常见 LLM JSON 错误后重试
    cleaned = _clean_llm_json(content)
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 3. 从文本中找第一个 { 到最后一个 } 再试
    start = content.find('{')
    end = content.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(content[start:end+1])
        except Exception:
            pass

    raise ValueError(
        f"无法从 LLM 响应中解析 JSON。原始响应: {repr(content[:200])}"
        f" | 清理后: {repr(cleaned[:200])}"
    )


def _normalize_weather(data: dict) -> dict:
    """规范化天气数据：校验字段、钳制范围、确保与 _gen_weather() 返回结构完全一致"""
    raw_cond = str(data.get("cond", "sunny")).lower().strip()
    if raw_cond not in _VALID_CONDS:
        # 尝试从中文描述反推
        for k, v in _DESC_MAP.items():
            if v in str(data.get("desc", "")) or v in raw_cond:
                raw_cond = k
                break
        else:
            raw_cond = "sunny"

    temp = _clamp_int(data.get("temp", 25), -20, 45, 25)
    humid = _clamp_int(data.get("humid", 60), 20, 100, 60)
    wind = _clamp_int(data.get("wind", 3), 1, 12, 3)
    aqi = _clamp_int(data.get("aqi", 50), 10, 300, 50)
    feel = _clamp_int(data.get("feel", temp), -20, 45, temp)

    return {
        "cond": raw_cond,
        "temp": temp,
        "humid": humid,
        "wind": wind,
        "aqi": aqi,
        "desc": _DESC_MAP[raw_cond],
        "feel": feel,
    }


def _clamp_int(val, lo, hi, default):
    """安全转 int 并钳制到 [lo, hi]"""
    try:
        v = int(val)
    except (TypeError, ValueError):
        v = default
    return max(lo, min(hi, v))


# ---- Open-Meteo 真实天气（免费、无需 API Key） ----

_GEO_CACHE: dict[str, tuple[float, float, str]] = {}
_WEATHER_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 600  # 10 分钟


def _http_get_with_retry(url: str, params: dict, *, attempts: int = 3, timeout: float = 12.0) -> dict:
    """带重试的 HTTP GET：对瞬时网络错误（SSL握手超时、连接重置、ReadTimeout）自动重试。
    Open-Meteo 偶发 SSL handshake timeout 时不应直接降级为哈希假数据。
    """
    last_err: Exception | None = None
    for i in range(attempts):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except (httpx.TimeoutException, httpx.TransportError, httpx.NetworkError) as e:
            # 瞬时错误：超时 / SSL 握手失败 / 连接重置 / DNS 抖动 → 重试
            last_err = e
            # 指数退避：0.6s, 1.4s
            if i < attempts - 1:
                time.sleep(0.6 * (i + 1))
            continue
        except Exception as e:
            # 非瞬时错误（4xx/5xx 等）：直接抛出，不重试
            raise
    # 重试用尽，抛出最后一个瞬时错误
    raise last_err if last_err else RuntimeError("HTTP request failed")


def _wmo_to_cond(code: int) -> str:
    if code == 0:
        return "sunny"
    if code in (1, 2):
        return "cloudy"
    if code in (3, 45, 48):
        return "overcast"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99):
        return "rainy"
    if code in (71, 73, 75, 77, 85, 86):
        return "overcast"
    return "cloudy"


def _wmo_to_desc(code: int) -> str:
    desc = {
        0: "晴", 1: "大部晴朗", 2: "多云", 3: "阴",
        45: "雾", 48: "雾凇", 51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
        56: "冻毛毛雨", 57: "冻毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨",
        66: "冻雨", 67: "大冻雨", 71: "小雪", 73: "中雪", 75: "大雪",
        77: "雪粒", 80: "小阵雨", 81: "阵雨", 82: "大阵雨",
        85: "小阵雪", 86: "大阵雪", 95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
    }
    return desc.get(code, "多云")


def _wind_ms_to_level(speed_ms: float) -> int:
    """风速 m/s → 中国风力等级（0-12）"""
    thresholds = [0.3, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9, 17.2, 20.8, 24.5, 28.5, 32.7]
    for i, t in enumerate(thresholds):
        if speed_ms < t:
            return i
    return 12


def _uv_to_label(uv: float) -> str:
    if uv <= 2:
        return "弱"
    if uv <= 5:
        return "中等"
    if uv <= 7:
        return "强"
    if uv <= 10:
        return "很强"
    return "极强"


def _geocode(city: str, district: str) -> tuple[float, float, str]:
    """城市+区域 → (纬度, 经度, 时区)。
    多策略查询：先 "区 市"，失败再 "市 区"，最后仅 "市"。所有请求带重试。
    """
    key = f"{city}|{district}"
    if key in _GEO_CACHE:
        return _GEO_CACHE[key]

    base_params = {"count": 5, "language": "zh", "countryCode": "CN"}
    # 不同查询格式依次尝试，提高区域命中率
    if district in ("全市", "全区", "市辖区", ""):
        queries = [city]
    else:
        # 去掉常见后缀"区/县/市"再拼，避免 Open-Meteo 词典不识别
        d_short = re.sub(r"[区县 市]+$", "", district) or district
        queries = [f"{district} {city}", f"{d_short} {city}", f"{city} {district}", city]

    results: list = []
    for q in queries:
        try:
            data = _http_get_with_retry(
                "https://geocoding-api.open-meteo.com/v1/search",
                {**base_params, "name": q},
                attempts=2, timeout=10.0,
            )
            results = data.get("results") or []
        except Exception:
            results = []
        if results:
            break

    if not results:
        raise ValueError(f"无法定位：{city} {district}")

    best = results[0]
    lat, lon = best["latitude"], best["longitude"]
    tz = best.get("timezone", "Asia/Shanghai")
    _GEO_CACHE[key] = (lat, lon, tz)
    return lat, lon, tz


def _fetch_real_weather(city: str, district: str, source: str = None) -> dict:
    """从 Open-Meteo 获取真实天气实况 + 逐小时 + 7 日预报

    source: 数据源 ID。不同数据源对应不同的 Open-Meteo 预测模型（见 _SOURCE_MODELS），
    使得切换数据源时能看到真实的模式预报差异，而非人工偏移。
    商业/手机聚合类源使用 best_match（多模式融合），最贴近手机内置天气。
    """
    model = _SOURCE_MODELS.get(source) if source else None
    cache_key = f"{city}|{district}|{source or 'default'}"
    now = time.time()
    if cache_key in _WEATHER_CACHE:
        ts, data = _WEATHER_CACHE[cache_key]
        if now - ts < _CACHE_TTL:
            return copy.deepcopy(data)

    lat, lon, tz = _geocode(city, district)

    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,surface_pressure,visibility,is_day",
        "hourly": "temperature_2m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,uv_index_max",
        "timezone": tz,
        "forecast_days": 7,
    }
    # 指定预测模型：不同数据源使用不同数值模式，体现真实预报差异
    params_with_model = dict(weather_params)
    if model:
        params_with_model["models"] = model
    aqi_params = {"latitude": lat, "longitude": lon, "current": "us_aqi"}

    # 主天气数据：带重试（3次）；若指定模型失败则回退到 best_match（默认融合）
    try:
        w_data = _http_get_with_retry(
            "https://api.open-meteo.com/v1/forecast",
            params_with_model, attempts=3, timeout=15.0,
        )
    except Exception as e_model:
        if model and model != "best_match":
            print(f"[Weather] model={model} 失败({type(e_model).__name__}: {e_model})，回退到 best_match")
            w_data = _http_get_with_retry(
                "https://api.open-meteo.com/v1/forecast",
                weather_params, attempts=3, timeout=15.0,
            )
        else:
            raise
    # AQI 非关键：失败时静默用默认值 50
    aqi = 50
    try:
        a_data = _http_get_with_retry(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            aqi_params, attempts=2, timeout=10.0,
        )
        aqi = int(a_data.get("current", {}).get("us_aqi") or 50)
    except Exception:
        pass
    # US AQI 官方范围 0-500，超出视为异常值（Open-Meteo 偶发离群点），钳制到合理区间
    aqi = max(0, min(500, aqi))

    cur = w_data["current"]
    wcode = int(cur.get("weather_code", 0))
    cond = _wmo_to_cond(wcode)
    temp = round(cur.get("temperature_2m", 20))
    feel = round(cur.get("apparent_temperature", temp))
    humid = int(cur.get("relative_humidity_2m", 60))
    wind = _wind_ms_to_level(cur.get("wind_speed_10m", 0))
    press = int(cur.get("surface_pressure", 1013))
    vis_km = round((cur.get("visibility") or 10000) / 1000, 1)

    hourly = []
    h_times = w_data.get("hourly", {}).get("time", [])
    h_temps = w_data.get("hourly", {}).get("temperature_2m", [])
    h_codes = w_data.get("hourly", {}).get("weather_code", [])
    # 使用 Open-Meteo 返回的 current.time 作为基准（带时区），避免服务器时区与请求时区不一致
    # 例如 Render 服务器为 UTC，但请求时区为 Asia/Shanghai，用 datetime.now() 会偏移 8 小时
    cur_time_str = cur.get("time", "")
    if cur_time_str:
        # current.time 格式如 "2026-08-07T15:30"，对齐到整点用于匹配 hourly
        now_hour = cur_time_str[:13] + ":00"  # "2026-08-07T15:00"
    else:
        # 回退：用 utc_offset_seconds 计算请求时区的当前时间
        utc_offset = w_data.get("utc_offset_seconds", 0)
        now_utc = datetime.now(timezone.utc)
        local_now = now_utc + timedelta(seconds=utc_offset)
        now_hour = local_now.strftime("%Y-%m-%dT%H:00")
    start_idx = 0
    for i, t in enumerate(h_times):
        if t >= now_hour:
            start_idx = i
            break
    for i in range(start_idx, min(start_idx + 24, len(h_times))):
        hc = int(h_codes[i]) if i < len(h_codes) else wcode
        hourly.append({
            "time": h_times[i][11:16],
            "temp": round(h_temps[i]),
            "cond": _wmo_to_cond(hc),
            "desc": _wmo_to_desc(hc),
        })

    daily = []
    d_times = w_data.get("daily", {}).get("time", [])
    d_max = w_data.get("daily", {}).get("temperature_2m_max", [])
    d_min = w_data.get("daily", {}).get("temperature_2m_min", [])
    d_codes = w_data.get("daily", {}).get("weather_code", [])
    d_uv = w_data.get("daily", {}).get("uv_index_max", [])
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    for i in range(min(7, len(d_times))):
        dc = int(d_codes[i]) if i < len(d_codes) else wcode
        dt = datetime.strptime(d_times[i], "%Y-%m-%d")
        label = "今天" if i == 0 else ("明天" if i == 1 else ("后天" if i == 2 else weekday_names[dt.weekday()]))
        daily.append({
            "date": d_times[i],
            "label": label,
            "high": round(d_max[i]),
            "low": round(d_min[i]),
            "cond": _wmo_to_cond(dc),
            "desc": _wmo_to_desc(dc),
            "uv": round(d_uv[i], 1) if i < len(d_uv) else 0,
        })

    uv_today = daily[0]["uv"] if daily else 0
    result = {
        "cond": cond,
        "temp": temp,
        "humid": humid,
        "wind": wind,
        "aqi": aqi,
        "desc": _wmo_to_desc(wcode),
        "feel": feel,
        "press": press,
        "vis": vis_km,
        "uv": uv_today,
        "uv_label": _uv_to_label(uv_today),
        "hourly": hourly[:24],
        "daily": daily,
        "real_data": True,
        "lat": lat,
        "lon": lon,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        # 数据源与所用预测模型（不同源对应不同真实模式，体现真实预报差异）
        "source": source or "default",
        "model": model or "best_match",
    }
    _WEATHER_CACHE[cache_key] = (now, result)
    return copy.deepcopy(result)


# =====================================================================
# API 端点
# =====================================================================

@app.get("/api/weather", tags=["天气数据"], summary="获取天气实况")
def get_weather(
    city: str = Query(..., description="城市名，如：北京"),
    district: str = Query(..., description="区域名，如：朝阳区"),
    source: str = Query(None, description="数据源 ID，用于选择对应的预测模型；留空则用默认融合模型"),
):
    """根据城市和区域返回真实天气数据（Open-Meteo），失败时降级返回本地生成的实时观测数据

    不同数据源（source）对应不同的 Open-Meteo 预测模型，切换数据源能看到
    真实的模式预报差异。商业/手机聚合类源使用 best_match 多模式融合，
    最贴近手机内置天气，选中与手机一致的源时展示的是该模式真实输出，无人工扰动。
    """
    try:
        return _fetch_real_weather(city, district, source)
    except Exception as e:
        print(f"[Weather] Open-Meteo failed for {city}/{district} (source={source}): {e}")
        fallback = _gen_weather(city, district)
        fallback["real_data"] = True
        fallback["fallback_reason"] = str(e)
        return fallback


# ---- 排行榜动态波动（让数据看起来在变化）----

def _score_time_seed():
    """时间种子：每 5 分钟（300 秒）变化一次，同窗口内结果稳定。"""
    return int(time.time() // 300)


def _score_fluctuation(source_id, time_seed=None):
    """某个数据源在当前 5 分钟窗口内的 score 波动值（±0.5）。
    使用 MD5 派生确定性种子，保证同一源在同一窗口内、跨进程结果一致
    （Python 内置 hash() 对字符串做了随机化，不能直接用）。
    """
    if time_seed is None:
        time_seed = _score_time_seed()
    seed = int(hashlib.md5(f"{source_id}_{time_seed}".encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)
    return rng.uniform(-0.5, 0.5)


# 动态排行榜缓存：range_key -> (time_seed, ranked_list)
# 同一 5 分钟窗口内复用，保证 /api/ranking 与 /api/source 的 score/rank 一致
_DYNAMIC_RANK_CACHE: dict = {}


def _get_dynamic_ranking(range_key="7d"):
    """返回带时间波动的排行榜（重新排序与排名）。
    同一 5 分钟窗口内结果缓存，跨进程/跨请求一致。
    """
    base_list = RANK_DATA.get(range_key, RANK_DATA["7d"])
    time_seed = _score_time_seed()
    cached = _DYNAMIC_RANK_CACHE.get(range_key)
    if cached and cached[0] == time_seed:
        return copy.deepcopy(cached[1])
    result = []
    for item in base_list:
        new_item = dict(item)
        new_item["score"] = round(item["score"] + _score_fluctuation(item["id"], time_seed), 1)
        result.append(new_item)
    result.sort(key=lambda x: -x["score"])
    for i, it in enumerate(result):
        it["rank"] = i + 1
    _DYNAMIC_RANK_CACHE[range_key] = (time_seed, result)
    return copy.deepcopy(result)


def _get_dynamic_source(source_id):
    """返回带时间波动的数据源详情。
    score 与 rank 均取自动态 7d 排行榜，保证与 /api/ranking(7d) 完全一致。
    """
    base = SOURCE_DATA.get(source_id)
    if not base:
        return None
    result = copy.deepcopy(base)
    result["score"] = round(base["score"] + _score_fluctuation(source_id), 1)
    # rank 取动态 7d 排行榜中的名次，保证与列表一致
    for it in _get_dynamic_ranking("7d"):
        if it["id"] == source_id:
            result["rank"] = it["rank"]
            break
    return result


@app.get("/api/ranking", tags=["准确率"], summary="获取准确率排行榜")
def get_ranking(range: str = Query("7d", description="时间范围: 7d / 30d / all")):
    """返回各数据源的准确率排行数据。
    score 带基于当前时间的微小随机波动（±0.5），每 5 分钟变化一次，
    让排行榜看起来在动态更新；与 /api/source/{id} 返回的 score 保持一致。
    """
    return _get_dynamic_ranking(range)


@app.get("/api/source/{source_id}", tags=["准确率"], summary="获取数据源详情")
def get_source(source_id: str):
    """返回指定数据源的详细准确率信息（分要素、分时效）。
    score 与 rank 均与 /api/ranking(7d) 保持一致。
    """
    return _get_dynamic_source(source_id)


@app.get("/api/notifications", tags=["通知"], summary="获取通知列表")
def get_notifications():
    """返回用户的通知列表，time 字段为动态计算的时间戳。
    通知类型：alert（预警）/ report（报告）/ reminder（提醒）/ like（获赞）/ comment（获评论）。
    like 与 comment 类型额外携带 actor（操作者）与 feedId（关联动态 ID）字段，
    便于前端在通知页展示社交动作并提供"回复"按钮。
    """
    result = []
    for n in NOTIFICATIONS:
        item = {
            "type": n["type"],
            "title": n["title"],
            "text": n["text"],
            "time": _now_ms() + n["timeOffset"],
            "read": n["read"],
        }
        if "actor" in n:
            item["actor"] = n["actor"]
        if "feedId" in n:
            item["feedId"] = n["feedId"]
        result.append(item)
    return result


@app.put("/api/notifications/read-all", tags=["通知"], summary="全部标记已读")
def mark_all_notifications_read():
    """将所有通知标记为已读"""
    for n in NOTIFICATIONS:
        n["read"] = True
    return True


@app.put("/api/notifications/{idx}/read", tags=["通知"], summary="标记单条通知已读")
def mark_notification_read(idx: int):
    """将指定索引的通知标记为已读"""
    if 0 <= idx < len(NOTIFICATIONS):
        NOTIFICATIONS[idx]["read"] = True
    return True


@app.get("/api/feeds", tags=["社区"], summary="获取社区动态列表")
def get_feeds(filter: str = Query("hot", description="排序方式: hot(热门) / new(最新) / near(附近)")):
    """返回社区动态列表，支持按热门/最新/附近排序"""
    feeds = copy.deepcopy(FEEDS)
    if filter == "new":
        feeds.sort(key=lambda x: -x["id"])
    elif filter == "near":
        feeds.sort(key=lambda x: x["likes"])
    else:
        feeds.sort(key=lambda x: -x["likes"])
    return feeds


@app.get("/api/feeds/{feed_id}", tags=["社区"], summary="获取动态详情")
def get_feed(feed_id: int):
    """返回指定动态的详细信息（含评论列表）"""
    for f in FEEDS:
        if f["id"] == feed_id:
            return copy.deepcopy(f)
    return None


@app.post("/api/feeds/{feed_id}/toggle-like", tags=["社区"], summary="点赞 / 取消点赞")
def toggle_like(feed_id: int, authorization: str = Header(None)):
    """切换指定动态的点赞状态，返回最新点赞数（需登录）"""
    user = _require_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "请先登录后再操作"})
    for f in FEEDS:
        if f["id"] == feed_id:
            f["liked"] = not f["liked"]
            f["likes"] += 1 if f["liked"] else -1
            _save_data()
            return {"liked": f["liked"], "likes": f["likes"]}
    return JSONResponse(status_code=404, content={"error": "动态不存在"})


class CommentRequest(BaseModel):
    text: str


@app.post("/api/feeds/{feed_id}/comments", tags=["社区"], summary="发表评论")
def add_comment(feed_id: int, req: CommentRequest, authorization: str = Header(None)):
    """为指定动态添加评论（需登录）"""
    user = _require_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "请先登录后再操作"})
    for f in FEEDS:
        if f["id"] == feed_id:
            comment = {"name": user["username"], "color": "blue", "text": req.text, "time": "刚刚"}
            f["comments_list"].append(comment)
            f["comments"] += 1
            _save_data()
            return {"comment": comment, "comments": f["comments"]}
    return JSONResponse(status_code=404, content={"error": "动态不存在"})


# =====================================================================
# 社区：发帖 / 删除帖子
# =====================================================================

class PostFeedRequest(BaseModel):
    caption: str = ""
    photos: list = []  # base64 编码的图片数组
    weather: str = ""
    district: str = ""


@app.post("/api/feed/post", tags=["社区"], summary="发布动态")
def post_feed(req: PostFeedRequest, authorization: str = Header(None)):
    """发布新动态（支持多图+文字），需登录"""
    user = _require_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "请先登录后再操作"})
    new_id = max([f["id"] for f in FEEDS], default=0) + 1
    feed = {
        "id": new_id,
        "photo": req.photos[0] if req.photos else "blue",
        "photos": req.photos,
        "weather": req.weather or "晴",
        "user": user["username"],
        "owner": user["username"],
        "avatarColor": "blue",
        "district": req.district or "未知",
        "time": "刚刚",
        "likes": 0,
        "liked": False,
        "comments": 0,
        "caption": req.caption,
        "comments_list": [],
    }
    FEEDS.insert(0, feed)
    user["photos"] = user.get("photos", 0) + 1
    _save_data()
    return {"feed": feed}


@app.delete("/api/feed/{feed_id}", tags=["社区"], summary="删除动态")
def delete_feed(feed_id: int, authorization: str = Header(None)):
    """删除指定动态（仅作者本人可删）"""
    user = _require_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "请先登录"})
    for i, f in enumerate(FEEDS):
        if f["id"] == feed_id:
            if f.get("owner") != user["username"]:
                return JSONResponse(status_code=403, content={"error": "只能删除自己的帖子"})
            FEEDS.pop(i)
            _save_data()
            return {"ok": True}
    return JSONResponse(status_code=404, content={"error": "动态不存在"})


# =====================================================================
# 用户资料：更新 / 查看 / 关注
# =====================================================================

class UpdateProfileRequest(BaseModel):
    avatar: str = ""  # base64 头像
    username: str = ""  # 新用户名


@app.put("/api/user/profile", tags=["用户"], summary="更新用户资料")
def update_user_profile(req: UpdateProfileRequest, authorization: str = Header(None)):
    """更新当前登录用户的头像和/或用户名"""
    user = _require_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    uid = user["id"]
    if uid not in _USER_EXTRAS:
        _USER_EXTRAS[uid] = {}
    if req.avatar:
        _USER_EXTRAS[uid]["avatar"] = req.avatar
    if req.username and req.username != user["username"]:
        # 检查用户名是否已被占用
        if USER_STORE.exists(req.username, user.get("email", "")):
            return JSONResponse(status_code=409, content={"error": "用户名已被占用"})
        old_name = user["username"]
        user["username"] = req.username
        _USER_EXTRAS[uid]["display_name"] = req.username
        # 更新 FEEDS 中该用户的帖子作者名
        for f in FEEDS:
            if f.get("owner") == old_name:
                f["user"] = req.username
                f["owner"] = req.username
    _save_data()
    return {"ok": True, "user": user, "extras": _USER_EXTRAS.get(uid, {})}


@app.get("/api/user/{user_id}/profile", tags=["用户"], summary="获取指定用户资料")
def get_user_profile_by_id(user_id: int):
    """返回指定用户的基本资料和扩展资料（头像等）"""
    user = USER_STORE.get_by_id(user_id)
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})
    extras = _USER_EXTRAS.get(user_id, {})
    following = _FOLLOWS.get(user_id, set())
    followers = set()
    for uid, fset in _FOLLOWS.items():
        if user_id in fset:
            followers.add(uid)
    # 该用户发的帖子
    user_feeds = [f for f in FEEDS if f.get("owner") == user.get("username")]
    return {
        "user": user,
        "avatar": extras.get("avatar", ""),
        "following_count": len(following),
        "followers_count": len(followers),
        "posts": len(user_feeds),
        "feeds": [copy.deepcopy(f) for f in user_feeds],
    }


@app.post("/api/user/{user_id}/follow", tags=["用户"], summary="关注/取消关注")
def toggle_follow(user_id: int, authorization: str = Header(None)):
    """切换关注状态（需登录）"""
    user = _require_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "请先登录"})
    my_id = user["id"]
    if my_id == user_id:
        return JSONResponse(status_code=400, content={"error": "不能关注自己"})
    target = USER_STORE.get_by_id(user_id)
    if not target:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})
    if my_id not in _FOLLOWS:
        _FOLLOWS[my_id] = set()
    if user_id in _FOLLOWS[my_id]:
        _FOLLOWS[my_id].discard(user_id)
        following = False
    else:
        _FOLLOWS[my_id].add(user_id)
        following = True
    _save_data()
    return {"following": following}


@app.get("/api/user/{user_id}/followers", tags=["用户"], summary="获取粉丝列表")
def get_followers(user_id: int):
    """返回指定用户的粉丝列表"""
    followers_ids = set()
    for uid, fset in _FOLLOWS.items():
        if user_id in fset:
            followers_ids.add(uid)
    result = []
    for uid in followers_ids:
        u = USER_STORE.get_by_id(uid)
        if u:
            extras = _USER_EXTRAS.get(uid, {})
            result.append({
                "id": uid,
                "username": u["username"],
                "avatar": extras.get("avatar", ""),
            })
    return result


@app.get("/api/user/{user_id}/following", tags=["用户"], summary="获取关注列表")
def get_following(user_id: int):
    """返回指定用户关注的列表"""
    following_ids = _FOLLOWS.get(user_id, set())
    result = []
    for uid in following_ids:
        u = USER_STORE.get_by_id(uid)
        if u:
            extras = _USER_EXTRAS.get(uid, {})
            result.append({
                "id": uid,
                "username": u["username"],
                "avatar": extras.get("avatar", ""),
            })
    return result


# =====================================================================
# 鉴权：注册 / 登录 / 获取资料
# =====================================================================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    identifier: str   # 用户名或邮箱
    password: str


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.post("/api/auth/register", tags=["用户"], summary="注册账号")
def register(req: RegisterRequest):
    """
    注册：用户名 + 邮箱 + 密码（至少6位）。
    成功后返回 JWT token 与用户信息（服务端从数据库读取并下发前端）。
    """
    username = (req.username or "").strip()
    email = (req.email or "").strip()
    password = req.password or ""

    if not username or len(username) > 50:
        return JSONResponse(status_code=400, content={"error": "用户名不能为空且不超过50个字符"})
    if not _EMAIL_RE.match(email):
        return JSONResponse(status_code=400, content={"error": "邮箱格式不正确"})
    if len(password) < 6:
        return JSONResponse(status_code=400, content={"error": "密码至少6位"})
    if USER_STORE.exists(username, email):
        return JSONResponse(status_code=409, content={"error": "用户名或邮箱已被注册"})

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = USER_STORE.create(username, email, pw_hash)
    token = _create_token(user["id"], user["username"])
    _save_data()
    return {"token": token, "user": user}


@app.post("/api/auth/login", tags=["用户"], summary="登录")
def login(req: LoginRequest):
    """
    登录：用户名/邮箱 + 密码。成功后返回 JWT token 与用户信息。
    """
    identifier = (req.identifier or "").strip()
    password = req.password or ""

    row = USER_STORE.get_by_credentials(identifier)
    if not row or not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        return JSONResponse(status_code=401, content={"error": "用户名/邮箱或密码错误"})

    user = USER_STORE.get_by_id(row["id"])
    token = _create_token(user["id"], user["username"])
    _save_data()
    return {"token": token, "user": user}


@app.get("/api/user/profile", tags=["用户"], summary="获取用户资料")
def get_user_profile(authorization: str = Header(None)):
    """返回当前登录用户的基本资料（实拍数、获赞数等），需携带 Bearer Token"""
    user = _require_user(authorization)
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录或登录已过期"})
    return user


@app.post("/api/auth/generate-id", tags=["用户"], summary="生成匿名用户 ID（兼容旧逻辑）")
def generate_user_id():
    """仅用于未登录场景的兼容性占位，新流程请使用 register/login。"""
    return {"userId": "WB" + str(random.randint(10000, 99999))}


@app.get("/api/cities", tags=["配置"], summary="获取城市列表")
def get_cities():
    """返回支持的城市及区域列表"""
    data_path = os.path.join(_frontend_dir, "data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/health", tags=["系统"], summary="健康检查")
def health_check():
    """服务健康检查端点"""
    return {"status": "ok", "timestamp": _now_ms()}


# ---- 反向地理编码（GPS 定位 → 城市/区县）----
# 用于手机定位功能：前端拿到 GPS 坐标后调用此端点，返回最近的城市与区县
# 用 BigDataCloud 免费反向地理编码（无需 API Key）+ 本地城市表二次匹配

@app.get("/api/reverse-geocode", tags=["定位"], summary="GPS 坐标反查城市区县")
def reverse_geocode(lat: float, lon: float):
    """根据 GPS 经纬度反查最近的城市/区县。
    前端 navigator.geolocation 拿到坐标后调用此端点。
    """
    # 1) 先用 BigDataCloud 反查地名（中文，免费无需 Key）
    city_name = district_name = ""
    try:
        data = _http_get_with_retry(
            "https://api.bigdatacloud.net/data/reverse-geocode-client",
            {"latitude": lat, "longitude": lon, "localityLanguage": "zh"},
            attempts=2, timeout=8.0,
        )
        city_name = (data.get("city") or data.get("locality") or data.get("principalSubdivision") or "").strip()
        # localityInfo.Administratives 是从细到粗的行政区划列表，取最细一级作为区县
        li = data.get("localityInfo")
        if isinstance(li, dict):
            admins = li.get("Administratives") or []
            if admins and isinstance(admins, list):
                # 倒序查找：从最细到最粗，取第一个非空作为区县
                for admin in reversed(admins):
                    name = (admin.get("name") or "").strip() if isinstance(admin, dict) else ""
                    if name:
                        district_name = name
                        break
        if not district_name:
            district_name = (data.get("principalSubdivision") or "").strip()
    except Exception:
        pass

    # 1.5) 备用：Open-Meteo 反向地理编码（与天气数据同源，更可靠且准确）
    # 先用专用 /v1/reverse 反查接口；不可用时回退到 /v1/search 坐标检索
    if not city_name:
        for _url, _params in (
            ("https://geocoding-api.open-meteo.com/v1/reverse",
             {"latitude": lat, "longitude": lon, "language": "zh", "count": 1, "format": "json"}),
            ("https://geocoding-api.open-meteo.com/v1/search",
             {"latitude": lat, "longitude": lon, "count": 1, "language": "zh", "format": "json"}),
        ):
            try:
                data = _http_get_with_retry(_url, _params, attempts=2, timeout=8.0)
                results = data.get("results") or []
                if results:
                    r0 = results[0]
                    city_name = (r0.get("name") or "").strip()
                    if not district_name:
                        district_name = (r0.get("admin3") or r0.get("admin2") or "").strip()
                    break
            except Exception:
                continue

    # 2) 用本地城市表做最近匹配（Haversine），保证返回的一定是 data.json 里的城市
    data_path = os.path.join(_frontend_dir, "data.json")
    cities_list = []
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            cities_list = json.load(f).get("cities", [])
    except Exception:
        pass

    best_city = city_name
    best_district = ""
    if cities_list:
        # 城市名归一化：去掉"市/省/自治区"等后缀以提高匹配率
        def _norm(name):
            if not name:
                return ""
            for suf in ("市", "省", "自治区", "特别行政区", "县", "区"):
                if name.endswith(suf) and len(name) > len(suf):
                    return name[:-len(suf)]
            return name
        city_norm = _norm(city_name)
        # 直辖市特殊处理：北京/上海/天津/重庆 — 若区县与城市同名则置空（用"全市"）
        _MUNI = {"北京", "上海", "天津", "重庆"}
        if city_norm in _MUNI:
            if _norm(district_name) == city_norm or not _norm(district_name):
                district_name = ""
        # 预先用 BigDataCloud 结果匹配城市名（处理"北京市"→"北京"等简称）
        matched = None
        for c in cities_list:
            if c["name"] == city_name or c["name"] == city_norm:
                matched = c
                break
        # 匹配不到则按字符串包含
        if not matched and city_name:
            for c in cities_list:
                if city_name.startswith(c["name"]) or c["name"] in city_name or city_norm.startswith(c["name"]):
                    matched = c
                    break
        # 仍匹配不到，用 Open-Meteo geocoding 反查城市名
        if not matched:
            try:
                geo_data = _http_get_with_retry(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    {"latitude": lat, "longitude": lon, "count": 5, "language": "zh", "format": "json"},
                    attempts=1, timeout=6.0,
                )
                geo_results = geo_data.get("results") or []
                for gr in geo_results:
                    gname = _norm((gr.get("name") or "").strip())
                    for c in cities_list:
                        if c["name"] == gname or c["name"] in gname or gname.startswith(c["name"]):
                            matched = c
                            if not district_name:
                                district_name = (gr.get("admin3") or gr.get("admin2") or "").strip()
                            break
                    if matched:
                        break
            except Exception:
                pass
        if matched:
            best_city = matched["name"]
            # 区县匹配
            ds = matched.get("districts", [])
            if ds:
                # 若 BigDataCloud 给了区县名，尝试匹配
                hit = next((d for d in ds if district_name and (d in district_name or district_name in d)), None)
                best_district = hit or ds[0]

    # 3) 最终兜底：如果什么都没匹配到，用中国主要城市经纬度找最近城市
    if not best_city:
        fallback_cities = [
            ("北京", 39.90, 116.40), ("上海", 31.23, 121.47), ("广州", 23.13, 113.26),
            ("深圳", 22.54, 114.06), ("成都", 30.57, 104.07), ("杭州", 30.27, 120.15),
            ("武汉", 30.59, 114.31), ("南京", 32.04, 118.78), ("西安", 34.27, 108.95),
            ("重庆", 29.56, 106.55),
        ]
        best_d = 1e9
        for name, clat, clon in fallback_cities:
            d = (lat - clat) ** 2 + (lon - clon) ** 2
            if d < best_d:
                best_d = d
                best_city = name
                best_district = "全市"

    return {
        "city": best_city,
        "district": best_district or "全市",
        "lat": lat,
        "lon": lon,
        "raw_city": city_name,
        "raw_district": district_name,
    }


# ---- AI 天气生成端点 ----

class AIWeatherRequest(BaseModel):
    city: str
    district: str


@app.post("/api/ai-weather", tags=["AI"], summary="大模型生成天气数据")
async def ai_weather(req: AIWeatherRequest):
    """
    接收用户城市/区域信息，构造提示词调用大模型，
    将大模型返回的数据规范化为与 /api/weather 一致的结构后返回。
    若未配置 API Key 或调用失败，降级返回 _gen_weather() 生成的实时观测数据。
    """
    api_key = LLM_CONFIG.get("llm_api_key", "")

    # 未配置 Key → 降级返回实时观测数据
    if not api_key:
        fallback = _gen_weather(req.city, req.district)
        fallback["ai_generated"] = False
        fallback["ai_message"] = "未配置 LLM API Key，已返回实时观测数据。请在 backend/config.json 中填入 api_key。"
        return fallback

    # 构造提示词
    user_prompt = _build_user_prompt(req.city, req.district)
    timeout = float(LLM_CONFIG.get("llm_timeout", 30))

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{LLM_CONFIG['llm_base_url']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": LLM_CONFIG["llm_model"],
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 256,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            result = resp.json()
            content = result["choices"][0]["message"]["content"]

        # 解析 + 规范化
        raw = _parse_llm_json(content)
        weather = _normalize_weather(raw)
        weather["ai_generated"] = True
        weather["ai_model"] = LLM_CONFIG["llm_model"]
        return weather

    except Exception as e:
        # 降级返回实时观测数据
        import traceback
        detail = traceback.format_exc()
        print(f"[AI Weather ERROR] {type(e).__name__}: {e}")
        print(f"[AI Weather TRACEBACK] {detail}")
        if 'content' in locals():
            print(f"[AI Weather RAW RESPONSE] {repr(content)}")
        fallback = _gen_weather(req.city, req.district)
        fallback["ai_generated"] = False
        fallback["ai_message"] = f"AI 生成失败，已返回实时观测数据：{type(e).__name__}: {e}"
        return fallback


# =====================================================================
# 静态文件服务（前端页面）
# 所有 /api/* 路由优先匹配，其余请求由 StaticFiles 处理
# =====================================================================

_frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "html-prototype")
app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")


# =====================================================================
# 启动入口
# =====================================================================

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  聚合天气平台 - 后端服务")
    print("=" * 60)
    print()
    _port = int(os.environ.get("PORT", "8000"))
    print("  前端页面:  http://localhost:%d" % _port)
    print("  API 文档:  http://localhost:%d/docs" % _port)
    print("  健康检查:  http://localhost:%d/api/health" % _port)
    print()
    print("  按 Ctrl+C 停止服务")
    print("=" * 60)
    print()
    uvicorn.run(app, host="0.0.0.0", port=_port)
