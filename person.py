"""
Elder Coxson
Class for managing person information from referral manager
"""

from datetime import datetime

from dashboard import PersonStatus, ReferralStatus, Zone


class PersonParseException(Exception):
    pass


class Person:
    """Class for a person"""

    first_name: str
    area_name: str
    org_name: str
    referral_assigned_date: datetime
    guid: str
    zone: Zone
    status: PersonStatus
    referral_status: ReferralStatus

    def __init__(self, obj: dict):
        self.first_name = obj['firstName'].split(' ')[0]
        try:
            self.area_name = obj['areaName']
        except KeyError:
            raise PersonParseException('Person has no area name')
        try:
            self.org_name = obj['orgName']
        except KeyError:
            raise PersonParseException('Person has no org name')
        try:
            self.referral_assigned_date = datetime.fromtimestamp(
                obj['referralAssignedDate'] / 1000
            )
        except KeyError:
            raise PersonParseException('Person has no org name')
        except TypeError:
            raise PersonParseException(
                'Supplied assigned date is not right type'
            )
        self.guid = obj['personGuid']
        try:
            self.zone = Zone(obj.get('zoneId'))
        except ValueError:
            raise PersonParseException(
                'Zone ID not found: ' + str(obj.get('zoneId'))
            )
        try:
            self.status = PersonStatus(obj.get('personStatusId'))
        except ValueError:
            raise PersonParseException('Person Status ID not found')
        try:
            self.referral_status = ReferralStatus(obj.get('referralStatusId'))
        except ValueError:
            raise PersonParseException('Referral Status ID not found')

    def ser(self) -> dict:
        return {
            'firstName': self.first_name,
            'areaName': self.area_name,
            'orgName': self.org_name,
            'referralAssignedDate': int(
                self.referral_assigned_date.timestamp()
            )
            * 1000,
            'personGuid': self.guid,
            'zoneId': self.zone.value,
            'personStatusId': self.status.value,
            'referralStatusId': self.referral_status.value,
        }

    def __eq__(self, other) -> bool:
        return (
            self.first_name == other.first_name
            and self.area_name == other.area_name
            and self.org_name == other.org_name
            and self.referral_assigned_date == other.referral_assigned_date
            and self.guid == other.guid
            and self.zone == other.zone
            and self.status == other.status
            and self.referral_status == other.referral_status
        )
