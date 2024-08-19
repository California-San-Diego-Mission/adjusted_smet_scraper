# pylint: disable=line-too-long disable=bare-except
"""Log into church servers and get data for SMET"""

import json
import os
from datetime import datetime, timedelta

import dotenv
import requests

import dashboard
from person import Person, PersonParseException


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
        # Read the dotenv file
        dotenv.load_dotenv()

        self.username = os.getenv('CHURCH_USERNAME')
        self.password = os.getenv('CHURCH_PASSWORD')
        try:
            with open('session.json', 'x') as file:
                file.write('{}')
        except FileExistsError:
            print('Session exists')

        with open('session.json', 'r', encoding='utf-8') as file:
            # Read to json
            session_data = json.load(file)

            # Determine if we have state, client_id, or stateToken
            self.nonce = session_data.get('nonce')
            self.state = session_data.get('state')
            self.client_id = session_data.get('client_id')
            self.state_token = session_data.get('stateToken')
            self.bearer = session_data.get('bearer')

            # Import cookies
            cookies = session_data.get('cookies')
            if cookies:
                self.client.cookies.update(session_data['cookies'])

    def __format__(self, __format_spec: str) -> str:
        return f'{self.username}:{self.password}\n State: {self.state} Client ID: {self.client_id} State Token: {self.state_token}'

    def save(self):
        """Save the state of the client to a file"""
        with open('session.json', 'w', encoding='utf-8') as file:
            # Write to json
            json.dump(
                {
                    'nonce': self.nonce,
                    'state': self.state,
                    'client_id': self.client_id,
                    'stateToken': self.state_token,
                    'cookies': dict(self.client.cookies),
                    'bearer': self.bearer,
                },
                file,
                indent=4,
            )

    def login(self):
        """Log into the church servers, setting cookies and tokens"""
        # Clear old cookies
        self.client.cookies.clear()

        # Set user-agent
        self.client.headers['User-Agent'] = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'
        )

        # Get redirect URL from login page, then extract the state token
        res = self.client.get(
            'https://referralmanager.churchofjesuschrist.org'
        )
        if res.status_code != 200:
            raise ChurchHttpError

        # Extract the JSON embedded in the HTML
        json_data = res.text.split('"stateToken":"')[1].split('",')[0]
        # Decode the nasty stuff the church does to JSON in HTML
        self.state_token = json_data.encode().decode('unicode-escape')

        print(self.state_token)

        # Get the state handle
        res = self.client.post(
            'https://id.churchofjesuschrist.org/idp/idx/introspect',
            data=json.dumps({'stateToken': self.state_token}),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
        )
        self.state_token = res.json()['stateHandle']

        # Send the username with the stateToken
        res = self.client.post(
            'https://id.churchofjesuschrist.org/idp/idx/identify',
            data=json.dumps(
                {'stateHandle': self.state_token, 'identifier': self.username}
            ),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
        )
        if not res.status_code == 200:
            print(res)
            print(res.text)
            raise ChurchInvalidCreds
        res = res.json()
        self.state_token = res['stateHandle']

        # Send the password with the stateToken
        res = self.client.post(
            'https://id.churchofjesuschrist.org/idp/idx/challenge/answer',
            data=json.dumps(
                {
                    'stateHandle': self.state_token,
                    'credentials': {'passcode': self.password},
                }
            ),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
        )
        if not res.status_code == 200:
            print(res)
            print(res.text)
            raise ChurchInvalidCreds

        # Set the auth cookies
        res = self.client.get(
            res.json()['success']['href'], allow_redirects=False
        )

        # Get the redirect URL from res
        res = self.client.get(res.headers['Location'], allow_redirects=False)

        # Get the bearer token
        res = self.client.get(
            'https://referralmanager.churchofjesuschrist.org/services/auth',
            headers={
                'Accept': 'application/json, text/plain, */*',
                'Authorization': '',
            },
        )
        self.bearer = res.json()['token']

        # Save the state for future launches
        self.save()

    def get_referral_dashboard_counts(self):
        """Get the dashboard counts from referral manager"""
        headers = {
            'Referer': 'https://referralmanager.churchofjesuschrist.org/dashboard/(right-sidebar:tasks)',
            'Authorization': f'Bearer {self.bearer}',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en',
            'Time-Zone': 'America/Los_Angeles',
        }
        res = self.client.get(
            'https://referralmanager.churchofjesuschrist.org/services/facebook/dashboardCounts',
            headers=headers,
        )
        if res.status_code == 500:
            print('Cookies are invalid, logging in')
            self.login()
            res = self.client.get(
                'https://referralmanager.churchofjesuschrist.org/services/facebook/dashboardCounts',
                headers=headers,
            )
        if res.status_code != 200:
            print(res)
            raise ChurchHttpError

        try:
            return res.json()
        except requests.exceptions.JSONDecodeError as e:
            raise ChurchParseError from e

    def get_people_list(self, recurse=False) -> list[Person]:
        """Gets the list of everyone from the referral manager. This is a HUGE request at roughly 8mb. Smh the church is bad"""
        res = self.client.get(
            'https://referralmanager.churchofjesuschrist.org/services/people/mission/14289?includeDroppedPersons=true',
            headers={'Authorization': f'Bearer {self.bearer}'},
        )
        if res.status_code == 500:
            if recurse:
                raise ChurchHttpError
            else:
                print('Cookies are invalid, logging in')
                self.login()
                return self.get_people_list(recurse=True)
        if res.status_code != 200:
            print(res)
            raise ChurchHttpError

        try:
            res = res.json()
            persons = res['persons']
            res = []
            for p in persons:
                try:
                    res.append(Person(p))
                except PersonParseException as e:
                    print('Unable to parse person: ', e)
                    continue
            return res
        except requests.exceptions.JSONDecodeError as e:
            if recurse:
                raise ChurchParseError from e
            else:
                print('Cookies might be invalid, logging in')
                self.login()
                return self.get_people_list(recurse=True)

    def get_cached_people_list(self) -> list[Person]:
        """Pulls the people list from the cache if available,
        or fetches new if none"""
        # Check if the people folder exists
        if not os.path.exists('people'):
            os.mkdir('people')

        # Lists are saved as <timestamp>.json
        files = os.listdir('people')
        if len(files) == 0:
            # No files, fetch new
            pl = self.get_people_list()
            self.cache_people_list(pl)
            return pl

        # Get the most recent file
        files.sort(reverse=True)
        file = files[0]

        # Get the timestamp
        timestamp = int(file.split('.')[0])

        # Check if the file is older than 2 hours
        if datetime.now() - datetime.fromtimestamp(timestamp) > timedelta(
            hours=2
        ):
            # File is older than 1 hour, fetch new
            pl = self.get_people_list()
            self.cache_people_list(pl)
            return pl

        # Load the file
        with open(f'people/{file}', 'r', encoding='utf-8') as file:
            res = json.load(file)
            persons = res['persons']
            res = []
            for p in persons:
                try:
                    res.append(Person(p))
                except PersonParseException as e:
                    print('Unable to parse person: ', e)
                    continue
            return res

    def cache_people_list(self, people_list: list[Person]):
        """Saves the people list to the cache"""
        # Get the current time
        timestamp = int(datetime.now().timestamp())

        # Save the file
        res = {'persons': list(map(lambda x: x.ser(), people_list))}
        with open(f'people/{timestamp}.json', 'w', encoding='utf-8') as file:
            json.dump(res, file, indent=4)

    def get_person_timeline(self, person_guid):
        """Gets the details for a single person from the referral manager"""
        res = self.client.get(
            f'https://referralmanager.churchofjesuschrist.org/services/progress/timeline/{person_guid}'
        )
        if res.status_code != 200:
            print(res)
            raise ChurchHttpError

        try:
            return res.json()
        except requests.exceptions.JSONDecodeError as e:
            raise ChurchParseError from e

    def filter_person(self, person: Person) -> bool:
        """Get all the critical information from the person"""

        if person.referral_status == dashboard.ReferralStatus.SUCCESSFUL:
            return False

        # If it's less than 48 hours, no need
        if person.referral_assigned_date > datetime.now() - timedelta(
            hours=48
        ):
            return False

        # Ignore referrals from the MCRD
        # since they can only be contacted on Sunday
        if 'Marine Corps' in person.org_name:
            return False

        grey_dot = False
        match person.status:
            case dashboard.PersonStatus.MEMBER:
                return False
            case dashboard.PersonStatus.NEW_MEMBER:
                return False
            case dashboard.PersonStatus.UNABLE_TO_CONTACT:
                return False
            case dashboard.PersonStatus.MOVED:
                return False
            case dashboard.PersonStatus.OUTSIDE_AREA_STRENGTH:
                return False
            case dashboard.PersonStatus.NOT_INTERESTED_DECLARED:
                return False
            case dashboard.PersonStatus.PRANK:
                return False
            case dashboard.PersonStatus.NOT_INTERESTED:
                grey_dot = True
            case dashboard.PersonStatus.NOT_PROGRESSING:
                grey_dot = True
            case dashboard.PersonStatus.TOO_BUSY:
                grey_dot = True
            case dashboard.PersonStatus.NOT_RECENTLY_CONTACTED:
                return True

        if person.referral_status == dashboard.ReferralStatus.NOT_SUCCESSFUL:
            print(f'Fetching timeline for {person.guid}')
            timeline = self.get_person_timeline(person.guid)
            if dashboard.parse_timeline(timeline, grey_dot) is False:
                return False

        return True
