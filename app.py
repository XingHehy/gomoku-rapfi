from pathlib import Path
import os
import platform
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from engine_pool import EnginePool

app = FastAPI()
_ROOT = Path(__file__).resolve().parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("gomoku")


def _detect_rapfi_binary() -> str:
    """
    根据当前操作系统自动选择合适的 Rapfi 引擎可执行文件（项目内相对路径）。
    若找不到可用引擎，则抛出异常。
    """
    base = _ROOT / "Rapfi-engine"
    system = platform.system()

    if system == "Windows":
        # 优先级：指令集越高越靠前；实际是否能跑由用户 CPU 决定
        candidates = [
            "pbrain-rapfi-windows-avx512vnni.exe",
            "pbrain-rapfi-windows-avx512.exe",
            "pbrain-rapfi-windows-avxvnni.exe",
            "pbrain-rapfi-windows-avx2.exe",
            "pbrain-rapfi-windows-sse.exe",
        ]
    elif system == "Linux":
        candidates = [
            "pbrain-rapfi-linux-clang-avx512vnni",
            "pbrain-rapfi-linux-clang-avx512",
            "pbrain-rapfi-linux-clang-avxvnni",
            "pbrain-rapfi-linux-clang-avx2",
            "pbrain-rapfi-linux-clang-sse",
        ]
    elif system == "Darwin":  # macOS
        candidates = [
            "pbrain-rapfi-macos-apple-silicon",
        ]
    else:
        raise RuntimeError(f"不支持的操作系统: {system}")

    for name in candidates:
        path = base / name
        if path.is_file():
            return str(path)

    raise RuntimeError(f"在 {base} 下未找到可用的 Rapfi 引擎文件")


# 允许网页脚本（如 Tampermonkey）跨域调用本地接口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

pool = EnginePool(
    path=_detect_rapfi_binary(),
    size=os.cpu_count() or 4,  # 默认使用 CPU 核心数
)

class MoveIn(BaseModel):
    uid: int
    r: int = Field(ge=0, le=14)
    c: int = Field(ge=0, le=14)


class BestMoveReq(BaseModel):
    board: list[MoveIn] = Field(default_factory=list)
    userid: int


def _turn_check_and_normalize(board: list[MoveIn], userid: int):
    """
    返回 (ok, message, moves_for_engine)
    - ok=False 时不应调用引擎
    - moves_for_engine: [{"r":int,"c":int}, ...] 按落子顺序
    """
    # 规则：list 第一个 uid 为先手黑子
    # 语义：userid 表示“需要 AI 帮忙下棋的那一方（通常是用户）”
    if not board:
        # 空棋盘：默认允许 userid 先手（黑）
        return True, "ok", []

    uids = []
    for m in board:
        if m.uid not in uids:
            uids.append(m.uid)
    if len(uids) > 2:
        return False, "棋局包含超过2个玩家uid，无法判断轮次", []

    black_uid = board[0].uid
    # 推断白方 uid：
    # - 如果棋局里已经出现第二个 uid，用它
    # - 如果目前只出现黑方：允许 userid 作为白方第一次加入（若 userid != black_uid）
    white_uid = None
    for uid in uids:
        if uid != black_uid:
            white_uid = uid
            break
    if white_uid is None:
        if userid == black_uid:
            # 只有黑方落子且 userid 是黑方：下一手应轮到白方（还没出现）
            return False, "还没有轮到您", []
        white_uid = userid

    if userid not in (black_uid, white_uid):
        return False, "userid不在该棋局中", []

    expected_uid = black_uid if (len(board) % 2 == 0) else white_uid
    if expected_uid != userid:
        return False, "还没有轮到您", []

    moves_for_engine = [{"r": m.r, "c": m.c} for m in board]
    return True, "ok", moves_for_engine


@app.post("/move")
def move(req: BestMoveReq):
    try:
        raw_moves = [{"uid": m.uid, "r": m.r, "c": m.c} for m in req.board]
        logger.info("收到下棋请求: userid=%s, 步数=%d, 原始数据=%s", req.userid, len(raw_moves), raw_moves)

        ok, msg, moves = _turn_check_and_normalize(req.board, req.userid)
        if not ok:
            logger.info("请求非法，未调用引擎: userid=%s, 原因=%s", req.userid, msg)
            return {"message": msg, "data": None, "success": False}

        best = pool.best_move(moves)
        logger.info(
            "引擎返回落子: userid=%s, 已有步数=%d, 返回=%s",
            req.userid,
            len(moves),
            best,
        )
        return {"message": "ok", "data": best, "success": True}
    except Exception as e:
        logger.exception("调用引擎异常: userid=%s", req.userid)
        return {"message": f"engine error: {e}", "data": None, "success": False}


@app.get("/")
def game_page():
    return FileResponse(_ROOT / "game.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8801, reload=False)
