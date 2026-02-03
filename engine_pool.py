import subprocess
import threading
import queue
import time
import re


class RapfiEngine:

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.start()

    def start(self):

        self.proc = subprocess.Popen(
            [self.path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1
        )

        self.send("START 15")
        # 吃掉启动阶段可能的若干行输出，避免污染后续读取
        self._drain_startup()

        # 限制思考时间（3秒）
        self.send("INFO timeout_turn 3000")

    def restart(self):
        try:
            self.proc.kill()
        except:
            pass
        self.start()

    def send(self, cmd):
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def read(self):
        return self.proc.stdout.readline().strip()

    def _drain_startup(self, max_lines: int = 50, max_seconds: float = 1.0):
        """
        Rapfi(pbrain) 启动后可能输出若干行（如 OK/INFO/版本信息）。
        这里做有限读取，避免把第一步 DONE 的结果读歪。
        """
        start = time.monotonic()
        for _ in range(max_lines):
            if time.monotonic() - start > max_seconds:
                break
            line = self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line == "":
                continue
            # 一般会有一行 OK，读到就结束
            if line.upper() == "OK":
                break

    def _read_bestmove_xy(self, max_lines: int = 200, max_seconds: float = 5.0):
        """
        读取引擎输出，直到拿到形如 'x,y' 的坐标。
        允许中间夹杂 OK/INFO 等杂讯行。
        """
        start = time.monotonic()
        last_nonempty = ""
        pat = re.compile(r"^\s*(-?\d+)\s*,\s*(-?\d+)\s*$")
        for _ in range(max_lines):
            if time.monotonic() - start > max_seconds:
                raise RuntimeError(f"engine timeout waiting bestmove, last='{last_nonempty}'")
            line = self.proc.stdout.readline()
            if line == "":
                # 进程退出/管道关闭
                raise RuntimeError(f"engine exited unexpectedly, last='{last_nonempty}'")
            line = line.strip()
            if not line:
                continue
            last_nonempty = line
            m = pat.match(line)
            if m:
                x = int(m.group(1))
                y = int(m.group(2))
                return x, y
            # 忽略其它输出（例如 OK / INFO ...)
        raise RuntimeError(f"engine did not return x,y within {max_lines} lines, last='{last_nonempty}'")

    def best_move(self, moves):

        with self.lock:

            try:
                self.send("BOARD")

                for i, m in enumerate(moves):

                    # 兼容 {"r": "7", "c": "7"} / {"r": 7, "c": 7}
                    x = int(m["c"])
                    y = int(m["r"])

                    player = 1 if i % 2 == 0 else 2

                    self.send(f"{x},{y},{player}")

                self.send("DONE")

                x, y = self._read_bestmove_xy()

                return {"r": int(y), "c": int(x)}

            except Exception as e:

                print("engine crashed -> restarting", e)
                self.restart()
                raise


class EnginePool:

    def __init__(self, path, size=6):

        self.pool = queue.Queue()

        for _ in range(size):
            self.pool.put(RapfiEngine(path))

    def acquire(self):
        return self.pool.get()

    def release(self, engine):
        self.pool.put(engine)

    def best_move(self, moves):

        engine = self.acquire()

        try:
            return engine.best_move(moves)
        finally:
            self.release(engine)
