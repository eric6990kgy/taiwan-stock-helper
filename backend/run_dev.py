"""Dev-server launcher that respects an externally-assigned PORT env var.

uvicorn's CLI has no built-in PORT env var support (unlike e.g. Next.js),
so a managed dev-tooling port-conflict-avoidance system (which assigns a
free port via PORT rather than a hardcoded --port flag) has nothing to hook
into without this wrapper. Port 8000 is also permanently blocked by Windows
on this machine (WinError 10013) -- 8010 is the confirmed-working default.
"""

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8010))
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True)
