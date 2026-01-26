from mcp.server.fastmcp import FastMCP
import logging

from oauth import OAuth

class CalendarMcp:
    def __init__(self):
        self.auth = OAuth()        
        self.mcp = FastMCP("calendar")

        self.register_tools()

    def register_tools(self):
        self.get_url = self.mcp.tool()(self.get_url)
        self.get_user = self.mcp.tool()(self.get_user)

    def run(self):
        self.auth.start_server()
        self.mcp.run(transport="stdio")

    def get_url(self) -> str:
        """
        Get OAuth url and session_id to login to google calendar, must give user time to log in
        """
        url, session_id = self.auth.get_url_and_session()
        return f"""
            URL: {url}
            session_id: {session_id}
        """

    def get_user(self, session_id: str) -> str:
        """Get user information
        This assumes that OAuth url has been received and user has gone through with authentication

        Args:
            session_id: Session id obtained from get_url
        """
        if session_id not in self.auth.sessions:
            return "User has not logged in yet"
        session_data = self.auth.sessions[session_id]
        return f"""
            email: {session_data["email"]}
            name: {session_data["name"]}
            id: {session_data["sub"]}
        """
