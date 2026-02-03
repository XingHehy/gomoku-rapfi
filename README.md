## gomoku-rapfi 本地五子棋 AI 服务

这是一个基于 FastAPI 封装的 Rapfi 五子棋 AI 服务接口。

---

## 1. Rapfi-engine 获取与放置

本仓库默认 **不自带** `Rapfi-engine` 目录，需要你自己从 Rapfi 原项目下载后放到本项目根目录下。

获取方式：

- 打开 Rapfi 项目仓库：[`https://github.com/dhbloo/rapfi`](https://github.com/dhbloo/rapfi)
- 进入 Releases 页面，下载对应平台的压缩包（包含 pbrain 可执行文件和模型）
- 解压后，将其中的引擎文件整理到本项目根目录下新建的 `Rapfi-engine` 目录中

目录结构示例：

  - Windows：`pbrain-rapfi-windows-*.exe`
  - Linux：`pbrain-rapfi-linux-clang-*`
  - macOS (Apple Silicon)：`pbrain-rapfi-macos-apple-silicon`

程序会在运行时根据当前系统自动选择合适的可执行文件（见 `app.py` 中的 `_detect_rapfi_binary` 函数），只要文件名和位置保持不变即可。

---

## 2. 本地直接运行（推荐给桌面环境用户）

### 2.1 环境准备

- 已安装 **Python 3.10+**

在项目根目录执行：

```bash
pip install -r requirements.txt
```

### 2.2 启动服务

在项目根目录执行：

```bash
python app.py
```

启动成功后，默认在本机 `8801` 端口提供服务：

- 页面访问：`http://127.0.0.1:8801/` 会返回 `game.html`
- 接口地址：`POST http://127.0.0.1:8801/move`

**接口请求示例（JSON）**：

```json
{
  "board": [
    { "uid": 1, "r": 7, "c": 7 },
    { "uid": 2, "r": 7, "c": 8 }
  ],
  "userid": 1
}
```

- `board`：按落子顺序给出历史棋步  
  - `uid`：玩家 ID，列表中第一个 `uid` 视为先手黑棋  
  - `r` / `c`：行、列坐标，范围 0–14（15×15 棋盘）
- `userid`：当前需要 AI 帮忙落子的那一方（通常是你自己对应的 uid）

返回示例：

```json
{
  "message": "ok",
  "data": { "r": 8, "c": 7 },
  "success": true
}
```

其中 `data` 即为 Rapfi 建议的下一步坐标。

---

## 3. 使用 Docker 运行（推荐给 Linux / 服务器环境）

### 3.1 构建镜像

在项目根目录执行：

```bash
docker build -t gomoku-rapfi .
```

镜像构建过程中会：

- 仅保留 `Rapfi-engine` 中的 **Linux 版本** 引擎二进制
- 安装所需 Python 依赖
- 设置默认启动命令为 `python app.py`

### 3.2 运行容器

```bash
docker run -d --name gomoku-rapfi -p 8801:8801 gomoku-rapfi
```

---

## 5. 其它

- 引擎并发：`EnginePool` 默认根据 CPU 核心数创建多个 Rapfi 实例，以支持并发请求。
- 如果需要修改思考时间，可调整 `engine_pool.py` 中的 `INFO timeout_turn 3000`。
- 引擎参数配置：请自行调整 `Rapfi-engine/config.toml`（不同版本/平台的可用配置项以 Rapfi 官方说明为准）。

如遇到引擎无法启动、模型缺失等问题，优先检查 `Rapfi-engine` 目录是否完整以及当前系统架构是否支持对应二进制文件。


