from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
import logging
import httpx

from oauth import OAuth

CALENDAR_API = "https://www.googleapis.com/calendar/v3"

class CalendarMcp:
    def __init__(self):
        self.auth = OAuth()        
        self.mcp = FastMCP("calendar")

        self.MCP_DESCRIPTION = "Generated via calendar-mcp"

        self.register_tools()

    def run(self):
        self.auth.start_server()
        self.mcp.run(transport="stdio")

    def register_tools(self):
        self.get_url = self.mcp.tool()(self.get_url)
        self.verify_login = self.mcp.tool()(self.verify_login)
        self.get_user = self.mcp.tool()(self.get_user)
        self.list_calendars = self.mcp.tool()(self.list_calendars)
        self.create_calendar = self.mcp.tool()(self.create_calendar)
        self.patch_calendar = self.mcp.tool()(self.patch_calendar)
        self.delete_calendar = self.mcp.tool()(self.delete_calendar)
        self.list_events = self.mcp.tool()(self.list_events)
        self.insert_event = self.mcp.tool()(self.insert_event)
        self.patch_event = self.mcp.tool()(self.patch_event)
        self.delete_event = self.mcp.tool()(self.delete_event)

    def get_url(self) -> str:
        """
            Purpose: Get an OAuth URL and session ID to log in to Google Calendar.
            Usage: Triggered when the user requests login (e.g., "log me into calendar") or runs a command that requires a login.
            Instructions for the model:
            - Provide the OAuth URL and session ID exactly as given. Do not modify them. ENSURE it is the same
            - Do not attempt to verify login or make any tool calls.
            - Do not generate new URLs or provide additional instructions unless the user requests it.
            - Only respond with the URL or acknowledge user input.
            - Put the URL in the chat even if it is redundant
            - The session ID is for internal use not for the user
        """
        url, session_id = self.auth.get_url_and_session()
        return f"""
            URL: {url}
            session_id: {session_id}
        """

    def verify_login(self, session_id: str) -> str:
        """
        Verify whether the user has successfully logged in with the url provided.
        Log in only needs to be verified once.

        Args:
            session_id: Session id obtained from get_url
        """
        return f"Logged in: {session_id in self.auth.sessions}"

    def get_user(self, session_id: str) -> str:
        """
        Get user information
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

    def list_calendars(self, session_id: str) -> str:
        """
        List calendars, assumes user has gone through with authentication.
        Use if a given calendar_id is unknown.
        Args:
            session_id: Session id obtained from get_url
        """
        with httpx.Client() as client:
            res = client.get(
                f"{CALENDAR_API}/users/me/calendarList", 
                headers={"Authorization": f"Bearer {self.auth.get_access_token(session_id)}"},
            )
            res.raise_for_status()
            res_json = res.json()
        output_str = "Calendars:\n"
        for item in res_json["items"]:
            output_str += f"Name: {item["summary"]}\nId: {item["id"]}\n\n"
        return output_str

    def create_calendar(self, session_id: str, calendar_name: str) -> str:
        """
        Creates a new calendar, assumes user has gone through with authentication
        Args:
            session_id: Session id obtained from get_url
            calendar_name: Name of new calendar (ask for this if user does not provide)
        """
        with httpx.Client() as client:
            res = client.post(
                f"{CALENDAR_API}/calendars",
                headers={"Authorization": f"Bearer {self.auth.get_access_token(session_id)}"},
                json={"summary": calendar_name, "description": self.MCP_DESCRIPTION},
            )
            res.raise_for_status()
            calendar_id = res.json()["id"]
        return f"calendar_id: {calendar_id}"

    def patch_calendar(self, session_id: str, calendar_id: str, new_calendar_name: str) -> str:
        """
        Patches an exissting calendar, assumes user has gone through authentication
        Args:
            session_id: Session id obtained from get_url
            calendar_id: Id of calendar either form create_calendar or list_calendars
            new_calenar_name: New calendar name
        """
        with httpx.Client() as client:
            res = client.get(
                f"{CALENDAR_API}/calendars/{calendar_id}",
                headers={"Authorization": f"Bearer {self.auth.get_access_token(session_id)}"},
            )
            res.raise_for_status()
            if res.json()["description"] != self.MCP_DESCRIPTION:
                return f"Failed to delete: calendar_id {calendar_id} was not generated by MCP"

            res = client.patch(
                f"{CALENDAR_API}/calendars/{calendar_id}",
                headers={"Authorization": f"Bearer {self.auth.get_access_token(session_id)}"},
                json={"summary": new_calendar_name}
            )
            res.raise_for_status()
        return f"""
            Successfully patched calendar
            calendar_id: {calendar_id}
        """


    def delete_calendar(self, session_id: str, calendar_id: str) -> str:
        """
        Deletes a calendar, calendar must have been created by calendar mcp either in current or previous session.
        Assumes user has gone through authentication
        Args:
            session_id: Session id obtained from get_url
            calendar_id: Id of calendar either from create_calendar or list_calendars
        """
        with httpx.Client() as client:
            res = client.get(
                f"{CALENDAR_API}/calendars/{calendar_id}",
                headers={"Authorization": f"Bearer {self.auth.get_access_token(session_id)}"},
            )
            res.raise_for_status()
            if res.json()["description"] != self.MCP_DESCRIPTION:
                return f"Failed to delete: calendar_id {calendar_id} was not generated by MCP"

            res = client.delete(
                f"{CALENDAR_API}/calendars/{calendar_id}",
                headers={"Authorization": f"Bearer {self.auth.get_access_token(session_id)}"},
            )
            res.raise_for_status()
        return f"calendar_id: {calendar_id}"""

    def list_events(self, session_id: str, calendar_id: str):
        """
        Lists the events on a calendar, good for verifying if events were all inserted correctly.
        Assumes user has gone through authentication.
        Args:
            session_id: Session id obtained from get_url
            calendar_id: Id of calendar either from create_calendar or list_calendars
        """
        with httpx.Client() as client:
            res = client.get(
                f"{CALENDAR_API}/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {self.auth.get_access_token(session_id)}"},
            )
            res.raise_for_status()
            events_list = res.json()["items"]
        output_str = ""
        for event in events_list:
            output_str += f"""
                event_id: {event["id"]}
                name: {event.get("summary", "n/a")}
                description: {event.get("description", "n/a")}
                start: {event["start"]["dateTime"]} {event["start"]["timeZone"]}
                end: {event["end"]["dateTime"]} {event["end"]["timeZone"]}
                location: {event.get("location", "n/a")}
                repition/recurrence_rules: {" ".join(event.get("recurrence", []))}
            """
        return output_str

    def insert_event(
        self,
        session_id: str,
        calendar_id: str,
        event_name: str,
        time_zone: str,
        start_date_time: str,
        end_date_time: str,
        location: str | None = None,
        repeats: bool = False,
        repeat_days: str | None = None,
        final_repeat_date: str | None = None,
    ) -> str:
        """
        Inserts a new calendar event, assumes user has gone through with authentication
        All datetime arguments are formatted as such YYYY-MM-DDTHH:MM:SS (do not include Z at the end)
        Weekday abbreviations are according to RFC: SU, MO, TU, WE, TH, FR, SA
        Assumes user has gone through authentication
        Args:
            session_id: Session id obtained from get_url
            calendar_id: The id of calendar the event should be added to, is returned from create_calendar
            event_name: The name of the event that will show up in the calendar
            time_zone: The time zone the event will take place in (ask user if unknown) formatted according to IANA time zone database such as America/New_York
            start_date_time: The start time of the event, the start of the first event if the event repeats
            end_date_time: The end time of the event, the end of the first event if the event repeats
            location: The location of the event (optional)
            repeats: Whether the event repeats or not (optional default False) 
            repeat_days: A string containing the days that the event repeats weekly comma separated (i.e. TU,TH) (optional)
            final_repeat_date: A datetime string indicating the cutoff date for repetitions, it does not need to fall on an event occurrence. (ask user if unknown) If time is unknown just use midnight (optional)
        """
        input_json = {
            "start": {
                "dateTime": start_date_time,
                "timeZone": time_zone,
            },
            "end": {
                "dateTime": end_date_time,
                "timeZone": time_zone,
            },
            "description": self.MCP_DESCRIPTION,
            "summary": event_name,
        }
        if location: input_json["location"] = location
        if repeats:
            final_dt = datetime.strptime(final_repeat_date, "%Y-%m-%dT%H:%M:%S")
            final_dt = final_dt.replace(tzinfo=timezone.utc)
            final_dt_reformatted = final_dt.strftime("%Y%m%dT%H%M%SZ")
            input_json["recurrence"] = [
                f"RRULE:FREQ=WEEKLY;UNTIL={final_dt_reformatted};WKST=SU;BYDAY={repeat_days}"
            ]

        with httpx.Client() as client:
            res = client.post(
                f"{CALENDAR_API}/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {self.auth.get_access_token(session_id)}"},
                json=input_json,
            )
            res.raise_for_status()
            event_id = res.json()["id"]
        return f"""
            event_name: {event_name}
            event_id: {event_id}
        """

    def patch_event(
        self,
        session_id: str,
        calendar_id: str,
        event_id: str,
        new_event_name: str | None = None,
        new_time_zone: str | None = None,
        new_start_date_time: str | None = None,
        new_end_date_time: str | None = None,
        new_location: str | None = None,
        repeats: bool = False,
        repeat_days: str | None = None,
        final_repeat_date: str | None = None,
    ) -> str:
        """
        Patches an event with updated information
        All datetime arguments are formatted as such YYYY-MM-DDTHH:MM:SS (do not include Z at the end)
        Weekday abbreviations are according to RFC: SU, MO, TU, WE, TH, FR, SA
        Assumes user has gone through authentication
        Args:
            session_id: Session id obtained from get_url
            calendar_id: The id of calendar the event should be added to, is returned from create_calendar
            event_id: From list_events
            new_event_name: The name of the event that will show up in the calendar (optional)
            new_time_zone: The time zone the event will take place in (ask user if unknown) formatted according to IANA time zone database such as America/New_York (necessary if new_start_date_time or new_end_date_time is used)
            new_start_date_time: The start time of the event, the start of the first event if the event repeats (optional)
            new_end_date_time: The end time of the event, the end of the first event if the event repeats (optional)
            new_location: The location of the event (optional)
            repeats: Whether the event repeats or not (optional default False)
            repeat_days: A string containing the days that the event repeats weekly comma separated (i.e. TU,TH) (optional)
            final_repeat_date: A datetime string indicating the cutoff date for repetitions, it does not need to fall on an event occurrence. (ask user if unknown) If time is unknown just use midnight (optional)
        """
        with httpx.Client() as client:
            res = client.get(
                f"{CALENDAR_API}/calendars/{calendar_id}/events/{event_id}",
                headers={"Authorization": f"Bearer {self.auth.get_access_token(session_id)}"},
            )
            if res.json().get("description", "") != self.MCP_DESCRIPTION:
                return "Cannot patch an event which is not MCP generated"

        input_json = {}
        if new_event_name:
            input_json["summary"] = new_event_name
        if (new_start_date_time or new_end_date_time) and new_time_zone == None:
            return "Timezone must be specified to update start and end times"
        if new_start_date_time:
            input_json["start"] = {
                "dateTime": new_start_date_time,
                "timeZone": new_time_zone,
            }
        if new_end_date_time:
            input_json["end"] = {
                "dateTime": new_end_date_time,
                "timeZone": new_time_zone,
            }
        if new_location: input_json["location"] = new_location
        if repeats:
            final_dt = datetime.strptime(final_repeat_date, "%Y-%m-%dT%H:%M:%S")
            final_dt = final_dt.replace(tzinfo=timezone.utc)
            final_dt_reformatted = final_dt.strftime("%Y%m%dT%H%M%SZ")
            input_json["recurrence"] = [
                f"RRULE:FREQ=WEEKLY;UNTIL={final_dt_reformatted};WKST=SU;BYDAY={repeat_days}"
            ]

        with httpx.Client() as client:
            res = client.patch(
                f"{CALENDAR_API}/calendars/{calendar_id}/events/{event_id}",
                headers={"Authorization": f"Bearer {self.auth.get_access_token(session_id)}"},
                json=input_json,
            )
            res.raise_for_status()
            event_id = res.json()["id"]
        return f"""
            Successfully updated!
            event_id: {event_id}
        """

    def delete_event(
        self,
        session_id: str,
        calendar_id: str,
        event_id: str,
    ) -> str:
        """
        Deletes an event that has been generated by MCP. Assumes user has been authenticated.
        Args:
            session_id: Session id obtained from get_url
            calendar_id: The id of calendar the event should be added to, is returned from create_calendar
            event_id: From list_events
        """
        with httpx.Client() as client:
            res = client.get(
                f"{CALENDAR_API}/calendars/{calendar_id}/events/{event_id}",
                headers={"Authorization": f"Bearer {self.auth.get_access_token(session_id)}"},
            )
            res.raise_for_status()
            if res.json().get("description") != self.MCP_DESCRIPTION:
                return "Cannot delete an event which is not MCP generated"

        with httpx.Client() as client:
            res = client.delete(
                f"{CALENDAR_API}/calendars/{calendar_id}/events/{event_id}",
                headers={"Authorization": f"Bearer {self.auth.get_access_token(session_id)}"},
            )
            res.raise_for_status()
        return "Successfully deleted!"
