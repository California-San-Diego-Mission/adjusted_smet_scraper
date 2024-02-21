#pylint: disable=line-too-long disable=bare-except
"""Log into church servers and get data for SMET"""

import json
from datetime import timedelta
from datetime import datetime
import requests
import dashboard

class ChurchInvalidCreds(Exception):
    """Exception for invalid church credentials"""

class ChurchHttpError(Exception):
    """Exception for church http errors"""

class ChurchParseError(Exception):
    """Exception for church parse errors"""

class ChurchClient:
    """Church client class"""
    def __init__(self):
        self.client = requests.Session()

        with open("session.json", "r", encoding="utf-8") as file:
            # Read to json
            session_data = json.load(file)
            self.username = session_data["username"]
            self.password = session_data["password"]

            # Determine if we have state, client_id, or stateToken
            self.nonce = session_data.get("nonce")
            self.state = session_data.get("state")
            self.client_id = session_data.get("client_id")
            self.state_token = session_data.get("stateToken")

            # Import cookies
            cookies = session_data.get("cookies")
            if cookies:
                self.client.cookies.update(session_data["cookies"])

    def __format__(self, __format_spec: str) -> str:
        return f"{self.username}:{self.password}\n State: {self.state} Client ID: {self.client_id} State Token: {self.state_token}"

    def save(self):
        """Save the state of the client to a file"""
        with open("session.json", "w", encoding="utf-8") as file:
            # Write to json
            json.dump({
                "username": self.username,
                "password": self.password,
                "nonce": self.nonce,
                "state": self.state,
                "client_id": self.client_id,
                "stateToken": self.state_token,
                "cookies": dict(self.client.cookies)
            }, file, indent=4)

    def login(self):
        """Log into the church servers, setting cookies and tokens"""
        # Clear old cookies
        self.client.cookies.clear()

        # Set user-agent
        self.client.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36"

        # Set OG cookies
        res = self.client.get("https://id.churchofjesuschrist.org/auth/services/devicefingerprint")
        if not res.status_code == 200:
            print("Unable to fingerprint this device")
            raise ChurchHttpError
        self.nonce = self.client.post("https://id.churchofjesuschrist.org/api/v1/internal/device/nonce").json().get("nonce")

        # Get the state and client_id
        res = self.client.get("https://referralmanager.churchofjesuschrist.org/?lang=eng")
        if not res.status_code == 200:
            print("Failed to fetch the state and client ID from the base site")
            raise ChurchHttpError
        print(res.url)
        self.state = res.url.split("state=")[1].split("&")[0]
        self.client_id = res.url.split("client_id=")[1].split("&")[0]

        # Get the stateToken
        for _ in range(5):
            res = self.client.get(f"https://id.churchofjesuschrist.org/oauth2/default/v1/authorize?response_type=code&redirect_uri=https%3A%2F%2Freferralmanager.churchofjesuschrist.org%2Flogin&scope=openid%20profile%20offline_access&state={self.state}&client_id={self.client_id}").text
            self.state_token = res.split("\"stateToken\":\"")[1].split("\"")[0].encode().decode('unicode-escape')
            if not '\\' in self.state_token:
                break
        print(self.state_token)

        # Send the username with the stateToken
        res = self.client.post("https://id.churchofjesuschrist.org/idp/idx/identify", data=json.dumps({"stateHandle": self.state_token, "identifier": self.username}), headers={"Content-Type": "application/json", "Accept": "application/json"})
        if not res.status_code == 200:
            print(res)
            print(res.text)
            raise ChurchInvalidCreds
        res = res.json()
        self.state_token = res["stateHandle"]

        # Send the password with the stateToken
        res = self.client.post("https://id.churchofjesuschrist.org/idp/idx/challenge/answer", data=json.dumps({"stateHandle": self.state_token, "credentials": {"passcode": self.password}}), headers={"Content-Type": "application/json", "Accept": "application/json"})
        if not res.status_code == 200:
            print(res)
            print(res.text)
            raise ChurchInvalidCreds

        # Set the oauth token cookie on the client (I think)
        self.client.get(f"https://id.churchofjesuschrist.org/login/step-up/redirect?stateToken={self.state_token}")

        # Save the state for future launches
        self.save()

    def get_referral_dashboard_counts(self):
        """Get the dashboard counts from referral manager"""
        res = self.client.get("https://referralmanager.churchofjesuschrist.org/services/facebook/dashboardCounts")
        if res.status_code == 500:
            print("Cookies are invalid, logging in")
            self.login()
            res = self.client.get("https://referralmanager.churchofjesuschrist.org/services/facebook/dashboardCounts")
        if res.status_code != 200:
            print(res)
            raise ChurchHttpError

        try:
            return res.json()
        except requests.exceptions.JSONDecodeError as e:
            raise ChurchParseError from e

    def get_people_list(self):
        """Gets the list of everyone from the referral manager. This is a HUGE request at roughly 8mb. Smh the church is bad"""
        res = self.client.get("https://referralmanager.churchofjesuschrist.org/services/people/mission/14289")
        if res.status_code == 500:
            print("Cookies are invalid, logging in")
            self.login()
            res = self.client.get("https://referralmanager.churchofjesuschrist.org/services/people/mission/14289")
        if res.status_code != 200:
            print(res)
            raise ChurchHttpError

        try:
            return res.json()
        except requests.exceptions.JSONDecodeError as e:
            raise ChurchParseError from e

    def get_person_timeline(self, person_guid):
        """Gets the details for a single person from the referral manager"""
        res = self.client.get(f"https://referralmanager.churchofjesuschrist.org/services/progress/timeline/{person_guid}")
        if res.status_code != 200:
            print(res)
            raise ChurchHttpError

        try:
            return res.json()
        except requests.exceptions.JSONDecodeError as e:
            raise ChurchParseError from e

    def parse_person(self, person):
        """Get all the critical information from the person"""
        res = {}
        res['guid'] = person["personGuid"]
        res['first_name'] = person["firstName"]
        res['last_name'] = person["lastName"]
        res['area_name'] = person["areaName"]

        status = person["referralStatusId"]
        if status is None:
            # This means the referral was canceled
            return None
        res['referral_status'] = dashboard.ReferralStatus(status)
        if res['referral_status'] == dashboard.ReferralStatus.SUCCESSFUL:
            return None

        assigned_date = person["referralAssignedDate"]
        assigned_date = datetime.fromtimestamp(assigned_date / 1000)
        # If it's less than 48 hours, no need
        if assigned_date > datetime.now() - timedelta(hours=48):
            return None

        zone = person["zoneId"]
        if zone is None:
            # If the referral is marked as a member, there will be no teaching area/zone etc
            return None
        try:
            res['zone'] = dashboard.Zone(zone)
        except:
            print(f"Zone {zone} not found")
            return None

        status = person["personStatusId"]
        try:
            res['status'] = dashboard.PersonStatus(status)
        except:
            print(f"Person status {status} not found")

        match res['status']:
            case dashboard.PersonStatus.MEMBER:
                return None
            case dashboard.PersonStatus.NEW_MEMBER:
                return None
            case dashboard.PersonStatus.UNABLE_TO_CONTACT:
                return None
            case dashboard.PersonStatus.MOVED:
                return None
            case dashboard.PersonStatus.OUTSIDE_AREA_STRENGTH:
                return None
            case dashboard.PersonStatus.NOT_INTERESTED_DECLARED:
                return None
            case dashboard.PersonStatus.PRANK:
                return None
            case dashboard.PersonStatus.NOT_RECENTLY_CONTACTED:
                return res

        if res['referral_status'] == dashboard.ReferralStatus.NOT_SUCCESSFUL:
            guid = person["personGuid"]
            print(f"Fetching timeline for {guid}")
            timeline = self.get_person_timeline(guid)
            if dashboard.parse_timeline(timeline) is False:
                return None

        return res
