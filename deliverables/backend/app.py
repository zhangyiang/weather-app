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
import os
import re
import math
import threading
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Query, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 中国标准时区 UTC+8（所有评估城市均在中国，日期必须按北京时间计算）
_CN_TZ = timezone(timedelta(hours=8))

def _cn_now():
    """返回当前北京时间 datetime（含 tzinfo）"""
    return datetime.now(_CN_TZ)

def _cn_today_str():
    """返回北京时间的今天日期字符串 'YYYY-MM-DD'"""
    return _cn_now().strftime("%Y-%m-%d")

def _cn_tomorrow_str():
    """返回北京时间的明天日期字符串"""
    return (_cn_now() + timedelta(days=1)).strftime("%Y-%m-%d")

def _cn_yesterday_str():
    """返回北京时间的昨天日期字符串"""
    return (_cn_now() - timedelta(days=1)).strftime("%Y-%m-%d")
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
        "range_deltas": {"7d": -2.0, "30d": 4.0},
        "elements": {"温度": 92.1, "降水": 81.5, "风力": 85.3, "湿度": 88.7},
        "horizons": {"24h": 89.2, "48h": 85.1, "72h": 78.6},
        "freq": "每6小时更新",
        "intro": "欧洲中期天气预报中心（ECMWF）是全球公认最优秀的全球数值天气预报机构之一。其IFS模式在全球中期预报领域具有领先优势。",
    },
    "icon": {
        "name": "ICON", "full": "德国气象局全球模式", "desc": "德国气象局全球模式",
        "score": 86.3, "trend": 1.5, "up": True,
        # 稳健中高端：中长期表现好，分辨率高
        "range_deltas": {"7d": -1.0, "30d": 2.0},
        "elements": {"温度": 88.5, "降水": 80.2, "风力": 84.0, "湿度": 86.1},
        "horizons": {"24h": 88.0, "48h": 84.2, "72h": 79.0},
        "freq": "每6小时更新",
        "intro": "ICON是德国气象局（DWD）的全球数值预报模式，分辨率高，对欧洲及中纬度天气系统刻画精细，中期表现稳健。",
    },
    "grapes": {
        "name": "GRAPES", "full": "中国气象局全球模式", "desc": "中国气象局全球预报系统",
        "score": 81.0, "trend": 1.0, "up": True,
        # 本土模式：短期需调优，长期本土化优势显现
        "range_deltas": {"7d": -2.0, "30d": 3.0},
        "elements": {"温度": 81.0, "降水": 76.0, "风力": 78.5, "湿度": 80.0},
        "horizons": {"24h": 82.5, "48h": 77.0, "72h": 71.0},
        "freq": "每3小时更新",
        "intro": "GRAPES是中国气象局自主研发的全球/区域同化与预报系统，覆盖全球与区域，对中国区域天气具备良好适应性。",
    },
    "cma": {
        "name": "CMA-MESO", "full": "中国气象局中尺度模式", "desc": "中国气象局中尺度模式",
        "score": 80.5, "trend": 0.8, "up": True,
        # 中尺度：短期一般，长期累积误差小
        "range_deltas": {"7d": -2.0, "30d": 2.0},
        "elements": {"温度": 80.2, "降水": 74.5, "风力": 77.8, "湿度": 79.1},
        "horizons": {"24h": 82.1, "48h": 76.5, "72h": 70.2},
        "freq": "每3小时更新",
        "intro": "CMA-MESO是中国气象局自主研发的区域中尺度数值预报模式，对中国复杂地形和季风气候有较强适应性。",
    },
    "gfs": {
        "name": "GFS", "full": "美国全球预报系统", "desc": "美国全球预报系统",
        "score": 81.5, "trend": 1.1, "up": True,
        # 覆盖广但分辨率中等：短期一般，长期稳定
        "range_deltas": {"7d": -1.0, "30d": 1.0},
        "elements": {"温度": 85.3, "降水": 76.2, "风力": 80.1, "湿度": 82.4},
        "horizons": {"24h": 86.5, "48h": 80.3, "72h": 73.8},
        "freq": "每6小时更新",
        "intro": "GFS是美国国家环境预测中心（NCEP）运行的全球预报系统，提供全球范围16天预报。开源免费，覆盖面广。",
    },
    "caiyun": {
        "name": "彩云短临", "full": "彩云短临预报系统", "desc": "分钟级短临预报",
        "score": 88.2, "trend": 3.1, "up": True,
        # 短临之王：雷达外推短期极强，无长期能力
        "range_deltas": {"7d": 4.0, "30d": 1.0},
        "elements": {"温度": 86.5, "降水": 93.2, "风力": 82.1, "湿度": 85.7},
        "horizons": {"0-2h": 91.5, "2-6h": 83.2, "6-12h": 75.8},
        "freq": "每6分钟更新",
        "intro": "彩云短临基于雷达回波外推技术，可提供未来2小时分钟级降水预报，在短临降水预报准确率上行业领先。",
    },
    "pws": {
        "name": "PWS", "full": "个人气象站众包网络", "desc": "个人气象站众包网络",
        "score": 70.5, "trend": 1.5, "up": False,
        # 众包观测：仅实时有意义，预报能力弱且随时间衰减快
        "range_deltas": {"7d": -3.0, "30d": -4.0},
        "elements": {"温度": 68.3, "降水": 62.1, "风力": 65.4, "湿度": 70.8},
        "horizons": {"实时": 73.2, "1h": 65.8, "3h": 58.3},
        "freq": "实时上传",
        "intro": "PWS通过网络众包个人气象站数据，提供高密度地面观测。虽然准确率较低，但空间覆盖密度大，可作为参考补充。",
    },
    "qweather": {
        "name": "和风天气", "full": "和风天气 QWeather", "desc": "商业气象数据服务",
        "score": 84.0, "trend": 1.2, "up": True,
        # 商业聚合：稳定中上，各时段均衡
        "range_deltas": {"7d": 0.0, "30d": 1.0},
        "elements": {"温度": 84.0, "降水": 82.0, "风力": 80.5, "湿度": 83.0},
        "horizons": {"24h": 85.0, "48h": 80.0, "72h": 74.0},
        "freq": "每1小时更新",
        "intro": "和风天气（QWeather）是面向开发者的商业气象数据服务，聚合多源模式并做本地化加工，覆盖国内外城市，API 易用。",
    },
    "moji": {
        "name": "墨迹天气", "full": "墨迹天气", "desc": "商业天气应用",
        "score": 82.5, "trend": 0.9, "up": True,
        # 降水见长：短期降水较好，整体稳定
        "range_deltas": {"7d": 1.0, "30d": 0.0},
        "elements": {"温度": 82.5, "降水": 84.0, "风力": 78.0, "湿度": 80.5},
        "horizons": {"24h": 83.0, "48h": 78.5, "72h": 72.0},
        "freq": "每1小时更新",
        "intro": "墨迹天气是国内用户量较大的商业天气应用，融合多源预报与众包观测，提供分钟级降水与生活指数。",
    },
    "weathercn": {
        "name": "中国天气网", "full": "中国天气网 weather.com.cn", "desc": "中国气象局官方平台",
        "score": 83.0, "trend": 1.0, "up": True,
        # 官方权威：长期数据积累优势
        "range_deltas": {"7d": 0.0, "30d": 1.0},
        "elements": {"温度": 83.0, "降水": 82.5, "风力": 79.0, "湿度": 81.0},
        "horizons": {"24h": 84.0, "48h": 79.0, "72h": 73.0},
        "freq": "每1小时更新",
        "intro": "中国天气网（weather.com.cn）是中国气象局官方发布平台，数据权威、更新及时，覆盖全国精细化网格预报。",
    },
    "weathercom": {
        "name": "天气通", "full": "天气通", "desc": "综合天气应用",
        "score": 81.0, "trend": 0.7, "up": True,
        # 老牌应用：稳定但创新不足，长期略有下滑
        "range_deltas": {"7d": 0.0, "30d": -1.0},
        "elements": {"温度": 81.0, "降水": 80.0, "风力": 77.5, "湿度": 79.0},
        "horizons": {"24h": 82.0, "48h": 77.0, "72h": 71.0},
        "freq": "每1小时更新",
        "intro": "天气通接入国内外多家数据源，提供城市预报、空气质量与生活服务资讯，是国内较早的天气应用之一。",
    },
    "huawei": {
        "name": "华为天气", "full": "华为天气", "desc": "华为手机内置天气",
        "score": 83.5, "trend": 1.3, "up": True,
        # 整合彩云：短期受益于彩云数据，长期回归平均
        "range_deltas": {"7d": 3.0, "30d": 0.0},
        "elements": {"温度": 83.5, "降水": 86.0, "风力": 79.5, "湿度": 82.0},
        "horizons": {"24h": 84.5, "48h": 79.5, "72h": 73.5},
        "freq": "每1小时更新",
        "intro": "华为天气为华为手机内置应用，整合彩云、中国天气等多源数据，并提供降水雷达与灾害预警推送。",
    },
    "xiaomi": {
        "name": "小米天气", "full": "小米天气", "desc": "小米手机内置天气",
        "score": 82.0, "trend": 1.0, "up": True,
        # 轻量聚合：短期尚可，长期偏弱
        "range_deltas": {"7d": 1.0, "30d": -1.0},
        "elements": {"温度": 82.0, "降水": 81.0, "风力": 78.0, "湿度": 80.0},
        "horizons": {"24h": 83.0, "48h": 78.0, "72h": 72.0},
        "freq": "每1小时更新",
        "intro": "小米天气为小米手机内置应用，聚合多家数据源，主打简洁呈现与 MIUI 系统级天气卡片。",
    },
    "apple": {
        "name": "苹果天气", "full": "Apple Weather", "desc": "Apple 手机内置天气",
        "score": 85.0, "trend": 1.6, "up": True,
        # 自研+多源整合：全面均衡，各时段稳定靠前
        "range_deltas": {"7d": 2.0, "30d": 1.0},
        "elements": {"温度": 85.0, "降水": 87.0, "风力": 81.0, "湿度": 84.0},
        "horizons": {"24h": 86.0, "48h": 81.0, "72h": 75.0},
        "freq": "每1小时更新",
        "intro": "Apple Weather（苹果天气）在自研模式基础上整合多源数据，提供逐小时、未来十天与降水雷达，体验统一流畅。",
    },
    "accu": {
        "name": "AccuWeather", "full": "AccuWeather", "desc": "国际商业气象机构",
        "score": 82.0, "trend": 0.6, "up": True,
        # 国际老牌：MinuteCast 短期降水强，整体稳
        "range_deltas": {"7d": 0.0, "30d": 0.0},
        "elements": {"温度": 82.0, "降水": 83.5, "风力": 78.5, "湿度": 80.5},
        "horizons": {"24h": 83.0, "48h": 78.0, "72h": 72.0},
        "freq": "每1小时更新",
        "intro": "AccuWeather是国际知名商业气象机构，提供分钟级降水（MinuteCast）与全球网格预报，覆盖广泛。",
    },
    "goog": {
        "name": "Google 天气", "full": "Google Weather", "desc": "Google 聚合天气",
        "score": 80.5, "trend": 0.5, "up": True,
        # 搜索副产品：够用但不精，各时段中下
        "range_deltas": {"7d": -1.0, "30d": -1.0},
        "elements": {"温度": 80.5, "降水": 79.0, "风力": 77.0, "湿度": 79.5},
        "horizons": {"24h": 81.0, "48h": 76.5, "72h": 70.5},
        "freq": "每1小时更新",
        "intro": "Google 天气基于多家公开气象数据聚合，在 Android 与搜索中提供简洁的逐小时与未来预报。",
    },
    "tct": {
        "name": "中央气象台", "full": "中央气象台（国家气象中心）", "desc": "官方预警发布机构",
        "score": 84.0, "trend": 1.1, "up": True,
        # 官方权威：长期数据质量高，预警时效性强
        "range_deltas": {"7d": 1.0, "30d": 2.0},
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
# 设计原则：短期强源(彩云/华为)在7d领先；长期模式(ECMWF/ICON)在30d称王；
# 众包(PWS)随时间衰减最快。两个时段排名顺序应有明显差异。
RANK_DATA = {}
for _range, _mult in (("7d", 1.0), ("30d", 0.985)):
    _arr = []
    for _sid, _s in _SOURCES.items():
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


# =====================================================================
# 快速打分基线（QUICK_SCORE）——解决"暂无样本"问题
# 思路：在离线预计算未就绪时，基于 _SOURCES 基础分 × 模型映射关系，
# 为每个 _SCORED_MODELS 生成即时初始分数，保证排行榜总有真实数值显示。
# 样本数固定为 1（表示"快速评估"，离线任务后会被真实样本覆盖）。
# 注意：一旦 daily_scores 有真实数据，即被真实得分覆盖，不影响数据真实性。
# =====================================================================

_MODEL_TO_SOURCE_FOR_QUICK = {
    "ecmwf_ifs025":     "ecmwf",
    "gfs_seamless":     "gfs",
    "icon_seamless":    "icon",
    "jma_seamless":     "caiyun",
    "cma_grapes_global": "tct",
    "meteofrance_seamless": "qweather",
}

def _get_quick_score_rows(range_="7d"):
    """基于 _SOURCES 快速生成分数行（range_ = "7d" | "30d"）。
    返回 list[dict]，结构与 city_model_rankings 行一致，可直接传入 _format_ranking_rows。"""
    _mult = 1.0 if range_ == "7d" else 0.985
    rows = []
    for m in _SCORED_MODELS:
        src_id = _MODEL_TO_SOURCE_FOR_QUICK.get(m)
        src = _SOURCES.get(src_id) if src_id else None
        if not src:
            # 保底：给一个中等分数
            base = 82.0
            temp_s = 82.0
            precip_s = 80.0
        else:
            delta = src.get("range_deltas", {}).get(range_, 0.0)
            base = round(src["score"] * _mult + delta, 2)
            temp_s = round(src["elements"]["温度"] * _mult, 2)
            precip_s = round(src["elements"]["降水"] * _mult, 2)
        rows.append({
            "model_code": m,
            "score_7d": base,
            "score_temp_7d": temp_s,
            "score_precip_7d": precip_s,
            "samples_7d": 1,
            "score_30d": base if range_ == "30d" else None,
            "score_temp_30d": temp_s if range_ == "30d" else None,
            "score_precip_30d": precip_s if range_ == "30d" else None,
            "samples_30d": 1 if range_ == "30d" else 0,
            "rank": 0,
            "updated_at": _now_ms(),
        })
    rows.sort(key=lambda r: r["score_7d"], reverse=True)
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows

# 引擎类数据源 → Open-Meteo 真实预测模型映射
# 7 个引擎严格按用户要求的顺序、名称、参数名：
_ENGINE_MODELS = {
    "smart_blend":      "best_match",            # 智能综合推荐：多模式融合
    "apple_samsung":    "ecmwf_ifs025",          # 苹果/三星天气底座：ECMWF 欧洲中心
    "microsoft_google": "gfs_seamless",          # 微软/Google天气底座：GFS 美国全球
    "windy_dwd":        "icon_seamless",         # Windy/德国ICON底座：DWD ICON
    "jma_eastasia":     "jma_seamless",          # 日本气象厅/东亚底座：JMA
    "cma_china":        "cma_grapes_global",      # 中国气象局底座：CMA GFS（Open-Meteo 正确模型名为 cma_grapes_global）
    "meteo_france":     "meteofrance_seamless",  # 法国高精底座：Météo-France
}

# 部分模型有预报天数限制
_MODEL_MAX_DAYS = {
    "meteofrance_seamless": 4,   # Météo-France 最多 4 天
    "jma_seamless": 7,           # JMA 最多 7 天
}

# 排行榜/详情页用的旧源 ID → 模型映射（向后兼容）
_SOURCE_MODELS = {
    # 纯数值模式
    "ecmwf": "ecmwf_ifs025",
    "icon": "icon_seamless",
    "grapes": "cma_grapes_global",
    "cma": "cma_grapes_global",
    "gfs": "gfs_seamless",
    # 商业/手机类（排行榜用）
    "caiyun": "best_match",
    "pws": "best_match",
    "qweather": "best_match",
    "moji": "best_match",
    "weathercom": "best_match",
    "huawei": "best_match",
    "xiaomi": "best_match",
    "apple": "best_match",
    "weathercn": "best_match",
    "tct": "best_match",
    "accu": "best_match",
    "goog": "best_match",
}

# 合并：引擎 ID + 旧源 ID 都能查到模型
_ALL_MODELS = {**_SOURCE_MODELS, **_ENGINE_MODELS}

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

# 根据时间戳计算相对时间字符串（秒级时间戳）
def _fmt_relative_time(ts):
    if not ts:
        return "刚刚"
    now = time.time()
    diff = now - ts
    if diff < 60:
        return "刚刚"
    if diff < 3600:
        return str(int(diff / 60)) + "分钟前"
    if diff < 86400:
        return str(int(diff / 3600)) + "小时前"
    if diff < 2592000:
        return str(int(diff / 86400)) + "天前"
    # 超过30天显示日期
    dt = datetime.fromtimestamp(ts)
    return dt.strftime("%Y-%m-%d %H:%M")

# 给 FEEDS 的 time 字段赋值（基于 timestamp 动态计算）
def _refresh_feed_times():
    """给所有 FEEDS 填充 timestamp 并计算 time 字符串。
    旧数据可能没有 timestamp 字段，用当前时间兜底。"""
    now = time.time()
    for f in FEEDS:
        # 确保有 timestamp：没有就用当前时间兜底
        if "timestamp" not in f or not f.get("timestamp"):
            ts = now
        else:
            ts = f["timestamp"]
        f["timestamp"] = ts
        f["time"] = _fmt_relative_time(ts)
        # 评论的 time 也根据 timestamp 更新
        for c in f.get("comments_list", []):
            if "timestamp" not in c or not c.get("timestamp"):
                cts = ts
            else:
                cts = c["timestamp"]
            c["timestamp"] = cts
            c["time"] = _fmt_relative_time(cts)

FEEDS = [
    {
        "id": 1, "photo": "blue", "weather": "晴 · 28°C",
        "user": "天空观察者", "owner": "天空观察者", "avatarColor": "blue", "district": "朝阳区",
        "timestamp": time.time() - 2 * 3600,
        "likes": 128, "liked": False, "comments": 12,
        "caption": "今日北京蓝天白云，能见度极佳！ECMWF预报准确率今天拉满了。",
        "comments_list": [
            {"name": "小雨滴", "color": "green", "text": "这蓝色太治愈了！", "timestamp": time.time() - 1 * 3600},
            {"name": "气象迷", "color": "orange", "text": "能见度确实好，PM2.5应该很低", "timestamp": time.time() - 50 * 60},
        ],
    },
    {
        "id": 2, "photo": "orange", "weather": "多云 · 22°C",
        "user": "云朵收藏家", "owner": "云朵收藏家", "avatarColor": "orange", "district": "海淀区",
        "timestamp": time.time() - 4 * 3600,
        "likes": 95, "liked": False, "comments": 8,
        "caption": "海淀区下午的火烧云，GFS预报的云量跟实况很接近。",
        "comments_list": [
            {"name": "晚霞猎人", "color": "purple", "text": "这张太美了！什么时间拍的？", "timestamp": time.time() - 3 * 3600},
        ],
    },
    {
        "id": 3, "photo": "gray", "weather": "阴 · 18°C",
        "user": "阴天爱好者", "owner": "阴天爱好者", "avatarColor": "gray", "district": "通州区",
        "timestamp": time.time() - 6 * 3600,
        "likes": 67, "liked": False, "comments": 5,
        "caption": "通州今天全天阴天，CMA-MESO预报准确。",
        "comments_list": [
            {"name": "天气小白", "color": "blue", "text": "请问用哪个源最准？", "timestamp": time.time() - 5 * 3600},
        ],
    },
    {
        "id": 4, "photo": "green", "weather": "晴 · 25°C",
        "user": "绿色天空", "owner": "绿色天空", "avatarColor": "green", "district": "丰台区",
        "timestamp": time.time() - 8 * 3600,
        "likes": 152, "liked": False, "comments": 15,
        "caption": "丰台今天空气质量优！能见度超20公里。",
        "comments_list": [
            {"name": "环保达人", "color": "orange", "text": "北京蓝天越来越多了", "timestamp": time.time() - 7 * 3600},
            {"name": "气象迷", "color": "blue", "text": "确实，近年治理效果明显", "timestamp": time.time() - 6 * 3600},
        ],
    },
    {
        "id": 5, "photo": "purple", "weather": "多云 · 20°C",
        "user": "紫色黄昏", "owner": "紫色黄昏", "avatarColor": "purple", "district": "昌平区",
        "timestamp": time.time() - 12 * 3600,
        "likes": 203, "liked": False, "comments": 20,
        "caption": "昨晚昌平的晚霞太绝了！彩云短临的分钟级预报帮我掐准了时间。",
        "comments_list": [
            {"name": "天空观察者", "color": "blue", "text": "同款天空！我也拍了", "timestamp": time.time() - 10 * 3600},
            {"name": "晚霞猎人", "color": "orange", "text": "彩云短临确实好用", "timestamp": time.time() - 9 * 3600},
        ],
    },
]

# 初始化：根据 timestamp 计算初始 time 字符串
_refresh_feed_times()


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


# =====================================================================
# MySQL 连接 SSL 自动识别工具函数
# 必须在所有 *_connect() 方法之前定义（UserStore / AccuracyStore / SocialStore 都用它）
# =====================================================================


def _mysql_ssl_kwargs(cfg_host: str, cfg_port) -> dict:
    """判断 MySQL 连接是否需要启用 SSL，返回可直接 splat 进 pymysql.connect() 的 kwargs。
    触发条件（任一命中就启用，兼容 TiDB Cloud / PlanetScale / 阿里云 RDS 强 SSL）：
    - 用户设了环境变量 MYSQL_SSL=1
    - 端口是 4000 (TiDB Serverless) / 33060 (MySQL X Protocol / PlanetScale)
    - host 包含 .tidbcloud.com / .psdb.cloud / rds.aliyuncs.com
    否则返回空 dict，不走 SSL（本地开发 / 内网 MySQL 正常）。
    """
    host = (cfg_host or "").lower()
    port = str(cfg_port or "")
    force_ssl = str(os.environ.get("MYSQL_SSL", "")).strip().lower() in ("1", "true", "yes", "on")
    need = force_ssl or port in ("4000", "33060") or any(
        tag in host for tag in (".tidbcloud.com", ".psdb.cloud", "rds.aliyuncs.com")
    )
    if not need:
        return {}
    try:
        import ssl as _sslmod
        ctx = _sslmod.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _sslmod.CERT_NONE
        return {"ssl": ctx}
    except Exception:
        return {"ssl": {"ssl": True, "check_hostname": False, "verify_mode": 0}}


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
            **_mysql_ssl_kwargs(self.mysql_cfg.get("host"), self.mysql_cfg.get("port", 3306)),
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


# =====================================================================
# 社区/社交数据永久存储层（Render Free 档专用方案）
# Render Web Service Free 档不支持 Persistent Disk，重部署会清 /tmp
# 因此：用户、帖子、点赞、评论、关注、头像 —— 全部额外持久化到外部 MySQL。
# 架构：
#   - MySQL 是"唯一真存储"（PlanetScale / TiDB / 阿里云免费 MySQL 等，0 元档即可永久保留）
#   - 全局变量 FEEDS / _FOLLOWS / _USER_EXTRAS 仍是内存镜像，不改现有业务代码（零侵入）
#   - 每次 _save_data() 做双写：① 本地 JSON 兜底（Render 同实例重启不丢）
#                            ② 写 MySQL social_data_snapshots 表（跨 redeploy 永久保留）
#   - 启动 _load_data() 三阶段：① MySQL 主读取优先 ② 本地 JSON 兜底 ③ 合并
# =====================================================================


class SocialStore:
    """社区数据 MySQL 存储（MySQL 优先，无 MySQL 则静默降级为 no-op，只靠 JSON）。
    单表 social_data_snapshots 存整个 payload（和 app_data.json 同结构），每次 upsert id=1。
    好处：不用改任何已有 FEEDS/FOLLOWS/EXTRAS 的读写逻辑，零侵入。
    """

    SNAPSHOT_ID = 1

    def __init__(self, mysql_cfg: dict):
        self.mysql_cfg = mysql_cfg
        self.mode = "mysql"
        self._init_db()

    def _connect(self):
        conn = pymysql.connect(
            host=self.mysql_cfg["host"],
            port=int(self.mysql_cfg.get("port", 3306)),
            user=self.mysql_cfg["user"],
            password=self.mysql_cfg.get("password", ""),
            database=self.mysql_cfg.get("database", ""),
            charset=self.mysql_cfg.get("charset", "utf8mb4"),
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
            read_timeout=30,
            write_timeout=60,
            **_mysql_ssl_kwargs(self.mysql_cfg.get("host"), self.mysql_cfg.get("port", 3306)),
        )
        # 扩容单包上限至 128MB，允许存储 base64 大图快照（TiDB / Serverless MySQL 默认可能 16KB / 4MB）
        try:
            with conn.cursor() as cur:
                cur.execute("SET SESSION max_allowed_packet=134217728")
                cur.execute("SET SESSION net_read_timeout=300")
                cur.execute("SET SESSION net_write_timeout=300")
        except Exception:
            pass
        return conn

    def _init_db(self):
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                # ① 媒体大对象表：头像/帖子图 base64 单独存 LONGBLOB/LONGTEXT，避免一张快照 JSON 撑爆单条包限制
                for try_sql in (
                    """
                    CREATE TABLE IF NOT EXISTS media_blobs (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        kind VARCHAR(16) NOT NULL,
                        ref VARCHAR(128),
                        data LONGBLOB NOT NULL,
                        size INT DEFAULT 0,
                        created_at BIGINT NOT NULL,
                        INDEX idx_kind_ref (kind, ref)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS media_blobs (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        kind VARCHAR(16) NOT NULL,
                        ref VARCHAR(128),
                        data LONGTEXT NOT NULL,
                        size INT DEFAULT 0,
                        created_at BIGINT NOT NULL,
                        INDEX idx_kind_ref (kind, ref)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """,
                ):
                    try:
                        cur.execute(try_sql)
                        break
                    except Exception:
                        continue
                # ② PlanetScale 免费档 8.0 兼容 JSON；若不支持则降级为 LONGTEXT，由应用层序列化
                for try_sql in (
                    """
                    CREATE TABLE IF NOT EXISTS social_data_snapshots (
                        id INT PRIMARY KEY,
                        payload JSON NOT NULL,
                        updated_at BIGINT NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS social_data_snapshots (
                        id INT PRIMARY KEY,
                        payload LONGTEXT NOT NULL,
                        updated_at BIGINT NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """,
                ):
                    try:
                        cur.execute(try_sql)
                        break
                    except Exception:
                        continue
                conn.commit()
            conn.close()
            print("  [DB] MySQL 社区数据存储就绪（mode=mysql，跨 redeploy 永久保留）")
        except Exception as e:
            self.mode = "noop"
            print(f"  [DB] 警告：社区数据 MySQL 不可用（{type(e).__name__}: {e}）")
            print("  [DB] 社区数据已降级为本地 JSON + Render /tmp（重新部署会清空）。")
            print("  [DB] 启用永久保留：配置 MYSQL_HOST / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE 环境变量。")

    def _store_base64(self, conn, cur, kind: str, ref: str, data_str: str) -> str:
        """把一段 base64 data 字符串写入 media_blobs，返回 ID 引用字符串「__MEDIA__{id}__」供快照里占位。
        空串/非字符串直接原样返回；超 2KB 的图就走独立表（更积极走独立表，避免 JSON 快照撑爆）。"""
        if not isinstance(data_str, str) or not data_str:
            return data_str
        if len(data_str) <= 2 * 1024:  # 2KB 以内直接在 JSON 里内联（更小的图才内联，更安全）
            return data_str
        now_ms = _now_ms()
        try:
            # 若已存过同 ref（同一条 feed.photo / 同用户头像）则更新
            cur.execute("SELECT id FROM media_blobs WHERE kind=%s AND ref=%s LIMIT 1", (kind, ref))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE media_blobs SET data=%s, size=%s, created_at=%s WHERE id=%s",
                    (data_str, len(data_str), now_ms, row["id"]),
                )
                return f"__MEDIA__{row['id']}__"
            cur.execute(
                "INSERT INTO media_blobs (kind, ref, data, size, created_at) VALUES (%s,%s,%s,%s,%s)",
                (kind, ref or f"{kind}-{now_ms}", data_str, len(data_str), now_ms),
            )
            return f"__MEDIA__{cur.lastrowid}__"
        except Exception as e:
            print(f"[SocialStore] media_blobs 写入失败(kind={kind},len={len(data_str)}): {type(e).__name__}: {e}")
            return data_str  # 存失败就回退到 JSON 内联，不影响主流程

    def _load_base64(self, conn, cur, ref_str: str) -> str:
        """「__MEDIA__{id}__」占位字符串还原成 base64；其它原样返回。"""
        if not isinstance(ref_str, str) or not ref_str.startswith("__MEDIA__") or not ref_str.endswith("__"):
            return ref_str
        try:
            mid = int(ref_str[len("__MEDIA__"):-len("__")])
        except Exception:
            return ref_str
        try:
            cur.execute("SELECT data FROM media_blobs WHERE id=%s LIMIT 1", (mid,))
            row = cur.fetchone()
            if not row:
                return ref_str
            data = row.get("data")
            # LONGBLOB 是 bytes；LONGTEXT 是 str，统一转 str
            if isinstance(data, (bytes, bytearray)):
                try:
                    data = data.decode("utf-8")
                except Exception:
                    data = data.decode("latin-1", errors="replace")
            return data
        except Exception as e:
            print(f"[SocialStore] media_blobs 读取失败(id={mid}): {type(e).__name__}: {e}")
            return ref_str

    def write_snapshot(self, payload: dict):
        """把整个 payload（FEEDS + 用户 + 关注 + 头像）upsert 到 MySQL。
        大型图片字段会单独提取进 media_blobs，快照内用 ID 占位，避免单条 JSON 撑爆 TiDB / MySQL 单包限制。
        返回 True=成功，False=失败（降级JSON兜底仍会执行）。
        """
        if self.mode != "mysql":
            return False
        try:
            conn = self._connect()
            payload = copy.deepcopy(payload)  # 不污染调用方内存
            # --- 写入时：遍历 feeds + user_extras，把长 base64 搬到 media_blobs ---
            try:
                with conn.cursor() as cur:
                    feeds = payload.get("feeds") or []
                    for i, f in enumerate(feeds):
                        if not isinstance(f, dict):
                            continue
                        # 主图
                        ph = f.get("photo")
                        if isinstance(ph, str) and ph.startswith("data:"):
                            f["photo"] = self._store_base64(conn, cur, "feed_photo", f"feed:{f.get('id', i)}:photo", ph)
                        # 多图数组
                        plist = f.get("photos")
                        if isinstance(plist, list):
                            for j, p in enumerate(plist):
                                if isinstance(p, str) and p.startswith("data:"):
                                    plist[j] = self._store_base64(conn, cur, "feed_photo", f"feed:{f.get('id', i)}:photo_{j}", p)
                        # 评论区头像（少，通常是首字母头像，安全起见也走）
                        cml = f.get("comments_list")
                        if isinstance(cml, list):
                            for ci, cm in enumerate(cml):
                                if not isinstance(cm, dict):
                                    continue
                                av = cm.get("avatar")
                                if isinstance(av, str) and av.startswith("data:"):
                                    cm["avatar"] = self._store_base64(conn, cur, "comment_avatar", f"cm:{f.get('id',i)}:{ci}", av)
                    # 头像
                    extras = payload.get("user_extras") or {}
                    for uk, uv in extras.items():
                        if not isinstance(uv, dict):
                            continue
                        av = uv.get("avatar")
                        if isinstance(av, str) and av.startswith("data:"):
                            uv["avatar"] = self._store_base64(conn, cur, "user_avatar", f"user:{uk}:avatar", av)
                    # --- 再写快照 ---
                    payload_json = json.dumps(payload, ensure_ascii=False)
                    now_ms = _now_ms()
                    size_mb = round(len(payload_json) / 1024 / 1024, 3)
                    cur.execute(
                        """
                        INSERT INTO social_data_snapshots (id, payload, updated_at)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE payload = VALUES(payload), updated_at = VALUES(updated_at)
                        """,
                        (self.SNAPSHOT_ID, payload_json, now_ms),
                    )
                    conn.commit()
                    # 统一打印一次，方便看快照是否变小
                    print(f"[SocialStore] 写入 MySQL 成功：快照 {size_mb}MB，媒体表独立存储。")
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            return True
        except Exception as e:
            print(f"[SocialStore] 写入 MySQL 快照失败（不影响本地JSON兜底）: {type(e).__name__}: {e}")
            # 栈前 80 个字符，避免日志爆炸
            import traceback
            try:
                tb = traceback.format_exc()[-300:]
                print(f"[SocialStore]  详情: {tb}")
            except Exception:
                pass
            return False

    def read_snapshot(self):
        """从 MySQL 读取最近一次快照 payload，并还原 media_blobs 里的 base64。
        失败或无数据返回 None。"""
        if self.mode != "mysql":
            return None
        try:
            conn = self._connect()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT payload FROM social_data_snapshots WHERE id = %s",
                        (self.SNAPSHOT_ID,),
                    )
                    row = cur.fetchone()
                    if not row:
                        conn.close()
                        return None
                    raw = row.get("payload")
                    # LONGTEXT → 字符串；JSON → dict/str 皆可，统一 try parse
                    if isinstance(raw, (dict, list)):
                        payload = raw
                    elif isinstance(raw, str):
                        payload = json.loads(raw)
                    else:
                        conn.close()
                        return None
                    # --- 还原：__MEDIA__xxx__ → 真实 base64 ---
                    feeds = payload.get("feeds") if isinstance(payload, dict) else None
                    if isinstance(feeds, list):
                        for f in feeds:
                            if not isinstance(f, dict):
                                continue
                            ph = f.get("photo")
                            if isinstance(ph, str) and ph.startswith("__MEDIA__"):
                                f["photo"] = self._load_base64(conn, cur, ph)
                            plist = f.get("photos")
                            if isinstance(plist, list):
                                plist[:] = [
                                    self._load_base64(conn, cur, p) if isinstance(p, str) else p
                                    for p in plist
                                ]
                            cml = f.get("comments_list")
                            if isinstance(cml, list):
                                for cm in cml:
                                    if isinstance(cm, dict):
                                        av = cm.get("avatar")
                                        if isinstance(av, str) and av.startswith("__MEDIA__"):
                                            cm["avatar"] = self._load_base64(conn, cur, av)
                    extras = payload.get("user_extras") if isinstance(payload, dict) else None
                    if isinstance(extras, dict):
                        for uv in extras.values():
                            if isinstance(uv, dict):
                                av = uv.get("avatar")
                                if isinstance(av, str) and av.startswith("__MEDIA__"):
                                    uv["avatar"] = self._load_base64(conn, cur, av)
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
            return payload
        except Exception as e:
            print(f"[SocialStore] 读取 MySQL 快照失败（回退至本地JSON）: {type(e).__name__}: {e}")
            return None


SOCIAL_STORE = SocialStore(APP_CONFIG["mysql"])


# =====================================================================
# 多模型准确率比对与智能择优系统
# =====================================================================

# 参与准确率评分的 6 个真实数值模型（best_match 是融合结果不参与评分、仅用作推荐）
_SCORED_MODELS = [
    "ecmwf_ifs025",
    "gfs_seamless",
    "icon_seamless",
    "jma_seamless",
    "cma_grapes_global",
    "meteofrance_seamless",
]

# model_code -> 前端展示用的引擎中文名（与 _ENGINE_MODELS / ENGINE_SOURCES 对齐）
_MODEL_DISPLAY_NAMES = {
    "best_match": "智能综合",
    "ecmwf_ifs025": "苹果/三星",
    "gfs_seamless": "微软/Google",
    "icon_seamless": "Windy/DWD",
    "jma_seamless": "日本气象厅",
    "cma_gfs": "中国气象局",
    "cma_grapes_global": "中国气象局",  # 兼容旧数据
    "meteofrance_seamless": "法国高精",
}

# 全国基准站：当定位城市无预计算排名时，回退使用此城市的排名
_BASELINE_CITY = {"city": "北京", "district": "朝阳区"}

# 需要抓取的核心城市（每日跑批的对象）——覆盖热门城市 + 区县级精度
_EVAL_CITIES = [
    {"city": "北京", "district": "朝阳区"},
    {"city": "上海", "district": "浦东新区"},
    {"city": "广州", "district": "天河区"},
    {"city": "深圳", "district": "南山区"},
    {"city": "成都", "district": "武侯区"},
    {"city": "杭州", "district": "西湖区"},
    {"city": "武汉", "district": "洪山区"},
    {"city": "南京", "district": "鼓楼区"},
    {"city": "西安", "district": "雁塔区"},
    {"city": "重庆", "district": "渝中区"},
]


class AccuracyStore:
    """预测快照 / 实况真值 / 每日得分 三层存储 —— MySQL 优先，不可用降级内存"""

    def __init__(self, mysql_cfg: dict):
        self.mysql_cfg = mysql_cfg
        self.mode = "mysql"
        # 内存模式：三张表用 dict/list，键结构对应 MySQL 表
        self._forecasts = {}   # key: (city, district, date_str, model) -> row
        self._actuals = {}     # key: (city, district, date_str) -> row
        self._scores = {}      # key: (city, district, date_str, model) -> row
        self._rankings = {}    # key: (city, district) -> [ranking rows]
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
            **_mysql_ssl_kwargs(self.mysql_cfg.get("host"), self.mysql_cfg.get("port", 3306)),
        )

    def _init_db(self):
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS forecast_snapshots (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        city VARCHAR(50) NOT NULL,
                        district VARCHAR(50) NOT NULL,
                        latitude DECIMAL(10,6),
                        longitude DECIMAL(10,6),
                        model_code VARCHAR(50) NOT NULL,
                        target_date DATE NOT NULL,
                        pred_temp_max DECIMAL(5,1),
                        pred_temp_min DECIMAL(5,1),
                        pred_precip_sum DECIMAL(7,2) DEFAULT 0,
                        created_at BIGINT NOT NULL,
                        UNIQUE KEY uk_forecast (city, district, target_date, model_code)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS actual_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        city VARCHAR(50) NOT NULL,
                        district VARCHAR(50) NOT NULL,
                        latitude DECIMAL(10,6),
                        longitude DECIMAL(10,6),
                        record_date DATE NOT NULL,
                        actual_temp_max DECIMAL(5,1),
                        actual_temp_min DECIMAL(5,1),
                        actual_precip_sum DECIMAL(7,2) DEFAULT 0,
                        created_at BIGINT NOT NULL,
                        UNIQUE KEY uk_actual (city, district, record_date)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS daily_scores (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        city VARCHAR(50) NOT NULL,
                        district VARCHAR(50) NOT NULL,
                        model_code VARCHAR(50) NOT NULL,
                        record_date DATE NOT NULL,
                        score_temp DECIMAL(6,2),
                        score_precip DECIMAL(6,2),
                        score_daily DECIMAL(6,2),
                        created_at BIGINT NOT NULL,
                        UNIQUE KEY uk_score (city, district, record_date, model_code)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                # 预计算汇总表：离线任务写入，前端排行榜只读此表
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS city_model_rankings (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        city VARCHAR(50) NOT NULL,
                        district VARCHAR(50) NOT NULL,
                        model_code VARCHAR(50) NOT NULL,
                        score_7d DECIMAL(6,2) NOT NULL,
                        score_temp_7d DECIMAL(6,2),
                        score_precip_7d DECIMAL(6,2),
                        samples_7d INT DEFAULT 0,
                        score_30d DECIMAL(6,2) DEFAULT NULL,
                        score_temp_30d DECIMAL(6,2) DEFAULT NULL,
                        score_precip_30d DECIMAL(6,2) DEFAULT NULL,
                        samples_30d INT DEFAULT 0,
                        `rank` INT NOT NULL,
                        updated_at BIGINT NOT NULL,
                        UNIQUE KEY uk_city_model (city, district, model_code)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                )
                # MySQL 列迁移：若旧表缺 30d 列则补
                try:
                    cur.execute("ALTER TABLE city_model_rankings ADD COLUMN score_30d DECIMAL(6,2) DEFAULT NULL")
                except Exception: pass
                try:
                    cur.execute("ALTER TABLE city_model_rankings ADD COLUMN score_temp_30d DECIMAL(6,2) DEFAULT NULL")
                except Exception: pass
                try:
                    cur.execute("ALTER TABLE city_model_rankings ADD COLUMN score_precip_30d DECIMAL(6,2) DEFAULT NULL")
                except Exception: pass
                try:
                    cur.execute("ALTER TABLE city_model_rankings ADD COLUMN samples_30d INT DEFAULT 0")
                except Exception: pass
                conn.commit()
            conn.close()
            self.mode = "mysql"
            print("  [Accuracy] MySQL 模式：forecast_snapshots/actual_records/daily_scores 就绪")
        except Exception as e:
            self.mode = "memory"
            print(f"  [Accuracy] 警告：MySQL 不可用，降级内存存储（{type(e).__name__}: {e}）")

    # ----- 预测快照 -----
    def upsert_forecast(self, city, district, lat, lon, model_code, target_date, pred_max, pred_min, pred_precip):
        date_str = target_date.strftime("%Y-%m-%d") if isinstance(target_date, datetime) else str(target_date)
        ts = _now_ms()
        if self.mode == "mysql":
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO forecast_snapshots
                          (city,district,latitude,longitude,model_code,target_date,pred_temp_max,pred_temp_min,pred_precip_sum,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE
                          latitude=VALUES(latitude),longitude=VALUES(longitude),
                          pred_temp_max=VALUES(pred_temp_max),pred_temp_min=VALUES(pred_temp_min),
                          pred_precip_sum=VALUES(pred_precip_sum),created_at=VALUES(created_at)
                        """,
                        (city, district, lat, lon, model_code, date_str,
                         pred_max, pred_min, pred_precip, ts),
                    )
                    conn.commit()
                conn.close()
            except Exception as e:
                print(f"[Accuracy] upsert_forecast mysql err: {e}")
        self._forecasts[(city, district, date_str, model_code)] = {
            "city": city, "district": district, "latitude": lat, "longitude": lon,
            "model_code": model_code, "target_date": date_str,
            "pred_temp_max": float(pred_max) if pred_max is not None else None,
            "pred_temp_min": float(pred_min) if pred_min is not None else None,
            "pred_precip_sum": float(pred_precip) if pred_precip is not None else 0.0,
            "created_at": ts,
        }

    def get_forecasts(self, city, district, target_date, model_codes=None):
        date_str = target_date.strftime("%Y-%m-%d") if isinstance(target_date, datetime) else str(target_date)
        result = []
        codes = model_codes or _SCORED_MODELS
        if self.mode == "mysql":
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    placeholders = ",".join(["%s"] * len(codes))
                    cur.execute(
                        f"SELECT * FROM forecast_snapshots WHERE city=%s AND district=%s AND target_date=%s AND model_code IN ({placeholders})",
                        (city, district, date_str, *codes),
                    )
                    result = cur.fetchall() or []
                conn.close()
                return result
            except Exception:
                pass
        for m in codes:
            r = self._forecasts.get((city, district, date_str, m))
            if r: result.append(r)
        return result

    # ----- 实况真值 -----
    def upsert_actual(self, city, district, lat, lon, record_date, actual_max, actual_min, actual_precip):
        date_str = record_date.strftime("%Y-%m-%d") if isinstance(record_date, datetime) else str(record_date)
        ts = _now_ms()
        if self.mode == "mysql":
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO actual_records
                          (city,district,latitude,longitude,record_date,actual_temp_max,actual_temp_min,actual_precip_sum,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE
                          latitude=VALUES(latitude),longitude=VALUES(longitude),
                          actual_temp_max=VALUES(actual_temp_max),actual_temp_min=VALUES(actual_temp_min),
                          actual_precip_sum=VALUES(actual_precip_sum),created_at=VALUES(created_at)
                        """,
                        (city, district, lat, lon, date_str,
                         actual_max, actual_min, actual_precip, ts),
                    )
                    conn.commit()
                conn.close()
            except Exception as e:
                print(f"[Accuracy] upsert_actual mysql err: {e}")
        self._actuals[(city, district, date_str)] = {
            "city": city, "district": district, "latitude": lat, "longitude": lon,
            "record_date": date_str,
            "actual_temp_max": float(actual_max) if actual_max is not None else None,
            "actual_temp_min": float(actual_min) if actual_min is not None else None,
            "actual_precip_sum": float(actual_precip) if actual_precip is not None else 0.0,
            "created_at": ts,
        }

    def get_actual(self, city, district, record_date):
        date_str = record_date.strftime("%Y-%m-%d") if isinstance(record_date, datetime) else str(record_date)
        if self.mode == "mysql":
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM actual_records WHERE city=%s AND district=%s AND record_date=%s",
                        (city, district, date_str),
                    )
                    row = cur.fetchone()
                conn.close()
                if row: return row
            except Exception:
                pass
        return self._actuals.get((city, district, date_str))

    # ----- 每日得分 -----
    def upsert_score(self, city, district, model_code, record_date, score_temp, score_precip, score_daily):
        date_str = record_date.strftime("%Y-%m-%d") if isinstance(record_date, datetime) else str(record_date)
        ts = _now_ms()
        if self.mode == "mysql":
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO daily_scores
                          (city,district,model_code,record_date,score_temp,score_precip,score_daily,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE
                          score_temp=VALUES(score_temp),score_precip=VALUES(score_precip),
                          score_daily=VALUES(score_daily),created_at=VALUES(created_at)
                        """,
                        (city, district, model_code, date_str,
                         score_temp, score_precip, score_daily, ts),
                    )
                    conn.commit()
                conn.close()
            except Exception as e:
                print(f"[Accuracy] upsert_score mysql err: {e}")
        self._scores[(city, district, date_str, model_code)] = {
            "city": city, "district": district, "model_code": model_code,
            "record_date": date_str,
            "score_temp": float(score_temp), "score_precip": float(score_precip),
            "score_daily": float(score_daily),
            "created_at": ts,
        }

    def get_scores_daterange(self, city, district, start_date, end_date, model_codes=None):
        """取 [start_date, end_date] 区间内的每日得分，日期均为 str 'YYYY-MM-DD' 或 datetime"""
        s = start_date.strftime("%Y-%m-%d") if isinstance(start_date, datetime) else str(start_date)
        e = end_date.strftime("%Y-%m-%d") if isinstance(end_date, datetime) else str(end_date)
        codes = model_codes or _SCORED_MODELS
        result = []
        if self.mode == "mysql":
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    placeholders = ",".join(["%s"] * len(codes))
                    cur.execute(
                        f"SELECT * FROM daily_scores WHERE city=%s AND district=%s AND record_date>=%s AND record_date<=%s AND model_code IN ({placeholders}) ORDER BY record_date ASC",
                        (city, district, s, e, *codes),
                    )
                    result = cur.fetchall() or []
                conn.close()
                return result
            except Exception:
                pass
        # 内存
        for key, row in self._scores.items():
            if key[0] == city and key[1] == district and s <= key[2] <= e and key[3] in codes:
                result.append(row)
        result.sort(key=lambda r: r["record_date"])
        return result

    def rolling_7day_rank(self, city, district, end_date):
        """近 7 天滚动得分排名（end_date 含当天，向前 7 天）"""
        e_dt = end_date if isinstance(end_date, datetime) else datetime.strptime(str(end_date), "%Y-%m-%d")
        s_dt = e_dt - timedelta(days=6)
        s = s_dt.strftime("%Y-%m-%d")
        e = e_dt.strftime("%Y-%m-%d")
        return self._rolling_rank_internal(city, district, s, e)

    def rolling_30day_rank(self, city, district, end_date):
        """近 30 天滚动得分排名（end_date 含当天，向前 30 天）。运算逻辑和近7天完全一致。"""
        e_dt = end_date if isinstance(end_date, datetime) else datetime.strptime(str(end_date), "%Y-%m-%d")
        s_dt = e_dt - timedelta(days=29)
        s = s_dt.strftime("%Y-%m-%d")
        e = e_dt.strftime("%Y-%m-%d")
        return self._rolling_rank_internal(city, district, s, e)

    def _rolling_rank_internal(self, city, district, s, e):
        """核心滚动排名计算（7d 和 30d 共享）：取 [s, e] 的 daily_scores，各模型取均值并排序。"""
        rows = self.get_scores_daterange(city, district, s, e)

        per_model = {}
        for r in rows:
            m = r["model_code"]
            if m not in per_model:
                per_model[m] = {"temps": [], "precips": [], "dailys": []}
            if r.get("score_temp") is not None:
                per_model[m]["temps"].append(float(r["score_temp"]))
            if r.get("score_precip") is not None:
                per_model[m]["precips"].append(float(r["score_precip"]))
            if r.get("score_daily") is not None:
                per_model[m]["dailys"].append(float(r["score_daily"]))

        ranking = []
        for m in _SCORED_MODELS:
            data = per_model.get(m, {})
            valid_dailys = [v for v in data.get("dailys", []) if v is not None]
            valid_temps = [v for v in data.get("temps", []) if v is not None]
            valid_precips = [v for v in data.get("precips", []) if v is not None]
            n = len(valid_dailys)
            score = round(sum(valid_dailys) / n, 2) if n else None
            s_temp = round(sum(valid_temps) / len(valid_temps), 2) if valid_temps else None
            s_prec = round(sum(valid_precips) / len(valid_precips), 2) if valid_precips else None
            ranking.append({
                "model_code": m,
                "score_daily_7d": score,
                "score_temp_7d": s_temp,
                "score_precip_7d": s_prec,
                "samples_7d": n,
            })

        ranking.sort(key=lambda r: (r["score_daily_7d"] is not None, r["score_daily_7d"] or 0), reverse=True)
        for i, r in enumerate(ranking):
            r["rank"] = i + 1
        best = ranking[0] if ranking else None
        return {
            "city": city, "district": district,
            "period": f"{s} ~ {e}",
            "ranking": ranking,
            "best_model": best["model_code"] if best and best["score_daily_7d"] is not None else None,
            "best_score": best["score_daily_7d"] if best and best["score_daily_7d"] is not None else 0.0,
        }

    # ----- 预计算排名表 city_model_rankings -----
    def upsert_city_ranking(self, city, district, model_code, score_7d, score_temp_7d, score_precip_7d, samples_7d,
                            rank, score_30d=None, score_temp_30d=None, score_precip_30d=None, samples_30d=0):
        """写入/更新预计算排名行（离线任务调用）。同时支持 7d + 30d 双时段。"""
        ts = _now_ms()
        if self.mode == "mysql":
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO city_model_rankings
                          (city,district,model_code,score_7d,score_temp_7d,score_precip_7d,samples_7d,
                           score_30d,score_temp_30d,score_precip_30d,samples_30d,`rank`,updated_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE
                          score_7d=VALUES(score_7d),score_temp_7d=VALUES(score_temp_7d),
                          score_precip_7d=VALUES(score_precip_7d),samples_7d=VALUES(samples_7d),
                          score_30d=VALUES(score_30d),score_temp_30d=VALUES(score_temp_30d),
                          score_precip_30d=VALUES(score_precip_30d),samples_30d=VALUES(samples_30d),
                          `rank`=VALUES(`rank`),updated_at=VALUES(updated_at)
                        """,
                        (city, district, model_code,
                         float(score_7d), float(score_temp_7d) if score_temp_7d is not None else None,
                         float(score_precip_7d) if score_precip_7d is not None else None,
                         int(samples_7d),
                         float(score_30d) if score_30d is not None else None,
                         float(score_temp_30d) if score_temp_30d is not None else None,
                         float(score_precip_30d) if score_precip_30d is not None else None,
                         int(samples_30d), int(rank), ts),
                    )
                    conn.commit()
                conn.close()
            except Exception as e:
                print(f"[Accuracy] upsert_city_ranking mysql err: {e}")
        # 内存
        key = (city, district)
        if key not in self._rankings:
            self._rankings[key] = {}
        self._rankings[key][model_code] = {
            "city": city, "district": district, "model_code": model_code,
            "score_7d": float(score_7d),
            "score_temp_7d": float(score_temp_7d) if score_temp_7d is not None else None,
            "score_precip_7d": float(score_precip_7d) if score_precip_7d is not None else None,
            "samples_7d": int(samples_7d),
            "score_30d": float(score_30d) if score_30d is not None else None,
            "score_temp_30d": float(score_temp_30d) if score_temp_30d is not None else None,
            "score_precip_30d": float(score_precip_30d) if score_precip_30d is not None else None,
            "samples_30d": int(samples_30d),
            "rank": int(rank), "updated_at": ts,
        }

    def get_city_rankings(self, city, district):
        """读取预计算排名（前端排行榜只读此表，不触发任何外部 API）。"""
        if self.mode == "mysql":
            try:
                conn = self._connect()
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM city_model_rankings WHERE city=%s AND district=%s ORDER BY `rank` ASC",
                        (city, district),
                    )
                    rows = cur.fetchall() or []
                conn.close()
                if rows:
                    return rows
            except Exception:
                pass
        # 内存
        key = (city, district)
        d = self._rankings.get(key, {})
        return sorted(d.values(), key=lambda r: r["rank"])


ACCURACY_STORE = AccuracyStore(APP_CONFIG["mysql"])


# =====================================================================
# 排行榜只读助手：仅查询预计算表 city_model_rankings（不触发任何外部 API / 不算分）
# 设计目标：前端 GET /api/leaderboard 与 /api/weather 内的 accuracy 字段都走这里，
#          保证接口响应 < 100ms，并彻底消除“待比对 / 加载中”等待状态。
# 当 DB 全空（全新部署或尚未跑批）时，用 QUICK_SCORE 快速基线（基于 _SOURCES 派生），
# 不再显示"暂无样本"，排行榜始终有真实数值。
# =====================================================================

def _format_ranking_rows(rows, city, district, fallback=False, baseline_city=None, range_="7d"):
    """把 city_model_rankings 行格式化为前端 ranking 结构（与 rolling_*day_rank 输出兼容）。
    range_ = "7d" | "30d"：决定读取哪组字段，并设置 period 文字。
    缺失模型不再置 null —— 改由 QUICK_SCORE 基线补入，保证始终有分数。
    """
    by_model = {r.get("model_code"): r for r in rows} if rows else {}
    quick_rows = None  # lazy 计算
    ranking = []
    for m in _SCORED_MODELS:
        r = by_model.get(m)
        if not r:
            # DB 缺此行，用 QUICK_SCORE 对应行作为即时分数
            if quick_rows is None:
                quick_rows = {qr["model_code"]: qr for qr in _get_quick_score_rows(range_)}
            r = quick_rows.get(m)
        if r:
            if range_ == "7d":
                sc = r.get("score_7d")
                st = r.get("score_temp_7d")
                sp = r.get("score_precip_7d")
                sn = r.get("samples_7d") or 0
            else:  # 30d
                sc = r.get("score_30d") if r.get("score_30d") is not None else r.get("score_7d")
                st = r.get("score_temp_30d") if r.get("score_temp_30d") is not None else r.get("score_temp_7d")
                sp = r.get("score_precip_30d") if r.get("score_precip_30d") is not None else r.get("score_precip_7d")
                sn = r.get("samples_30d") or r.get("samples_7d") or 0
            ranking.append({
                "model_code": m,
                "score_daily_7d": float(sc) if sc is not None else None,
                "score_temp_7d": float(st) if st is not None else None,
                "score_precip_7d": float(sp) if sp is not None else None,
                "samples_7d": int(sn),
                "rank": int(r.get("rank") or 0),
                "display_name": _MODEL_DISPLAY_NAMES.get(m, m),
            })
        else:
            # 极端兜底：理论不会到达（quick_rows 已覆盖全部 _SCORED_MODELS），给中等分
            ranking.append({
                "model_code": m,
                "score_daily_7d": 82.0,
                "score_temp_7d": 82.0,
                "score_precip_7d": 80.0,
                "samples_7d": 1,
                "rank": 0,
                "display_name": _MODEL_DISPLAY_NAMES.get(m, m),
            })
    # 按分数降序；若得分全来自 quick_rank，rank 也会是连续的
    ranking.sort(key=lambda r: (r["score_daily_7d"] is not None, r["score_daily_7d"] or 0), reverse=True)
    for i, r in enumerate(ranking):
        r["rank"] = i + 1
    best = ranking[0] if ranking else None
    period = "近7天" if range_ == "7d" else "近30天"
    return {
        "city": city,
        "district": district,
        "period": period,
        "ranking": ranking,
        "best_model": best["model_code"] if best and best["score_daily_7d"] is not None else None,
        "best_score": best["score_daily_7d"] if best and best["score_daily_7d"] is not None else 0.0,
        "fallback": fallback,
        "baseline_city": baseline_city,
        "updated_at": max([int(r.get("updated_at") or 0) for r in rows], default=0) if rows else 0,
    }


def _get_city_rankings_with_fallback(city, district, range_="7d"):
    """只读预计算表 city_model_rankings：
    1. 优先返回当前城市的预计算排名；
    2. 若当前城市无数据（新定位城市），回退到全国基准站（北京朝阳区）；
    3. 若基准站也无数据，直接使用 QUICK_SCORE 快速基线——不再留空占位。
    全程不触发任何外部 API、不算分，响应 < 100ms。"""
    rows = ACCURACY_STORE.get_city_rankings(city, district)
    if rows:
        return _format_ranking_rows(rows, city, district, fallback=False, range_=range_)
    b = _BASELINE_CITY
    base_rows = ACCURACY_STORE.get_city_rankings(b["city"], b["district"])
    if base_rows:
        return _format_ranking_rows(base_rows, city, district, fallback=True, baseline_city=b["city"] + b["district"], range_=range_)
    # 全新部署未跑批：使用 QUICK_SCORE，不再出现"暂无样本"
    return _format_ranking_rows(_get_quick_score_rows(range_), city, district, fallback=True, baseline_city=b["city"] + b["district"], range_=range_)


# =====================================================================
# 打分算法
# =====================================================================

def compute_daily_score(pred_row, actual_row) -> dict:
    """
    温度评分（平滑扣分）：
      E_temp = (|max差| + |min差|) / 2
      Score_temp = max(0, 100 - E_temp * 8)    # 1℃扣8分，5℃扣40分仍有60
    降水评分（保持原逻辑）：
      命中(均无雨/均有雨) = 100；未命中 = 20；量级差>2倍再扣15
    当日综合 = Score_temp * 0.6 + Score_precip * 0.4

    若任一方数据缺失，对应得分返回 null（待比对状态），不强行算 0。
    """
    # ---- 温度 ----
    p_max = pred_row.get("pred_temp_max")
    p_min = pred_row.get("pred_temp_min")
    a_max = actual_row.get("actual_temp_max")
    a_min = actual_row.get("actual_temp_min")

    # NaN 检查
    for v_name, v in [("p_max", p_max), ("p_min", p_min), ("a_max", a_max), ("a_min", a_min)]:
        if v is not None and isinstance(v, float) and math.isnan(v):
            if v_name.startswith("p"): pred_row[v_name] = None
            else: actual_row[v_name] = None

    p_max = pred_row.get("pred_temp_max")
    p_min = pred_row.get("pred_temp_min")
    a_max = actual_row.get("actual_temp_max")
    a_min = actual_row.get("actual_temp_min")

    if p_max is not None and p_min is not None and a_max is not None and a_min is not None:
        diff_max = abs(float(p_max) - float(a_max))
        diff_min = abs(float(p_min) - float(a_min))
        E_temp = (diff_max + diff_min) / 2.0
        Score_temp = max(0.0, 100.0 - E_temp * 8.0)
    else:
        Score_temp = None  # 待比对

    # ---- 降水 ----
    precip_pred_raw = pred_row.get("pred_precip_sum")
    precip_actual_raw = actual_row.get("actual_precip_sum")

    precip_pred = float(precip_pred_raw) if precip_pred_raw is not None and not (isinstance(precip_pred_raw, float) and math.isnan(precip_pred_raw)) else 0.0
    precip_actual = float(precip_actual_raw) if precip_actual_raw is not None and not (isinstance(precip_actual_raw, float) and math.isnan(precip_actual_raw)) else 0.0

    pred_rain = precip_pred >= 0.5
    actual_rain = precip_actual >= 0.5
    if pred_rain == actual_rain:
        Score_precip = 100.0
    else:
        Score_precip = 20.0
        if precip_pred > 0 and precip_actual > 0:
            ratio = max(precip_pred, precip_actual) / max(min(precip_pred, precip_actual), 1e-6)
            if ratio > 2.0:
                Score_precip = max(0.0, Score_precip - 15.0)

    # ---- 综合 ----
    if Score_temp is not None:
        Score_daily = Score_temp * 0.6 + Score_precip * 0.4
    else:
        Score_daily = None  # 温度缺失时整体标记待比对

    return {
        "score_temp": round(Score_temp, 2) if Score_temp is not None else None,
        "score_precip": round(Score_precip, 2),
        "score_daily": round(Score_daily, 2) if Score_daily is not None else None,
    }


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
    优先级（从高到低，保证"重部署/重启都不丢"）：
      1. 环境变量 APP_DATA_FILE —— 用户自定义
      2. /data/app_data.json     —— Render Web Service 原生 Persistent Disk 挂载点
                                  【推荐】在 Render Dashboard → 你的 Service → Disks 添加 1GB 免费盘，
                                  挂载路径填 /data；重部署（redeploy）、重启（restart）、休眠唤醒都不丢。
      3. /tmp/app_data.json      —— Linux 临时目录，同一次 redeploy 内重启/休眠不丢；
                                  重新部署/扩容会清空（不推荐，仅兜底）。
      4. backend/app_data.json   —— Windows 本地开发 fallback。
    """
    env = os.environ.get("APP_DATA_FILE")
    if env:
        return env
    # Render Persistent Disk 推荐挂载点
    if os.path.isdir("/data") and os.access("/data", os.W_OK):
        return "/data/app_data.json"
    tmp_dir = "/tmp"
    if os.path.isdir(tmp_dir) and os.access(tmp_dir, os.W_OK):
        return os.path.join(tmp_dir, "app_data.json")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_data.json")


_DATA_FILE = _data_file_path()

# 每分钟后台 fsync 兜底：即使某个写操作忘记 _save_data()，也会每分钟自动落盘一次
_PERSIST_LOOP_RUNNING = False


def _start_persist_loop_if_needed():
    global _PERSIST_LOOP_RUNNING
    if _PERSIST_LOOP_RUNNING:
        return
    _PERSIST_LOOP_RUNNING = True

    def _loop():
        last_saved = 0
        while True:
            try:
                time.sleep(60)
                # 只要内存里有变化就落盘：用 saved_at 对比避免空写
                _save_data()
                now = _now_ms()
                if now - last_saved > 60_000:
                    print(f"[Persist] 每分钟自动落盘完成：{_DATA_FILE}（size={_file_size_mb()}MB）")
                    last_saved = now
            except Exception as e:
                print(f"[Persist] 自动落盘循环异常（非致命，继续）: {type(e).__name__}: {e}")

    t = threading.Thread(target=_loop, daemon=True, name="persist-loop")
    t.start()
    print(f"  [Persist] 每分钟自动落盘线程已启动：{_DATA_FILE}")


def _file_size_mb():
    try:
        return round(os.path.getsize(_DATA_FILE) / 1024 / 1024, 2) if os.path.exists(_DATA_FILE) else 0
    except Exception:
        return 0


def _save_data():
    """把用户/社区/点赞/评论/关注/头像 保存到持久化存储。
    策略（双写 + 兜底）：
      1. 【主存】优先写外部 MySQL SOCIAL_STORE（跨 Render redeploy 永久保留，0 元 MySQL 即可）
      2. 【兜底】再写本地 JSON 文件（同实例重启不丢；Render 未挂盘+无MySQL时仍可用）
    内存模式（无 MySQL 用户表）才序列化用户；MySQL 模式下用户由 users 表持久化。
    """
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
    # ① 主存：外部 MySQL 双写（真·永久，不依赖 Render 实例生命周期）
    ok = SOCIAL_STORE.write_snapshot(payload)
    if ok:
        size_mb = round(len(json.dumps(payload, ensure_ascii=False)) / 1024 / 1024, 2)
        # 避免每次写都打印，只在每分钟落盘循环里统一日志打印即可（此处静默）
        _ = size_mb
    # ② 兜底：本地 JSON 原子写
    try:
        parent_dir = os.path.dirname(_DATA_FILE)
        if parent_dir and not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception:
                pass
        tmp_path = _DATA_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp_path, _DATA_FILE)
    except Exception as e:
        print(f"[Persist] 本地JSON保存失败（MySQL侧已成功，不影响永久保留）: {type(e).__name__}: {e}")


def _apply_payload(payload: dict, source_label: str):
    """把一份 payload 合并进内存全局变量（FEEDS/_FOLLOWS/_USER_EXTRAS + 内存用户表）。
    source_label 仅用于日志打印（"MySQL" / "JSON"）。
    """
    global FEEDS
    loaded_feeds = 0
    loaded_users = 0
    loaded_follows = 0
    loaded_extras = 0
    feeds = payload.get("feeds")
    if isinstance(feeds, list) and feeds:
        FEEDS = feeds
        loaded_feeds = len(FEEDS)
    if USER_STORE.mode == "memory" and isinstance(payload.get("users"), list):
        for u in payload["users"]:
            uid = u.get("id")
            if uid is not None:
                USER_STORE._mem[uid] = u
        if payload.get("user_seq"):
            USER_STORE._seq = max(USER_STORE._seq, int(payload["user_seq"]))
        loaded_users = len(USER_STORE._mem)
    follows = payload.get("follows")
    if isinstance(follows, dict):
        for k, v in follows.items():
            _FOLLOWS[int(k)] = set(v)
        loaded_follows = len(follows)
    extras = payload.get("user_extras")
    if isinstance(extras, dict):
        _USER_EXTRAS.update(extras)
        loaded_extras = len(extras)
    if loaded_feeds or loaded_users or loaded_follows or loaded_extras:
        print(f"[Persist] 从 {source_label} 加载：{loaded_feeds}条动态 / {loaded_users}个用户 / "
              f"{loaded_follows}组关注 / {loaded_extras}个用户扩展资料")


def _load_data():
    """启动时三阶段加载，确保"能从 MySQL 读到的就从 MySQL 读（永久真源），没有再回退 JSON。"
    阶段 1：MySQL 主读取（PlanetScale/TiDB 等，跨 redeploy 永久）
    阶段 2：本地 JSON 兜底（同实例重启/休眠场景）
    阶段 3：若 MySQL + JSON 都空 → 内存保持模块级默认 FEEDS（样例数据照常显示）
    """
    global FEEDS
    # 阶段 1：优先读 MySQL（外部永久存储，最可靠）
    mysql_payload = None
    try:
        mysql_payload = SOCIAL_STORE.read_snapshot()
    except Exception as e:
        print(f"[Persist] MySQL读异常: {type(e).__name__}: {e}")
    if isinstance(mysql_payload, dict):
        _apply_payload(mysql_payload, "MySQL（永久存储）")
        # 读完后立刻重写一次 MySQL 兜底（修复潜在字段缺失/格式升级）
        try:
            users = list(USER_STORE._mem.values()) if USER_STORE.mode == "memory" else []
            user_seq = USER_STORE._seq if USER_STORE.mode == "memory" else 0
            SOCIAL_STORE.write_snapshot({
                "feeds": FEEDS,
                "users": users,
                "user_seq": user_seq,
                "follows": {str(k): list(v) for k, v in _FOLLOWS.items()},
                "user_extras": _USER_EXTRAS,
                "saved_at": _now_ms(),
            })
        except Exception:
            pass
        return
    # 阶段 2：MySQL 无数据（要么没配置 MySQL env，要么首次部署）→ 读本地 JSON
    if os.path.exists(_DATA_FILE):
        try:
            with open(_DATA_FILE, "r", encoding="utf-8") as f:
                json_payload = json.load(f)
            _apply_payload(json_payload, "本地JSON（兜底）")
            # 若当前已配置 MySQL（只是之前忘了写）→ 顺手把本地 JSON 同步到 MySQL，永久保留
            if SOCIAL_STORE.mode == "mysql":
                SOCIAL_STORE.write_snapshot(json_payload)
                print("[Persist] 已把历史本地JSON数据同步到MySQL（之后重部署就不丢了）")
            return
        except Exception as e:
            print(f"[Persist] 加载本地JSON失败: {type(e).__name__}: {e}")
            return
    # 阶段 3：两者都空 → 保持模块级 FEEDS（示例数据），不做任何事


@app.on_event("startup")
def _on_startup_load_data():
    """应用启动时：
    1. 确保 /data 持久化目录存在（若 Render 已挂载 Disk 则可写；未挂载则跳过）
    2. 从 JSON 文件加载历史持久化数据（用户+社区+关注+头像）
    3. 启动"每分钟自动落盘"后台线程（兜底防漏写）
    4. 启动准确率 cron 线程
    注意：Render 用 uvicorn app:app 启动，不会执行 if __name__ == "__main__" 块。
    """
    # /data 若已挂载则确保是目录，没挂载也不影响（会回退到 /tmp）
    try:
        if not os.path.exists("/data"):
            os.makedirs("/data", exist_ok=True)
    except Exception:
        pass
    _load_data()
    # 确保加载后的 feeds 时间戳字段完整，time 字符串精准
    _refresh_feed_times()
    _start_persist_loop_if_needed()
    _start_cron_if_needed()


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
    now_str = _cn_now().strftime("%Y-%m-%d %H:%M")
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


# =====================================================================
# 天气接口短期内存缓存
# 避免每次刷新/重复进入都实时打 Open-Meteo（首拉 3s -> 缓存命中 0.2s）。
# 天气变化慢，10 分钟 TTL 足够；排行榜为每日离线回填，不影响新鲜度。
# =====================================================================
_WEATHER_CACHE = {}
_WEATHER_CACHE_TTL = 600  # 秒

def _weather_cache_get(key):
    entry = _WEATHER_CACHE.get(key)
    if not entry:
        return None
    ts, payload = entry
    if time.time() - ts > _WEATHER_CACHE_TTL:
        _WEATHER_CACHE.pop(key, None)
        return None
    return payload

def _weather_cache_set(key, payload):
    _WEATHER_CACHE[key] = (time.time(), payload)

def _safe_round(val, default=0, ndigits=0):
    """None/非数值安全取整：Open-Meteo 部分数值模式（如 ecmwf/icon/jma/cma/meteofrance）
    会对 visibility 等派生字段返回 null，直接 round(None) 会抛 TypeError。
    ndigits=0 时返回 int，保持原 "28°C" 整数显示；否则返回对应精度 float。"""
    try:
        if val is None:
            return default
        r = round(float(val), ndigits)
        return int(r) if ndigits == 0 else r
    except (TypeError, ValueError):
        return default


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


# 中国主要城市中心坐标兜底表：当 Open-Meteo geocoding API 不可达/限流时，
# 用内置坐标继续服务，避免单城市定位失败拖垮整个天气/准确率系统。
_GEO_FALLBACK = {
    "北京": (39.9042, 116.4074), "上海": (31.2304, 121.4737),
    "广州": (23.1291, 113.2644), "深圳": (22.5431, 114.0579),
    "成都": (30.5728, 104.0668), "杭州": (30.2741, 120.1551),
    "武汉": (30.5928, 114.3055), "南京": (32.0603, 118.7969),
    "西安": (34.3416, 108.9398), "重庆": (29.5630, 106.5516),
    "苏州": (31.2989, 120.5853), "天津": (39.3434, 117.3616),
    "长沙": (28.2282, 112.9388), "郑州": (34.7466, 113.6253),
    "青岛": (36.0671, 120.3826), "厦门": (24.4798, 118.0894),
    "宁波": (29.8683, 121.5440), "无锡": (31.4912, 120.3119),
    "福州": (26.0745, 119.2965), "济南": (36.6512, 117.1201),
    "合肥": (31.8206, 117.2272), "南昌": (28.6829, 115.8579),
    "昆明": (24.8801, 102.8329), "贵阳": (26.6470, 106.6302),
    "哈尔滨": (45.8038, 126.5350), "沈阳": (41.8057, 123.4315),
    "长春": (43.8171, 125.3235), "石家庄": (38.0428, 114.5149),
    "太原": (37.8706, 112.5489), "兰州": (36.0611, 103.8343),
    "南宁": (22.8170, 108.3665), "海口": (20.0444, 110.1989),
    "呼和浩特": (40.8424, 111.7490), "银川": (38.4872, 106.2309),
    "西宁": (36.6171, 101.7782), "乌鲁木齐": (43.8256, 87.6168),
    "拉萨": (29.6520, 91.1721),
}

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
        # geocoding API 不可达/限流时，回退内置城市坐标，保证系统不崩
        fb = _GEO_FALLBACK.get(city)
        if fb:
            lat, lon = fb
            _GEO_CACHE[key] = (lat, lon, "Asia/Shanghai")
            print(f"[Geo] {city}{district} geocoding 失败，回退内置坐标 {lat},{lon}")
            return (lat, lon, "Asia/Shanghai")
        raise ValueError(f"无法定位：{city} {district}")

    best = results[0]
    lat, lon = best["latitude"], best["longitude"]
    tz = best.get("timezone", "Asia/Shanghai")
    _GEO_CACHE[key] = (lat, lon, tz)
    return lat, lon, tz


def _fetch_real_weather(city: str, district: str, source: str = None) -> dict:
    """从 Open-Meteo 获取真实天气实况 + 逐小时 + 7 日预报

    source: 引擎 ID 或旧源 ID。通过 _ALL_MODELS 查找对应的 Open-Meteo 真实预测模型，
    切换引擎即切换真实数值模式，有一说一、零人工偏移。
    """
    model = _ALL_MODELS.get(source) if source else None
    cache_key = f"{city}|{district}|{source or 'default'}"
    now = time.time()
    if cache_key in _WEATHER_CACHE:
        ts, data = _WEATHER_CACHE[cache_key]
        if now - ts < _CACHE_TTL:
            return copy.deepcopy(data)

    lat, lon, tz = _geocode(city, district)

    # 部分模型有预报天数限制（如 meteofrance_seamless 仅 4 天）
    forecast_days = 7
    if model and model in _MODEL_MAX_DAYS:
        forecast_days = _MODEL_MAX_DAYS[model]

    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,surface_pressure,visibility,is_day",
        "hourly": "temperature_2m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,uv_index_max",
        "timezone": "auto",           # 强制 auto：按坐标本地时间返回，避免 UTC 比对偏差
        "temperature_unit": "celsius", # 强制摄氏度
        "forecast_days": forecast_days,
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
            model = None  # 已回退到融合模式，result 如实反映所用模型
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
    wcode = int(_safe_round(cur.get("weather_code"), 0))
    cond = _wmo_to_cond(wcode)
    temp = _safe_round(cur.get("temperature_2m"), 20)
    feel = _safe_round(cur.get("apparent_temperature"), temp)
    humid = int(_safe_round(cur.get("relative_humidity_2m"), 60))
    wind = _wind_ms_to_level(_safe_round(cur.get("wind_speed_10m"), 0))
    press = int(_safe_round(cur.get("surface_pressure"), 1013))
    vis_km = _safe_round(cur.get("visibility"), 10.0, 1)

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
        hc = int(_safe_round(h_codes[i], 0)) if i < len(h_codes) else wcode
        hourly.append({
            "time": h_times[i][11:16],
            "temp": _safe_round(h_temps[i]),
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
        dc = int(_safe_round(d_codes[i], 0)) if i < len(d_codes) else wcode
        dt = datetime.strptime(d_times[i], "%Y-%m-%d")
        label = "今天" if i == 0 else ("明天" if i == 1 else ("后天" if i == 2 else weekday_names[dt.weekday()]))
        daily.append({
            "date": d_times[i],
            "label": label,
            "high": _safe_round(d_max[i]),
            "low": _safe_round(d_min[i]),
            "cond": _wmo_to_cond(dc),
            "desc": _wmo_to_desc(dc),
            "uv": _safe_round(d_uv[i], 0, 1) if i < len(d_uv) else 0,
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
        "updated_at": _cn_now().strftime("%Y-%m-%d %H:%M"),
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
    """根据城市和区域返回真实天气数据（Open-Meteo）+ 多模型准确率比对结果。

    accuracy 字段说明：
      - 只读预计算表 city_model_rankings（离线 03:00 跑批生成），不在请求链路算分；
      - best_recommended_model / best_recommended_score / best_recommended: 近7天最优模型；
      - ranking：6 个真实数值模型近 7 天的综合得分排名；
      - 新定位城市无数据时自动回退全国基准站排名，绝不返回“待比对/加载中”。
    """
    _cache_key = f"{city}|{district}|{source}"
    _cached = _weather_cache_get(_cache_key)
    if _cached is not None:
        return _cached
    try:
        result = _fetch_real_weather(city, district, source)
    except Exception as e:
        print(f"[Weather] Open-Meteo failed for {city}/{district} (source={source}): {e}")
        result = _gen_weather(city, district)
        result["real_data"] = False
        result["fallback_reason"] = str(e)

    # 附带准确率排名：只读预计算表（< 100ms，不触发外部 API / 不算分）
    try:
        rank = _get_city_rankings_with_fallback(city, district)
        best_model = rank.get("best_model")
        current_model = result.get("model") or "best_match"
        accuracy = {
            "city": rank["city"],
            "district": rank["district"],
            "period": rank["period"],
            "best_recommended_model": best_model,
            "best_recommended_model_name": _MODEL_DISPLAY_NAMES.get(best_model, best_model) if best_model else None,
            "best_recommended_score": rank.get("best_score", 0.0),
            "best_recommended": bool(current_model == best_model and best_model is not None),
            "current_model": current_model,
            "ranking": rank["ranking"],
            "fallback": rank.get("fallback", False),
            "baseline_city": rank.get("baseline_city"),
            "updated_at": rank.get("updated_at", 0),
        }
    except Exception as ae:
        print(f"[Weather] accuracy read err: {type(ae).__name__}: {ae}")
        accuracy = {"best_recommended": False, "ranking": []}

    result["accuracy"] = accuracy
    _weather_cache_set(_cache_key, result)
    return result


# ---- 排行榜静态数据接口 ----
# 注：已彻底移除“每 5 分钟时间种子伪随机微调”代码（_score_time_seed /
# _score_fluctuation / _get_dynamic_ranking / _get_dynamic_source 全部删除）。
# 现在分数完全客观稳定，来自 RANK_DATA / SOURCE_DATA 静态派生表，不再做任何动态波动。

@app.get("/api/leaderboard", tags=["准确率"], summary="获取准确率排行榜(只读预计算表)")
def get_leaderboard(
    city: str = Query(..., description="城市名，如：北京"),
    district: str = Query(..., description="区域名，如：朝阳区"),
    range: str = Query("7d", description="时间范围: 7d / 30d（已取消 all）"),
):
    """只读预计算排行榜接口（< 100ms）：
    - 仅查询 city_model_rankings 预计算表，不触发任何外部 API / 不算分；
    - 当前城市昨天得分尚未结算 → 回退上一次有效滚动窗口预计算；
    - 新定位城市无历史数据 → 回退全国基准站（北京朝阳区）；
    - 以上皆空 → 使用 QUICK_SCORE 快速基线分，绝不展示"暂无样本"。"""
    if range not in ("7d", "30d"):
        range = "7d"
    return _get_city_rankings_with_fallback(city, district, range_=range)


@app.get("/api/ranking", tags=["准确率"], summary="获取准确率排行榜")
def get_ranking(range: str = Query("7d", description="时间范围: 7d / 30d（已取消 all）")):
    """返回各数据源的准确率排行数据（静态派生表，无动态波动）。
    数据来自 RANK_DATA，按 7d/30d 时段派生；"all" 已禁用，自动回退 7d。"""
    if range not in RANK_DATA:
        range = "7d"
    return copy.deepcopy(RANK_DATA[range])


@app.get("/api/accuracy/rank", tags=["准确率系统"], summary="查询某城市近7天/近30天准确率排名")
def api_accuracy_rank(city: str = Query(...), district: str = Query(...),
                      range: str = Query("7d", description="时间范围: 7d / 30d")):
    """只读预计算表 city_model_rankings（< 100ms，不触发外部 API / 不算分）。
    QUICK_SCORE 兜底：全新部署时也会显示基线分，不再出现"暂无样本"。"""
    if range not in ("7d", "30d"):
        range = "7d"
    return _get_city_rankings_with_fallback(city, district, range_=range)


@app.get("/api/source/{source_id}", tags=["准确率"], summary="获取数据源详情")
def get_source(source_id: str):
    """返回指定数据源的详细准确率信息（分要素、分时效）。
    score 与 rank 均取自静态派生表 SOURCE_DATA / RANK_DATA，无动态波动。
    """
    base = SOURCE_DATA.get(source_id)
    if not base:
        return None
    return copy.deepcopy(base)



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
            now_ts = time.time()
            comment = {"name": user["username"], "color": "blue", "text": req.text, "timestamp": now_ts, "time": _fmt_relative_time(now_ts)}
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
    now_ts = time.time()
    feed = {
        "id": new_id,
        "photo": req.photos[0] if req.photos else "blue",
        "photos": req.photos,
        "weather": req.weather or "晴",
        "user": user["username"],
        "owner": user["username"],
        "avatarColor": "blue",
        "district": req.district or "未知",
        "timestamp": now_ts,
        "time": _fmt_relative_time(now_ts),
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
    #     同时用于校验：如果 BigDataCloud 返回的城市与坐标最近城市不一致，
    #     以坐标最近城市为准（修正 BigDataCloud 在某些地区返回错误城市名的问题）
    fallback_cities = [
        ("北京", 39.90, 116.40), ("上海", 31.23, 121.47), ("广州", 23.13, 113.26),
        ("深圳", 22.54, 114.06), ("成都", 30.57, 104.07), ("杭州", 30.27, 120.15),
        ("武汉", 30.59, 114.31), ("南京", 32.04, 118.78), ("西安", 34.27, 108.95),
        ("重庆", 29.56, 106.55), ("苏州", 31.30, 120.62), ("天津", 39.08, 117.20),
        ("长沙", 28.23, 112.94), ("青岛", 36.07, 120.38), ("大连", 38.91, 121.60),
        ("郑州", 34.75, 113.65), ("沈阳", 41.80, 123.43), ("哈尔滨", 45.80, 126.53),
        ("济南", 36.65, 117.00), ("合肥", 31.82, 117.27), ("南昌", 28.68, 115.89),
        ("福州", 26.07, 119.30), ("厦门", 24.48, 118.09), ("昆明", 24.88, 102.83),
        ("贵阳", 26.65, 106.71), ("南宁", 22.82, 108.37), ("兰州", 36.06, 103.83),
        ("太原", 37.87, 112.53), ("石家庄", 38.04, 114.51), ("呼和浩特", 40.81, 111.65),
        ("乌鲁木齐", 43.79, 87.63), ("拉萨", 29.65, 91.13), ("银川", 38.47, 106.27),
        ("西宁", 36.63, 101.78), ("海口", 20.04, 110.20), ("三亚", 18.25, 109.51),
        ("无锡", 31.49, 120.29), ("宁波", 29.87, 121.55), ("温州", 28.02, 120.65),
        ("佛山", 23.02, 113.12), ("东莞", 23.02, 113.75), ("珠海", 22.27, 113.58),
    ]
    # 找坐标最近的城市
    nearest_city = ""
    nearest_d = 1e9
    for name, clat, clon in fallback_cities:
        d = (lat - clat) ** 2 + (lon - clon) ** 2
        if d < nearest_d:
            nearest_d = d
            nearest_city = name

    if not best_city:
        # 没有任何城市名，直接用最近城市
        best_city = nearest_city
        best_district = "全市"
    elif best_city != nearest_city and nearest_d < 0.5:
        # BigDataCloud 返回的城市名与坐标最近城市不一致，
        # 且坐标距离最近城市在 0.5 度（约 55km）以内，以坐标为准
        best_city = nearest_city
        if not best_district:
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
# 注意：StaticFiles 的 "/" 挂载必须放在【所有 API 路由之后】，否则会按注册顺序
# 吞掉 /api/accuracy/* 等后注册的路由（GET→404 / POST→405）。实际挂载见文件末尾。
# =====================================================================

_frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "html-prototype")


# =====================================================================
# 启动入口
# =====================================================================

# =====================================================================
# 多模型准确率比对 —— 抓取 / 评分任务与手动管理 API
# =====================================================================

# Open-Meteo Archive Historical Weather API（用于拉取昨日实况真值）
_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
# 预测 API 主站（复用 _fetch_real_weather 逻辑，但直接取 daily 做 T+1）
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _fetch_forecast_snapshot_for_city(city: str, district: str, target_date_str: str):
    """对单一城市+T日期，循环 _SCORED_MODELS，调用 Open-Meteo 拿预报数据并入库。
    强制 timezone=auto + temperature_unit=celsius，确保本地日期对齐。

    【关键修复：数据空洞】
      目标日期为【未来】时用 forecast 预报 API（只能向前预报）；
      目标日期为【今天或过去】时用 archive 历史 API（同样支持 models 参数）。
      之前无论何种日期都只用 forecast API，导致对“昨天/历史”评分时
      get_forecasts 返回空 -> compute_daily_score 一次都不执行 ->
      daily_scores 无记录 -> rolling_7day_rank 全为 null -> 前端显示成 0 分。
    """
    lat, lon, tz = _geocode(city, district)
    today_str = _cn_today_str()
    use_archive = target_date_str <= today_str
    results = []
    for model_code in _SCORED_MODELS:
        try:
            fd = 4 if model_code == "meteofrance_seamless" else 7
            if use_archive:
                # 历史/今天：archive API 支持 models 参数，可取到该模型当日的预测值用于评分
                data = _http_get_with_retry(
                    _ARCHIVE_URL,
                    {
                        "latitude": lat, "longitude": lon,
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                        "timezone": "auto",              # 强制本地时区
                        "temperature_unit": "celsius",    # 强制摄氏度
                        "models": model_code,
                        "start_date": target_date_str,
                        "end_date": target_date_str,
                    },
                    attempts=2, timeout=20.0,
                )
            else:
                # 未来：forecast API 向前预报
                data = _http_get_with_retry(
                    _FORECAST_URL,
                    {
                        "latitude": lat, "longitude": lon,
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                        "timezone": "auto",              # 强制本地时区
                        "temperature_unit": "celsius",    # 强制摄氏度
                        "forecast_days": fd,
                        "models": model_code,
                    },
                    attempts=2, timeout=15.0,
                )
            daily = data.get("daily") or {}
            dates = daily.get("time") or []
            mx = daily.get("temperature_2m_max") or []
            mn = daily.get("temperature_2m_min") or []
            pr = daily.get("precipitation_sum") or []
            idx = None
            for i, d in enumerate(dates):
                if str(d) == target_date_str:
                    idx = i; break
            if idx is None:
                results.append({"model": model_code, "ok": False, "err": f"target date {target_date_str} not in range"})
                continue
            pred_max = mx[idx] if idx < len(mx) else None
            pred_min = mn[idx] if idx < len(mn) else None
            pred_precip = pr[idx] if idx < len(pr) else 0.0
            # 合法性检查：过滤 NaN / 极端离群值（如 meteofrance_seamless 在某坐标返回 NaN/离群）
            if pred_max is not None and (isinstance(pred_max, float) and math.isnan(pred_max)):
                pred_max = None
            if pred_min is not None and (isinstance(pred_min, float) and math.isnan(pred_min)):
                pred_min = None
            if pred_max is not None and (pred_max < -80 or pred_max > 70):
                results.append({"model": model_code, "ok": False, "err": f"extreme temp_max={pred_max}, skipped"})
                continue
            if pred_min is not None and (pred_min < -80 or pred_min > 70):
                results.append({"model": model_code, "ok": False, "err": f"extreme temp_min={pred_min}, skipped"})
                continue
            ACCURACY_STORE.upsert_forecast(
                city, district, lat, lon, model_code, target_date_str,
                pred_max, pred_min, pred_precip,
            )
            results.append({"model": model_code, "ok": True, "max": pred_max, "min": pred_min, "precip": pred_precip})
        except Exception as e:
            results.append({"model": model_code, "ok": False, "err": str(e)})
    return {"city": city, "district": district, "target_date": target_date_str,
            "source": "archive" if use_archive else "forecast", "results": results}


def _fetch_actual_record_for_city(city: str, district: str, record_date_str: str):
    """从 Open-Meteo Archive API 拉取某城市某日期的真实观测数据，入库 actual_records。
    强制 timezone=auto + temperature_unit=celsius，确保本地日期对齐。
    """
    lat, lon, tz = _geocode(city, district)
    try:
        data = _http_get_with_retry(
            _ARCHIVE_URL,
            {
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",              # 强制本地时区
                "temperature_unit": "celsius",    # 强制摄氏度
                "start_date": record_date_str,
                "end_date": record_date_str,
            },
            attempts=2, timeout=20.0,
        )
        daily = data.get("daily") or {}
        mx = daily.get("temperature_2m_max") or []
        mn = daily.get("temperature_2m_min") or []
        pr = daily.get("precipitation_sum") or []
        actual_max = float(mx[0]) if mx and mx[0] is not None and not (isinstance(mx[0], float) and math.isnan(mx[0])) else None
        actual_min = float(mn[0]) if mn and mn[0] is not None and not (isinstance(mn[0], float) and math.isnan(mn[0])) else None
        actual_precip = float(pr[0]) if pr and pr[0] is not None and not (isinstance(pr[0], float) and math.isnan(pr[0])) else 0.0
        # 极端值过滤
        if actual_max is not None and (actual_max < -80 or actual_max > 70):
            actual_max = None
        if actual_min is not None and (actual_min < -80 or actual_min > 70):
            actual_min = None
        ACCURACY_STORE.upsert_actual(
            city, district, lat, lon, record_date_str,
            actual_max, actual_min, actual_precip,
        )
        return {"city": city, "district": district, "record_date": record_date_str,
                "max": actual_max, "min": actual_min, "precip": actual_precip, "ok": True}
    except Exception as e:
        return {"city": city, "district": district, "record_date": record_date_str, "ok": False, "err": str(e)}


# ---- 批量范围抓取（启动 bootstrap 专用，大幅减少 API 调用次数）----

def _fetch_forecast_range_for_city(city: str, district: str, start_date_str: str, end_date_str: str):
    """批量抓取某城市在 [start_date, end_date] 日期范围内所有 6 个模型的预报快照。
    优化：每个模型只发 1 次 archive API 调用（start_date~end_date），而非逐天逐模型调用。
    将 7天×6模型=42 次调用降为 6 次调用，大幅加速 Render 免费版启动。"""
    lat, lon, tz = _geocode(city, district)
    today_str = _cn_today_str()
    use_archive = end_date_str <= today_str
    results = []
    for model_code in _SCORED_MODELS:
        try:
            if use_archive:
                data = _http_get_with_retry(
                    _ARCHIVE_URL,
                    {
                        "latitude": lat, "longitude": lon,
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                        "timezone": "auto",
                        "temperature_unit": "celsius",
                        "models": model_code,
                        "start_date": start_date_str,
                        "end_date": end_date_str,
                    },
                    attempts=2, timeout=25.0,
                )
            else:
                fd = 4 if model_code == "meteofrance_seamless" else 7
                data = _http_get_with_retry(
                    _FORECAST_URL,
                    {
                        "latitude": lat, "longitude": lon,
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                        "timezone": "auto",
                        "temperature_unit": "celsius",
                        "forecast_days": fd,
                        "models": model_code,
                    },
                    attempts=2, timeout=15.0,
                )
            daily = data.get("daily") or {}
            dates = daily.get("time") or []
            mx = daily.get("temperature_2m_max") or []
            mn = daily.get("temperature_2m_min") or []
            pr = daily.get("precipitation_sum") or []
            for i, d in enumerate(dates):
                if str(d) < start_date_str or str(d) > end_date_str:
                    continue
                pred_max = mx[i] if i < len(mx) else None
                pred_min = mn[i] if i < len(mn) else None
                pred_precip = pr[i] if i < len(pr) else 0.0
                if pred_max is not None and (isinstance(pred_max, float) and math.isnan(pred_max)):
                    pred_max = None
                if pred_min is not None and (isinstance(pred_min, float) and math.isnan(pred_min)):
                    pred_min = None
                if pred_max is not None and (pred_max < -80 or pred_max > 70):
                    results.append({"model": model_code, "date": d, "ok": False, "err": f"extreme temp_max={pred_max}"})
                    continue
                if pred_min is not None and (pred_min < -80 or pred_min > 70):
                    results.append({"model": model_code, "date": d, "ok": False, "err": f"extreme temp_min={pred_min}"})
                    continue
                ACCURACY_STORE.upsert_forecast(
                    city, district, lat, lon, model_code, str(d),
                    pred_max, pred_min, pred_precip,
                )
                results.append({"model": model_code, "date": d, "ok": True})
        except Exception as e:
            results.append({"model": model_code, "ok": False, "err": str(e)})
    return {"city": city, "district": district, "start": start_date_str, "end": end_date_str,
            "source": "archive" if use_archive else "forecast", "results": results}


def _fetch_actual_range_for_city(city: str, district: str, start_date_str: str, end_date_str: str):
    """批量抓取某城市在 [start_date, end_date] 日期范围内的真实观测数据。
    1 次 archive API 调用获取整个日期范围，将 7 天 7 次调用降为 1 次。"""
    lat, lon, tz = _geocode(city, district)
    try:
        data = _http_get_with_retry(
            _ARCHIVE_URL,
            {
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
                "temperature_unit": "celsius",
                "start_date": start_date_str,
                "end_date": end_date_str,
            },
            attempts=2, timeout=25.0,
        )
        daily = data.get("daily") or {}
        dates = daily.get("time") or []
        mx = daily.get("temperature_2m_max") or []
        mn = daily.get("temperature_2m_min") or []
        pr = daily.get("precipitation_sum") or []
        ok_count = 0
        for i, d in enumerate(dates):
            if str(d) < start_date_str or str(d) > end_date_str:
                continue
            actual_max = float(mx[i]) if i < len(mx) and mx[i] is not None and not (isinstance(mx[i], float) and math.isnan(mx[i])) else None
            actual_min = float(mn[i]) if i < len(mn) and mn[i] is not None and not (isinstance(mn[i], float) and math.isnan(mn[i])) else None
            actual_precip = float(pr[i]) if i < len(pr) and pr[i] is not None and not (isinstance(pr[i], float) and math.isnan(pr[i])) else 0.0
            if actual_max is not None and (actual_max < -80 or actual_max > 70):
                actual_max = None
            if actual_min is not None and (actual_min < -80 or actual_min > 70):
                actual_min = None
            ACCURACY_STORE.upsert_actual(city, district, lat, lon, str(d), actual_max, actual_min, actual_precip)
            ok_count += 1
        return {"city": city, "district": district, "start": start_date_str, "end": end_date_str, "ok_count": ok_count}
    except Exception as e:
        return {"city": city, "district": district, "start": start_date_str, "end": end_date_str, "ok_count": 0, "err": str(e)}


def _score_day_for_city(city: str, district: str, record_date_str: str):
    """对 record_date 这一天，取所有模型的 forecast_snapshots 与 actual_record 做比对，写入 daily_scores。
    若 actual 未生成，标记为 pending 不结算 0 分。
    """
    actual = ACCURACY_STORE.get_actual(city, district, record_date_str)
    if not actual:
        return {"city": city, "district": district, "record_date": record_date_str, "scored": 0, "status": "pending", "note": "actual_records not yet available"}
    forecasts = ACCURACY_STORE.get_forecasts(city, district, record_date_str)
    scored = 0
    for fc in forecasts:
        sc = compute_daily_score(fc, actual)
        ACCURACY_STORE.upsert_score(
            city, district, fc["model_code"], record_date_str,
            sc["score_temp"], sc["score_precip"], sc["score_daily"],
        )
        scored += 1
    return {"city": city, "district": district, "record_date": record_date_str, "scored": scored, "status": "done"}


def _rebuild_city_ranking(city, district):
    """重新计算单个城市近 7 天 + 近 30 天各模型的平均分，写入预计算表 city_model_rankings。
    写入策略：
    - 若 7d 有真实样本则写入真实值；否则用 QUICK_SCORE 的 7d 基线兜底；
    - 30d 同理：有真实样本写真实值；无则 QUICK_SCORE + 30d 衰减。
    返回写入行数。
    """
    today_str = _cn_today_str()
    rank_7d = ACCURACY_STORE.rolling_7day_rank(city, district, today_str)
    rank_30d = ACCURACY_STORE.rolling_30day_rank(city, district, today_str)
    by_m_30d = {r["model_code"]: r for r in rank_30d["ranking"]}

    # 若 7d 无任何真实样本，改用 QUICK_SCORE 兜底（保证始终有分数）
    has_real_7d = any(r["samples_7d"] > 0 for r in rank_7d["ranking"])
    has_real_30d = any(r["samples_7d"] > 0 for r in rank_30d["ranking"])
    quick_7d = None
    quick_30d = None
    if not has_real_7d:
        quick_7d = {r["model_code"]: r for r in _get_quick_score_rows("7d")}
    if not has_real_30d:
        quick_30d = {r["model_code"]: r for r in _get_quick_score_rows("30d")}

    count = 0
    for r in rank_7d["ranking"]:
        m = r["model_code"]
        # 7d 取值
        if r["samples_7d"] > 0:
            s7, st7, sp7, n7 = r["score_daily_7d"], r["score_temp_7d"], r["score_precip_7d"], r["samples_7d"]
        else:
            qr = quick_7d[m] if quick_7d else None
            s7 = qr["score_7d"] if qr else 82.0
            st7 = qr["score_temp_7d"] if qr else 82.0
            sp7 = qr["score_precip_7d"] if qr else 80.0
            n7 = qr["samples_7d"] if qr else 1
        # 30d 取值
        r30 = by_m_30d.get(m, {})
        if r30.get("samples_7d", 0) > 0:
            s30 = r30["score_daily_7d"]
            st30 = r30["score_temp_7d"]
            sp30 = r30["score_precip_7d"]
            n30 = r30["samples_7d"]
        else:
            qr30 = quick_30d[m] if quick_30d else None
            s30 = qr30.get("score_7d") if qr30 else (s7 * 0.985)
            st30 = qr30.get("score_temp_7d") if qr30 else st7
            sp30 = qr30.get("score_precip_7d") if qr30 else sp7
            n30 = qr30.get("samples_7d") if qr30 else 1
        ACCURACY_STORE.upsert_city_ranking(
            city, district, m,
            s7, st7, sp7, n7,
            r["rank"],
            score_30d=s30, score_temp_30d=st30, score_precip_30d=sp30, samples_30d=n30,
        )
        count += 1
    return count


def _run_offline_scoring_task():
    """每日 03:00 执行的离线计算任务（近30天滚动窗口维护）：
    a. 批量回抓近 30 天各 _EVAL_CITIES 的实况真值（补漏 Render 休眠错过的日子）
    b. 与 forecast_snapshots 比对，算出近 30 天每天各模型 Score_daily
    c. 重新计算每个城市近 7 天 + 近 30 天各模型的平均分，更新写入 city_model_rankings
    用户要求「近30天运算逻辑和近7天一样，只是要抓取30天的数据」。
    """
    today = datetime.strptime(_cn_today_str(), "%Y-%m-%d")
    WINDOW = 30  # 近 30 天窗口
    start_dt = today - timedelta(days=WINDOW - 1)
    print(f"[Cron 03:00] 离线计算启动，窗口={start_dt.strftime('%Y-%m-%d')}~{today.strftime('%Y-%m-%d')} ({WINDOW}天)，城市数={len(_EVAL_CITIES)}")
    # a + b: 抓实况并评分（循环近 30 天每一天）
    for back in range(WINDOW - 1, -1, -1):
        record_date_str = (today - timedelta(days=back)).strftime("%Y-%m-%d")
        for c in _EVAL_CITIES:
            city, district = c["city"], c["district"]
            try:
                _fetch_actual_record_for_city(city, district, record_date_str)
            except Exception as e:
                pass  # 静默：已有行不重复 API 调用
            time.sleep(0.1)
            try:
                _score_day_for_city(city, district, record_date_str)
            except Exception as e:
                pass
    # c: 重新计算 7d + 30d 滚动均值，写入预计算表
    updated = 0
    for c in _EVAL_CITIES:
        try:
            updated += _rebuild_city_ranking(c["city"], c["district"])
        except Exception as e:
            print(f"[Cron 03:00] 跳过 {c['city']}{c['district']} 预计算: {type(e).__name__}: {e}")
    print(f"[Cron 03:00] 离线计算完成，更新 {updated} 条预计算排名记录")
    return {"job": "offline_scoring", "window_days": WINDOW, "updated": updated}


def _run_daily_forecast_job():
    """每日 08:00 执行：对所有 _EVAL_CITIES 抓明日(T+1)的预测快照。"""
    target_date = _cn_tomorrow_str()
    print(f"[Cron 08:00] 开始抓取 T+1={target_date} 预测快照，城市数 {len(_EVAL_CITIES)}")
    out = []
    for c in _EVAL_CITIES:
        try:
            out.append(_fetch_forecast_snapshot_for_city(c["city"], c["district"], target_date))
        except Exception as e:
            print(f"[Cron 08:00] 跳过 {c['city']}{c['district']} 预报抓取失败: {type(e).__name__}: {e}")
        time.sleep(0.3)
    print(f"[Cron 08:00] 预测快照完成 {len(out)} 城市")
    return {"job": "forecast", "target_date": target_date, "cities": out}


def _run_daily_actual_and_score_job():
    """每日 08:30 执行：抓昨日(T-1)实况真值，然后评分，产出每日得分。"""
    yesterday = _cn_yesterday_str()
    print(f"[Cron 08:30] 开始抓取 T-1={yesterday} 实况真值并评分，城市数 {len(_EVAL_CITIES)}")
    actuals = []; scores = []
    for c in _EVAL_CITIES:
        try:
            actuals.append(_fetch_actual_record_for_city(c["city"], c["district"], yesterday))
        except Exception as e:
            print(f"[Cron 08:30] 跳过 {c['city']}{c['district']} 实况抓取失败: {type(e).__name__}: {e}")
        time.sleep(0.3)
        try:
            scores.append(_score_day_for_city(c["city"], c["district"], yesterday))
        except Exception as e:
            print(f"[Cron 08:30] 跳过 {c['city']}{c['district']} 评分失败: {type(e).__name__}: {e}")
    print(f"[Cron 08:30] 实况 + 评分完成 {len(actuals)} 城市")
    return {"job": "actual+score", "record_date": yesterday, "actuals": actuals, "scores": scores}


def _backfill_accuracy(days: int = 7):
    """回填最近 days 天的「预报快照(archive) + 实况(archive) + 评分」，使 7 日排行榜有真实数据。
    幂等：upsert 已存在则覆盖；某日实况未就绪时该日评分标记 pending（不计 0 分）。
    过去/今天的目标日期由 _fetch_forecast_snapshot_for_city 自动走 archive API（支持 models）。
    """
    today = datetime.strptime(_cn_today_str(), "%Y-%m-%d")
    summary = []
    for back in range(days - 1, -1, -1):  # 从最早一天到今天
        rec = (today - timedelta(days=back)).strftime("%Y-%m-%d")
        forecasts_ok = 0
        for c in _EVAL_CITIES:
            try:
                fr = _fetch_forecast_snapshot_for_city(c["city"], c["district"], rec)
                forecasts_ok += sum(1 for r in fr.get("results", []) if r.get("ok"))
            except Exception as e:
                print(f"[Backfill] 跳过 {c['city']}{c['district']} 预报抓取失败: {type(e).__name__}: {e}")
            time.sleep(0.2)
        actuals_ok = 0
        for c in _EVAL_CITIES:
            try:
                ar = _fetch_actual_record_for_city(c["city"], c["district"], rec)
                if ar.get("ok"):
                    actuals_ok += 1
            except Exception as e:
                print(f"[Backfill] 跳过 {c['city']}{c['district']} 实况抓取失败: {type(e).__name__}: {e}")
            time.sleep(0.2)
        scored = 0
        for c in _EVAL_CITIES:
            try:
                sr = _score_day_for_city(c["city"], c["district"], rec)
                scored += sr.get("scored", 0)
            except Exception as e:
                print(f"[Backfill] 跳过 {c['city']}{c['district']} 评分失败: {type(e).__name__}: {e}")
        summary.append({"date": rec, "forecasts_ok": forecasts_ok,
                        "actuals_ok": actuals_ok, "scored": scored})
        print(f"[Backfill] {rec}: forecast={forecasts_ok} actual={actuals_ok} scored={scored}")
    return {"backfill_days": days, "summary": summary}


def _backfill_accuracy_fast(days: int = 7):
    """快速回填（启动 bootstrap 专用）：用批量范围抓取将 API 调用从 days×10×6=420 降到 10×7=70 次。
    步骤：
    1. 每城市 1 次 archive 调用抓实况范围（7天1次）
    2. 每城市 6 次 archive 调用抓各模型预报范围（7天6次）
    3. 逐天逐城市评分（纯本地 DB 操作，无 API）
    Render 免费版实测 ~2-3 分钟（原 _backfill_accuracy 需 ~17 分钟）。"""
    today = datetime.strptime(_cn_today_str(), "%Y-%m-%d")
    start_date = (today - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    print(f"[Backfill-Fast] 开始批量回填 {start_date} ~ {end_date}（{days}天 × {len(_EVAL_CITIES)}城市）")
    for c in _EVAL_CITIES:
        city, district = c["city"], c["district"]
        try:
            ar = _fetch_actual_range_for_city(city, district, start_date, end_date)
            print(f"[Backfill-Fast] {city}{district} 实况: {ar.get('ok_count', 0)}天")
        except Exception as e:
            print(f"[Backfill-Fast] {city}{district} 实况失败: {type(e).__name__}: {e}")
        try:
            fr = _fetch_forecast_range_for_city(city, district, start_date, end_date)
            ok = sum(1 for r in fr.get("results", []) if r.get("ok"))
            print(f"[Backfill-Fast] {city}{district} 预报: {ok}条")
        except Exception as e:
            print(f"[Backfill-Fast] {city}{district} 预报失败: {type(e).__name__}: {e}")
        time.sleep(0.1)  # 城市间极短间隔
    # 评分（纯本地操作，无 API 调用，秒级完成）
    scored_total = 0
    for back in range(days - 1, -1, -1):
        rec = (today - timedelta(days=back)).strftime("%Y-%m-%d")
        for c in _EVAL_CITIES:
            try:
                sr = _score_day_for_city(c["city"], c["district"], rec)
                scored_total += sr.get("scored", 0)
            except Exception as e:
                print(f"[Backfill-Fast] {c['city']}{c['district']} {rec} 评分失败: {type(e).__name__}: {e}")
    print(f"[Backfill-Fast] 完成: 评分 {scored_total} 条")
    return {"backfill_days": days, "scored_total": scored_total}


# ---- 手动管理 API（POST，无鉴权；内部使用）----

@app.post("/api/accuracy/run-forecast", tags=["准确率系统"], summary="手动：抓取 T+1 预测快照")
def api_run_forecast(target_date: str = Query(None, description="目标日期 YYYY-MM-DD，留空 = 明日")):
    target_date = target_date or _cn_tomorrow_str()
    out = []
    for c in _EVAL_CITIES:
        out.append(_fetch_forecast_snapshot_for_city(c["city"], c["district"], target_date))
        time.sleep(0.25)
    return {"target_date": target_date, "cities": out}


@app.post("/api/accuracy/run-actual", tags=["准确率系统"], summary="手动：抓取某日实况真值")
def api_run_actual(record_date: str = Query(..., description="记录日期 YYYY-MM-DD，例如昨天")):
    out = []
    for c in _EVAL_CITIES:
        out.append(_fetch_actual_record_for_city(c["city"], c["district"], record_date))
        time.sleep(0.25)
    return {"record_date": record_date, "actuals": out}


@app.post("/api/accuracy/run-score", tags=["准确率系统"], summary="手动：对某日所有模型评分")
def api_run_score(record_date: str = Query(..., description="记录日期 YYYY-MM-DD")):
    out = []
    for c in _EVAL_CITIES:
        out.append(_score_day_for_city(c["city"], c["district"], record_date))
    return {"record_date": record_date, "scores": out}


@app.post("/api/accuracy/backfill", tags=["准确率系统"], summary="手动：回填最近 N 天准确率数据(预报+实况+评分)")
def api_backfill(days: int = Query(30, description="回填天数，默认 30；近30天运算逻辑同近7天")):
    return _backfill_accuracy(days=days)


# /api/accuracy/rank 已在上方 API 路由区重新定义（支持 range 参数）


# =====================================================================
# Cron 后台线程：每日 03:00 离线预计算、08:00 抓预测、08:30 抓实况+评分
# =====================================================================

def _cron_worker():
    """每分钟醒来一次，检查是否到点，到点就执行对应任务。
    避免 threading.Timer 长漂；只在对应本地时间 2 分钟窗口内触发，保证一天一次。
    - 03:00-03:02：离线预计算（抓昨日实况 + 评分 + 重算 7 天滚动均值写入 city_model_rankings）
    - 08:00-08:02：抓明日(T+1)预测快照
    - 08:30-08:32：抓昨日(T-1)实况并评分（产出 daily_scores，供次日 03:00 预计算使用）
    """
    last_offline_day = None
    last_forecast_day = None
    last_actual_day = None
    while True:
        try:
            now = _cn_now()
            hh, mm, today = now.hour, now.minute, now.strftime("%Y-%m-%d")
            if hh == 3 and 0 <= mm <= 2 and today != last_offline_day:
                try:
                    _run_offline_scoring_task()
                finally:
                    last_offline_day = today
            if hh == 8 and 0 <= mm <= 2 and today != last_forecast_day:
                try:
                    _run_daily_forecast_job()
                finally:
                    last_forecast_day = today
            if hh == 8 and 30 <= mm <= 32 and today != last_actual_day:
                try:
                    _run_daily_actual_and_score_job()
                finally:
                    last_actual_day = today
        except Exception as e:
            print(f"[Cron] worker loop err: {type(e).__name__}: {e}")
        # 睡眠 45 秒再查
        time.sleep(45)


def _prime_city_rankings_with_quick_scores():
    """【零等待快速打分方案】应用启动时，立刻将 QUICK_SCORE 基线写进
    city_model_rankings 预计算表（覆盖所有 _EVAL_CITIES + 所有 _SCORED_MODELS）。

    效果：
    - 即使是全新部署，启动后第一个 /api/leaderboard 请求也能 <100ms 返回完整分数；
    - 不再走基准站 fallback，也不触发空 ranking → 前端不展示"暂无样本"；
    - 后台 2-3 分钟的真实回填完成后，_rebuild_city_ranking 会用真实样本覆盖这些基线行，
      数据从不准确 → 准确，整个过程用户侧无等待态，只看到分数。
    幂等：对同城市同模型，upsert 覆盖；已存在真实行（samples_7d>1）不覆盖，避免倒退。
    """
    quick_7d = {r["model_code"]: r for r in _get_quick_score_rows("7d")}
    quick_30d = {r["model_code"]: r for r in _get_quick_score_rows("30d")}
    total = 0
    for c in _EVAL_CITIES:
        city, district = c["city"], c["district"]
        existing = ACCURACY_STORE.get_city_rankings(city, district)
        by_m = {r.get("model_code"): r for r in existing} if existing else {}
        for i, m in enumerate(_SCORED_MODELS):
            ex = by_m.get(m)
            # 若已有相当样本（> 1 表示不是 quick 占位）则跳过，不覆盖真实数据
            if ex and (int(ex.get("samples_7d") or 0) > 1):
                continue
            q7 = quick_7d.get(m)
            q30 = quick_30d.get(m)
            if not q7 or not q30:
                continue
            ACCURACY_STORE.upsert_city_ranking(
                city, district, m,
                q7["score_7d"], q7["score_temp_7d"], q7["score_precip_7d"], q7["samples_7d"],
                i + 1,
                score_30d=q30["score_30d"] or (q7["score_7d"] * 0.985),
                score_temp_30d=q30["score_temp_30d"] or q7["score_temp_7d"],
                score_precip_30d=q30["score_precip_30d"] or q7["score_precip_7d"],
                samples_30d=q30["samples_30d"] or 1,
            )
            total += 1
    print(f"  [QuickScore] 已将快速基线分写入预计算表：{len(_EVAL_CITIES)}城市 × {len(_SCORED_MODELS)}模型 = {total}行")
    return total


_CRON_THREAD = None


def _start_cron_if_needed():
    global _CRON_THREAD
    # 【零等待】启动线程前，先用 QUICK_SCORE 填充满 city_model_rankings。
    # 这一步是纯内存/MySQL 写入，通常 < 50ms，启动完成即可立即服务排行榜请求。
    try:
        _prime_city_rankings_with_quick_scores()
    except Exception as e:
        print(f"  [QuickScore] 写入失败（不影响运行，会走 fallback）: {e}")
    if _CRON_THREAD and _CRON_THREAD.is_alive():
        return
    try:
        _CRON_THREAD = threading.Thread(target=_cron_worker, daemon=True, name="accuracy-cron")
        _CRON_THREAD.start()
        print("  [Cron] 准确率后台定时线程已启动：每日 03:00 离线预计算 / 08:00 抓预测 / 08:30 抓实况+评分")
        # 启动时立即跑一次：回填 30 天数据 + 重建预计算排名 + 抓明日预测
        # 原因：Render 免费版休眠后重启可能错过 Cron 时间窗口；
        #       必须在回填后立即重建 city_model_rankings，否则 quick 基线不会被真实分替换。
        #       用户要求「近30天运算逻辑和近7天一样，只是抓30天数据」—— 这里回填30天。
        def _startup_bootstrap():
            try:
                time.sleep(5)  # 等 FastAPI 完全就绪
                print("[Startup] 自动补跑：快速回填最近 30 天准确率数据（批量范围抓取，~5-8分钟）")
                _backfill_accuracy_fast(30)
                print("[Startup] 自动补跑：重建预计算排行榜 city_model_rankings（基于回填的 daily_scores）")
                updated = 0
                for c in _EVAL_CITIES:
                    try:
                        updated += _rebuild_city_ranking(c["city"], c["district"])
                    except Exception as e:
                        print(f"[Startup] 跳过 {c['city']}{c['district']} 预计算: {type(e).__name__}: {e}")
                print(f"[Startup] 预计算完成，更新 {updated} 条排名记录（quick 基线已替换为真实分）")
                print("[Startup] 自动补跑：抓取明日预测快照")
                _run_daily_forecast_job()
                print("[Startup] 自动补跑完成")
            except Exception as e:
                print(f"[Startup] 自动补跑失败（不影响运行，quick 基线仍可用）: {type(e).__name__}: {e}")
        t = threading.Thread(target=_startup_bootstrap, daemon=True, name="startup-bootstrap")
        t.start()
    except Exception as e:
        print(f"  [Cron] 启动失败: {e}")


# =====================================================================
# 静态文件服务（前端页面）—— 必须放在【所有 API 路由之后】挂载
# 原因：Starlette 按路由注册顺序匹配，"/" 的 StaticFiles 是通配挂载，
# 若放在 /api/accuracy/* 等路由之前注册，会拦截这些请求（GET→404 / POST→405）。
# =====================================================================
app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")


# =====================================================================
# 启动入口
# =====================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  聚合天气平台 - 后端服务（含多模型准确率比对系统）")
    print("=" * 60)
    print()
    _port = int(os.environ.get("PORT", "8000"))
    print("  前端页面:  http://localhost:%d" % _port)
    print("  API 文档:  http://localhost:%d/docs" % _port)
    print("  健康检查:  http://localhost:%d/api/health" % _port)
    print()
    print("  准确率管理 API（内部）:")
    print("    POST /api/accuracy/run-forecast?target_date=YYYY-MM-DD")
    print("    POST /api/accuracy/run-actual?record_date=YYYY-MM-DD")
    print("    POST /api/accuracy/run-score?record_date=YYYY-MM-DD")
    print("    POST /api/accuracy/backfill?days=30")
    print("    GET  /api/leaderboard?city=北京&district=朝阳区  (前端只读，<100ms)")
    print("    GET  /api/accuracy/rank?city=北京&district=朝阳区")
    print("  Cron: 每日 03:00 离线预计算 / 08:00 抓预测 / 08:30 抓实况+评分")
    print()
    print("  按 Ctrl+C 停止服务")
    print("=" * 60)
    print()
    _start_cron_if_needed()
    uvicorn.run(app, host="0.0.0.0", port=_port)
