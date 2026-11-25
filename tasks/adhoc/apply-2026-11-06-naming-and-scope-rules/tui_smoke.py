"""Drive the curses TUI under a pty: 3 discs, two moves, history, quit.

Run inside the python image, from python/: copy to python/ and
`make shell-exec CMD='python3 tui_smoke.py'`, then remove the copy."""

import fcntl
import os
import pty
import select
import struct
import sys
import termios
import time

pid: int
fd: int
pid, fd = pty.fork()
if pid == 0:
    os.environ["TERM"] = "xterm"
    os.execvp("python", ["python", "-m", "hanoigame.hanoigame"])
fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
out: bytes = b""


def pump(seconds: float) -> None:
    global out
    end: float = time.time() + seconds
    while time.time() < end:
        ready, _, _ = select.select([fd], [], [], 0.1)
        if ready:
            try:
                out += os.read(fd, 65536)
            except OSError:
                return


pump(1.0)
for keys in ("3\r", "1 3\r", "1 2\r", "history\r", "quit\r"):
    os.write(fd, keys.encode())
    pump(0.8)
os.write(fd, b"\r")
pump(0.5)
done: tuple[int, int] = os.waitpid(pid, os.WNOHANG)
text: str = out.decode("utf-8", "replace")
sys.stdout.write(f"bytes={len(out)} traceback={'Traceback' in text} exited={done}\n")
sys.stdout.write(f"saw_goal={'Goal' in text} saw_peg={'1' in text}\n")
if "Traceback" in text:
    sys.stdout.write(text[text.index("Traceback"):][:1500] + "\n")
