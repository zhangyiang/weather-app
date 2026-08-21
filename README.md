# 聚合天气 · Aggregate Weather

一款「准确率透明化」的天气聚合应用：聚合多个气象数据源（ECMWF / GFS / CMA-MESO / 彩云短临 / PWS），展示各家预报与实况对比，并内置社区实拍、排行榜与可选的 AI 天气解读。

- 在线地址：https://weather-app-pdw4.onrender.com
- 代码仓库：https://github.com/zhangyiang/weather-app

---

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | 纯 HTML + 原生 JavaScript（PWA，无框架依赖），`localStorage` 存登录态 |
| 后端 | Python · FastAPI + Uvicorn（端口 8000） |
| 部署 | Docker + Render（Blueprint 自动部署） |
| 数据存储 | MySQL（可选）；无 MySQL 时优雅降级为内存 / 本地 JSON |
| AI 解读 | SiliconFlow（Qwen/Qwen2.5-7B-Instruct，可选，未配 Key 则降级） |

---

## 目录结构

```
555/
├─ deliverables/                  # 项目主交付物
│  ├─ Dockerfile                  # 后端镜像构建（已上传）
│  ├─ .dockerignore               # Docker 构建排除（已上传）
│  ├─ render.yaml                 # Render Blueprint 部署配置（已上传）
│  ├─ backend/
│  │  ├─ app.py                   # 核心 FastAPI 后端：天气/排行/社区/鉴权/AI 等 14+ 接口（已上传）
│  │  ├─ requirements.txt         # Python 依赖（已上传）
│  │  ├─ start.sh                 # Linux/macOS 启动脚本（已上传）
│  │  ├─ start_server.bat         # Windows 启动脚本：venv 启动→轮询 /api/health→开浏览器（已上传）
│  │  ├─ _verify_fix.py           # 修复验证测试脚本（已上传）
│  │  ├─ config.json              # ⚠️ 本地真实配置（含密钥），已被 .gitignore 忽略，未上传
│  │  ├─ config.example.json      # 配置示例模板（被 gitignore 误伤，未上传）
│  │  ├─ app_data.json            # 运行时 JSON 持久化（用户/动态，降级存储），未上传
│  │  └─ _srv_new.log / ......_srv.log  # 后端运行日志，未上传
│  ├─ html-prototype/             # 前端原型
│  │  ├─ index.html               # 主页面（vanilla JS）（已上传）
│  │  ├─ data.json                # 静态城市配置（已上传）
│  │  ├─ sw.js / manifest.webmanifest  # PWA Service Worker 与清单（已上传）
│  │  ├─ icons/                   # PWA 图标（png/svg，已上传）
│  │  ├─ test_data.js             # 前端 Mock 数据（模拟后端 API），未上传
│  │  └─ _gen_districts.py / _gen_icons.py  # 区县/图标生成脚本，未上传
│  ├─ deploy/
│  │  ├─ 部署指南.md              # Render 部署步骤（已上传）
│  │  └─ 移动端打包指南.md        # PWA/移动端打包指南（已上传）
│  └─ product-strategy/
│     └─ prd-weather-aggregator-2026-08-01.md  # 产品需求文档 PRD（已上传）
├─ .gitignore                     # 忽略规则：密钥/日志/缓存/构建产物/本地配置（已上传）
├─ fix_koyeb_dns.ps1              # 早期 Koyeb 平台 DNS 修复脚本（已上传）
├─ test_platforms.ps1            # 多平台（Render/Koyeb 等）部署测试脚本（已上传）
├─ test_js.js                     # 前端 JS 语法/逻辑测试（Node 运行，已上传）
├─ overview.md / overview-*.md    # 各次修复与改动概览笔记（本地，未上传）
├─ _srv.log / _srv.err.log        # 根目录运行日志（本地，未上传）
└─ deliverables/backend-arch-prompt.md / backend-architecture-design.md  # 后端架构设计（本地，未上传）
```

> 标注「已上传」= 已提交并推送到 GitHub `main`（commit `cd4edf5`）；「未上传」= 被 `.gitignore` 忽略的本地文件。

---

## 本地运行

前置：Python 3.10+（推荐用虚拟环境）。

```bash
cd deliverables/backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 准备配置：复制示例（注意 config.example.json 目前被 gitignore 忽略，可手动从 config.json 改）
cp config.json config.local.json   # 或直接编辑 config.json，填入 jwt_secret / 可选 llm_api_key

python app.py                      # 默认 http://127.0.0.1:8000
```

前端：`deliverables/html-prototype/index.html` 需通过 HTTP 访问（fetch 在 `file://` 下会被 CORS 拦截），可用任意静态服务器，例如：

```bash
cd deliverables/html-prototype && python -m http.server 8080
```

> 读接口（天气/排行等）默认使用内存 Mock 数据，无需后端即可浏览原型；用户系统（注册/登录/点赞/评论）需后端运行。无 MySQL 时数据存内存，重启清空。

---

## 部署（Render）

仓库关联 Render 后，用 Blueprint 自动建服务：

1. Render 控制台 → New → Blueprint → 选择本仓库。
2. Blueprint Path 填 `deliverables/render.yaml`。
3. 环境变量：`JWT_SECRET` 自动生成；`LLM_API_KEY` 可选（不填则 AI 解读降级）；`MYSQL_*` 免费套餐可不配（自动降级内存存储）。
4. `autoDeploy: true`，推送 `main` 即自动重新部署。

---

## 配置说明

后端按以下优先级读取配置（后者覆盖前者）：`代码默认值` → `config.json`（本地）→ `环境变量`（云部署）。

| 项 | 说明 | 来源 |
| --- | --- | --- |
| `JWT_SECRET` | 签名 JWT 的密钥 | 环境变量 / config.json `jwt_secret` |
| `LLM_API_KEY` | SiliconFlow Key（可选） | 环境变量 / config.json `llm_api_key` |
| `LLM_BASE_URL` / `LLM_MODEL` | 模型接口与名称 | 环境变量 / config.json |
| `MYSQL_HOST/USER/PASSWORD/DATABASE` | MySQL 连接（可选） | 环境变量 / config.json `mysql` |

---

## 安全与隐私

- ✅ **真实密钥不入库**：`config.json`（含 SiliconFlow API Key、JWT 密钥、MySQL 密码）已被 `.gitignore` 忽略，**从未提交到 git**，公开仓库不含任何可用密钥。
- ✅ **日志与本地数据不上传**：`*.log`、`app_data.json`、`_srv*.log` 均被忽略，不会泄露运行时用户数据或请求痕迹。
- ⚠️ **默认 JWT 密钥偏弱**：`app.py` 第 520 行写死 `jwt_secret = "dev-secret-change-me"`。在 Render 上由 `JWT_SECRET` 环境变量自动覆盖，因此线上安全；但**任何人 clone 本仓库后若未设置 `JWT_SECRET` 直接运行，可伪造任意用户 token**。生产环境务必设置强随机 `JWT_SECRET`，或将其改为「缺失即启动失败」。
- 🔐 **建议**：本地 `config.json` 中的真实 API Key 虽未泄露，仍建议到 SiliconFlow 后台轮换一次；任何时候不要用 `git add -f` 强制加入被忽略的密钥文件。
- 📌 小提示：`config.example.json` 被 `config.*.json` 规则误伤而未上传，若希望对外提供模板，可在 `.gitignore` 末尾加 `!deliverables/backend/config.example.json` 放行。

---

## API 概览（后端）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查（含 build tag） |
| GET | `/api/weather` | 聚合天气数据（多源 + 准确率） |
| GET | `/api/ranking` | 数据源准确率排行榜（请求驱动懒更新） |
| GET | `/api/source` | 数据源列表 |
| POST | `/api/auth/register` | 注册（用户名+邮箱+密码，bcrypt） |
| POST | `/api/auth/login` | 登录（用户名/邮箱+密码，返回 JWT） |
| GET | `/api/user/profile` | 当前用户资料（需 Bearer Token） |
| GET/POST | `/api/feeds` · `/api/feeds/:id/toggle-like` · `/api/feeds/:id/comments` | 社区动态、点赞、评论 |
| POST | `/api/ai-weather` | AI 天气解读（可选 LLM） |
| GET | `/api/cities` | 城市列表 |

完整清单见 `deliverables/backend/app.py`。

---

## 许可证

未声明。如需开源请补充 LICENSE。
