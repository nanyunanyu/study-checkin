"""启动入口：读取 PORT 环境变量并绑定 0.0.0.0，供托管环境直接运行 `python server.py`。

本地开发也可以用它：`PORT=8000 python server.py`
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
