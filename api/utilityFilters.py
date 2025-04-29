from django.db.models import F
from datetime import date, timedelta


class UtilityFilterBase:
    """Base parent class for filters   

    Utility filters returns filter query: dict {key : value}
    """


class DateFilter(UtilityFilterBase):
    @staticmethod
    # TODO поместить подчерк в конец названия
    def from_singe_date(date_ : str|date):
        return {"date" : date_}


    @staticmethod
    def today():
        return DateFilter.from_singe_date(date.today())


    @staticmethod
    def tomorrow():
        return DateFilter.from_singe_date(date.today() + timedelta(days=1))


    @staticmethod
    def from_range(_date : str|date, left_range : int, right_range : int):
        if isinstance(_date, str):
            _date = date.fromisoformat(_date)
        
        left_interval_date = _date - timedelta(days=left_range)
        right_interval_date = _date + timedelta(days=right_range)

        return {"date__range" : [left_interval_date, right_interval_date]}
    

    @staticmethod
    def take_whole_week(_date):
        return DateFilter.from_range(_date, _date.weekday(), 6 - _date.weekday())


    @staticmethod
    def this_week():
        return DateFilter.take_whole_week(date.today())
    

    @staticmethod
    def next_week():
        return DateFilter.take_whole_week(date.today() + timedelta(weeks=1))
    

class ParticipantFilter(UtilityFilterBase):
    @staticmethod
    def by_name(name):
        return {"participants_override__name" : name}
    

    @staticmethod
    def by_role(role):
        return {"participants_override__role" : role}
    

class PlaceFilter(UtilityFilterBase):
    @staticmethod
    def by_building(building):
        return {"places_override__building" : building}
    

    @staticmethod
    def by_room(room):
        return {"places_override__room" : room}
    

class EventFilter(UtilityFilterBase):
    @staticmethod
    def not_overriden():
        return {
            'abstract_event__kind' : F("kind_override"),
            'abstract_event__subject' : F("subject_override"),
            'abstract_event__time_slot' : F("time_slot_override"),
            'is_event_canceled' : False
        }
    

    @staticmethod
    def by_schedule_in_range(acceptable_schedule_range):
        return {"abstract_event__schedule__in" : acceptable_schedule_range}
    