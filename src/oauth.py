import os
import uuid
import threading

from dotenv import load_dotenv
import httpx
from flask import Flask, request, jsonify
from werkzeug.serving import make_server

load_dotenv()

class OAuth:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = os.getenv("FLASK_SECRET_KEY")
        self.server = make_server("127.0.0.1", "5000", self.app)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True

        self.CLIENT_ID = os.getenv("CLIENT_ID")
        self.CLIENT_SECRET = os.getenv("CLIENT_SECRET")
        self.REDIRECT_URI = "http://localhost:5000/callback"

        self.AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
        self.TOKEN_URL = "https://oauth2.googleapis.com/token"
        self.USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

        self.REQUIRED_SCOPES = [
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ]

        self.sessions = {}

        self.register_routes()

    def register_routes(self):
        self.app.add_url_rule("/callback", "callback", self.callback)

    def start_server(self):
        self.thread.start()
        
    def stop_server(self):
        self.thread.stop()

    def callback(self):
        code = request.args.get("code")
        session_id = request.args.get("state")
        if not code:
            return "Error: No code provided", 400

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
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]

            # Fetch user info
            user_resp = client.get(self.USERINFO_URL, headers={
                "Authorization": f"Bearer {access_token}"
            })
            user_resp.raise_for_status()
            user_info = user_resp.json()
        self.sessions[session_id] = user_info
        return jsonify(user_info)
    
    def get_url_and_session(self):
        session_id = uuid.uuid4()
        self.sessions[session_id] = None

        # redirect_params = {
        #     "session_id": session_id,
        # }
        # redirect_uri = httpx.URL(self.REDIRECT_URI).copy_merge_params(redirect_params)
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
