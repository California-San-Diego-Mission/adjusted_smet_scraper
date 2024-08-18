"""Upload the data to Google Sheets"""

import datetime
import gspread

from dashboard import ClaimedStatus, FbPageId


class SpreadClient:
    """Client for managing the Gsheet"""

    def __init__(self):
        print('Logging in with Google')
        self.gc = gspread.service_account(filename='g_service.json')  # type: ignore
        self.spreadsheet = self.gc.open_by_key(
            '130QHJihi_6YhjbyKKLxGgTF12XivG8bkW9u21pcBSLM'
        )

        self.database_sheet = self.spreadsheet.worksheet('AutoDatabase')
        self.stats_sheet = self.spreadsheet.worksheet('AutoStats')

        # Get the list of people in the spreadsheet
        self.user_list = []
        data = self.database_sheet.get('B1:ZZZ1')
        if len(data) > 0:
            for d in data[0]:
                if d == '':
                    continue
                self.user_list.append(d)

        # Get the page list
        self.page_list = []
        data = self.stats_sheet.get('B1:ZZZ1')
        if len(data) > 0:
            for d in data[0]:
                if d == '':
                    continue
                self.page_list.append(d)

    def add_user(self, name):
        """Adds a user to the spreadsheet"""
        self.database_sheet.insert_cols(
            [
                [name, 'Responses', 'U'],
                [None, None, 'R'],
                ['', '', 'P'],
                ['', '', 'N'],
                ['', 'Messaging', 'U'],
                ['', '', 'R'],
                ['', '', 'P'],
                ['', '', 'N'],
                ['', '', 'DOT'],
            ],
            col=self.database_sheet.col_count,
        )
        self.user_list.append(name)

    def check_users_exist(self, name_list):
        """Checks that all users exist"""
        to_insert = []
        for name in name_list:
            if name not in self.user_list:
                to_insert.extend(
                    [
                        [name, 'Messaging', 'U'],
                        [None, None, 'R'],
                        ['', '', 'P'],
                        ['', '', 'N'],
                        ['', 'Responses', 'U'],
                        ['', '', 'R'],
                        ['', '', 'P'],
                        ['', '', 'N'],
                        ['', '', 'DOT'],
                    ]
                )
                self.user_list.append(name)
        self.database_sheet.insert_cols(
            to_insert, col=self.database_sheet.col_count
        )

    def add_daily_data(self, data):
        """Inserts the data into the spreadsheet"""

        # Check to make sure we have every single user
        self.check_users_exist(data['user'].keys())

        # Add the user rows
        user_row = [
            datetime.date.today().isoformat(),
        ]
        for user in self.user_list:
            res = data['user'].get(user)
            if res:
                user_row.append(
                    res['messaging'][ClaimedStatus.NOT_CONTACTED.value]
                )
                user_row.append(
                    res['messaging'][ClaimedStatus.NO_RESPONSE.value]
                )
                user_row.append(
                    res['messaging'][ClaimedStatus.POSITIVE_RESPONSE.value]
                )
                user_row.append(
                    res['messaging'][ClaimedStatus.NEGATIVE_RESPONSE.value]
                )
                user_row.append(
                    res['responses'][ClaimedStatus.NOT_CONTACTED.value]
                )
                user_row.append(
                    res['responses'][ClaimedStatus.NO_RESPONSE.value]
                )
                user_row.append(
                    res['responses'][ClaimedStatus.POSITIVE_RESPONSE.value]
                )
                user_row.append(
                    res['responses'][ClaimedStatus.NEGATIVE_RESPONSE.value]
                )
                user_row.append(res['dots'])
            else:
                print('No user: ', user)
                user_row.extend([0, 0, 0, 0, 0, 0, 0, 0, 0])

        self.database_sheet.append_rows([user_row])

        # Create the page dictionary
        pages = {}
        for p in FbPageId:
            pages[p.name] = p.value

        # Iterate over the pages
        res_values = [
            datetime.date.today().isoformat(),
        ]
        for page in self.page_list:
            page_id = pages.get(page)
            if page_id:
                page_data = data['overview'].get(page_id)
                if page_data:
                    res_values.extend(
                        [
                            page_data['missed'],
                            page_data['received'],
                            page_data['dots'],
                        ]
                    )
                else:
                    print(f'Page {page} not found in the given data')
                    res_values.extend([0, 0, 0])
            else:
                print(f'Page {page} not found in the enum')
                res_values.extend([0, 0, 0])

        self.stats_sheet.append_rows([res_values])
