from django.db.models import F
from datetime import timedelta

from api.models import (Event,)


class Utilities():
    def __init__(self):
        pass


    pass


class Filter():


## возвращать как объекты готовые для json
class ReadAPI():
    filter_query : dict


    def __init__(self, filter_query : dict = None):
        self.filter_query = filter_query if filter_query is not None else {}
        # self.filter_query = filter_query or {}

    
    def append_filter(self, addition_query):
        self.filter_query.update(addition_query)


    def get_data(self):
        """ Предназначено для внутреннего использования """

        data = Event.objects.filter(**self.filter_query)

        print(data)


    def get_teachers(self): ###
        pass

    ## get расписание преподавателей для ПОАС


class WriteAPI():
    @staticmethod
    def create_event(date, abstract_event):
        """create new Event from given AbstractEvent and date when Event happens"""

        event = Event()

        event.date = date
        event.kind_override = abstract_event.kind
        event.subject_override = abstract_event.subject
        event.time_slot_override = abstract_event.time_slot
        event.abstract_event = abstract_event
        event.is_event_canceled = False
        
        event.save()

        event.participants_override.add(*abstract_event.participants.all())
        event.places_override.add(*abstract_event.places.all())


    @staticmethod
    def clear_event_table(additional_filter_query = {}):
        """delete all not overriden Events"""
        
        filter_query = {
            'abstract_event__kind' : F("kind_override"),
            'abstract_event__subject' : F("subject_override"),
            'abstract_event__time_slot' : F("time_slot_override"),
            'is_event_canceled' : False
        }
        filter_query.update(additional_filter_query)

        Event.objects.filter(**filter_query).delete()


    @staticmethod
    def fill_semester(abstract_event):
        """takes AbstractEvent and fill all semester"""

        if abstract_event.holds_on_dates != None:
            WriteAPI.create_event(abstract_event.holds_on_dates, abstract_event)
            return

        semester_start_date = abstract_event.schedule.start_date
        semester_end_date = abstract_event.schedule.end_date

        repetition_period = abstract_event.schedule.schedule_template.repetition_period

        fill_from_date = semester_start_date

        # if start date in first week
        # finding previous first week monday date
        if abstract_event.schedule.starting_day_number.day_number < 7:
            fill_from_date -= timedelta(abstract_event.schedule.starting_day_number.day_number)
        # otherwise
        # finding next first week monday date
        else:
            fill_from_date += timedelta(14 - abstract_event.schedule.starting_day_number.day_number)

        # adding AbstractEvent delta from first week monday
        fill_from_date += timedelta(abstract_event.abstract_day.day_number)

        date = fill_from_date
        while date < semester_end_date:
            if date >= semester_start_date:
                WriteAPI.create_event(date, abstract_event)

                # creating Event for only first acceptable date
                if not abstract_event.schedule.schedule_template.repeatable:
                    return
            
            date += timedelta(days=repetition_period)

    
    @staticmethod
    def fill_event_table(abstract_events):
        """clear database and fill it from found AbstractEvents"""

        WriteAPI.clear_event_table()

        for e in abstract_events:
            WriteAPI.fill_semester(e)

        return True


    @staticmethod
    def rewrite_events(changed_abstract_event):
        """rewrite Events with specified AbstractEvent"""

        WriteAPI.clear_event_table({'abstract_event__pk' : changed_abstract_event.pk})

        WriteAPI.fill_semester(changed_abstract_event)

        return True