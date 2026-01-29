import os

from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Mount
import uvicorn

from calendar_mcp import CalendarMcp
from oauth import OAuth

load_dotenv()

if __name__ == "__main__":
    auth = OAuth()
    mcp = CalendarMcp(auth)
    if os.getenv("MODE") == "stdio":
        auth.run()
        mcp.run() # blocking
    elif os.getenv("MODE") == "http":
        mcp_app = mcp.get_asgi_app()
        auth_app = auth.get_asgi_app()
        server = Starlette(
            routes=[
                Mount("/mcp", app=mcp_app),
                Mount("/auth", app=auth_app)
            ],
            lifespan=mcp_app.lifespan,
        )
        uvicorn.run(server, host="0.0.0.0", port=5000)
    else:
        print("env variable MODE must either be 'stdio' or 'http'")
