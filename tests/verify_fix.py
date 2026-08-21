"""验证脚本：用本地坐标(北京)实测 timezone=auto 是否生效、四大模型温度是否合理、
以及准确率评分链路是否有数据空洞。"""
import sys, json, os
# 脚本位于仓库根 tests/，需把 backend 目录加入导入路径才能 import app
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "deliverables", "backend"))
import app as app_mod

_URL = "https://api.open-meteo.com/v1/forecast"
_LAT, _LON = 39.9042, 116.4074  # 北京本地坐标

print("=" * 70)
print("【1】timezone=auto 是否生效（对比默认 UTC）")
print("=" * 70)
base = {"latitude": _LAT, "longitude": _LON, "current": "temperature_2m",
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "celsius", "forecast_days": 1}
r_auto = app_mod._http_get_with_retry(_URL, {**base, "timezone": "auto"}, attempts=1, timeout=15)
r_utc = app_mod._http_get_with_retry(_URL, {**base}, attempts=1, timeout=15)  # 不加 timezone => 默认 UTC
print(f"auto: tz={r_auto['timezone']} offset={r_auto['utc_offset_seconds']}s "
      f"current.time={r_auto['current']['time']} temp={r_auto['current']['temperature_2m']}℃ "
      f"daily={r_auto['daily']['time']}")
print(f"utc : tz={r_utc['timezone']} offset={r_utc['utc_offset_seconds']}s "
      f"current.time={r_utc['current']['time']} temp={r_utc['current']['temperature_2m']}℃ "
      f"daily={r_utc['daily']['time']}")
print("=> 若 auto 返回 Asia/Shanghai 且 current.time 为本地时间，则 timezone=auto 生效。")

print()
print("=" * 70)
print("【2】四大模型当前温度（本地坐标, timezone=auto+celsius）")
print("=" * 70)
models = {"ecmwf_ifs025": "欧洲中心底座", "icon_seamless": "德国气象底座(DWD)",
          "jma_seamless": "东亚高分辨(日本)", "meteofrance_seamless": "法国底座"}
for mc, name in models.items():
    try:
        r = app_mod._http_get_with_retry(
            _URL, {"latitude": _LAT, "longitude": _LON, "current": "temperature_2m",
                   "timezone": "auto", "temperature_unit": "celsius", "models": mc},
            attempts=2, timeout=15)
        print(f"  {name}({mc}): {r['current']['temperature_2m']}℃  tz={r['timezone']} t={r['current']['time']}")
    except Exception as e:
        print(f"  {name}({mc}): 错误 {type(e).__name__}: {e}")

print()
print("=" * 70)
print("【3】准确率评分链路数据空洞验证（以昨天为例, 朝阳区）")
print("=" * 70)
city, dist = "北京", "朝阳区"
y = app_mod._cn_yesterday_str()
print(f"昨天日期={y}")
af = app_mod._fetch_actual_record_for_city(city, dist, y)
print(f"实况抓取: {json.dumps(af, ensure_ascii=False)}")
fc = app_mod._fetch_forecast_snapshot_for_city(city, dist, y)
print(f"预报快照抓取(用预报API): {json.dumps(fc, ensure_ascii=False)}")
# 检查 get_forecasts 是否能取到昨天的预报
fc_stored = app_mod.ACCURACY_STORE.get_forecasts(city, dist, y)
print(f"DB/内存中昨天预报快照条数={len(fc_stored)}")
sc = app_mod._score_day_for_city(city, dist, y)
print(f"评分结果: {json.dumps(sc, ensure_ascii=False)}")
