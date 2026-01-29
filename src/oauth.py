import os
import uuid
import threading

import httpx
from starlette.responses import PlainTextResponse
from starlette.exceptions import HTTPException
from starlette.routing import Route, Router, Mount
from starlette.applications import Starlette
import uvicorn

class OAuth:
    def __init__(self):
        self.routes = [
            Route("/callback", endpoint=self.callback),
        ]

        self.REDIRECT_URI = f"{os.getenv("DOMAIN")}/auth/callback"
        self.CLIENT_ID = os.getenv("CLIENT_ID")
        self.CLIENT_SECRET = os.getenv("CLIENT_SECRET")

        self.AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
        self.TOKEN_URL = "https://oauth2.googleapis.com/token"
        self.USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

        self.REQUIRED_SCOPES = [
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/calendar",
            "openid",
        ]

        self.sessions = {}

    # For stdio mode
    def run(self):
        def run_server(app):
            try:
                uvicorn.run(app, host="127.0.0.1", port=5000, log_level="error", access_log=False)
            except:
                os._exit(1)
        self.app = Starlette(debug=True, routes=[Mount('/auth', routes=self.routes)])
        self.server_thread = threading.Thread(
            target=run_server,
            args=(self.app,),
            daemon=True,
        )
        self.server_thread.start()

    # For http mode
    def get_asgi_app(self):
        return Router(routes=self.routes)

    async def callback(self, request):
        if "code" not in request.query_params or "state" not in request.query_params:
            return PlainTextResponse("Query params missing key 'code' or 'state'", status_code=404)
        code = request.query_params["code"]
        session_id = request.query_params["state"]

        # Exchange authorization code for tokens
        token_data = {
            "code": code,
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "redirect_uri": self.REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        with httpx.Client() as client:
            token_resp = client.post(self.TOKEN_URL, data=token_data)
            if not token_resp.is_success:
                return PlainTextResponse("Request for access token failed", status_code=500)
            access_token = token_resp.json()["access_token"]

            user_resp = client.get(self.USERINFO_URL, headers={
                "Authorization": f"Bearer {access_token}"
            })
            if not user_resp.is_success:
                return PlainTextResponse("Request for user info failed", status_code=500)
        user_info = user_resp.json()
        user_info["access_token"] = access_token
        self.sessions[session_id] = user_info
        return PlainTextResponse("Success")
    
    def get_url_and_session(self):
        session_id = uuid.uuid4()
        self.sessions[session_id] = None

        auth_params = {
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(self.REQUIRED_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": session_id,
        }
        url = httpx.URL(self.AUTH_URL).copy_merge_params(auth_params)
        return url, session_id
    
    def get_access_token(self, session_id):
        if session_id not in self.sessions:
            return None
        return self.sessions[session_id]["access_token"]
