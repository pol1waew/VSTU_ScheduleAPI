from django.db.models import QuerySet
from datetime import date, timedelta

from api.models import (
    AbstractEvent,
    Event, 
    Schedule
)

import api.utilityFilters as filters


class Utilities:
    def __init__(self):
        pass


    pass


## возвращать как объекты готовые для json
class ReadAPI:
    filter_query : dict
    found_data : QuerySet

    def __init__(self, filter_query : dict = None):
        self.filter_query = filter_query or {}

    
    def append_filter(self, addition_query : dict):
        """Updates filter query from dictionary

        Allows user manualy append filters in format {'field_name' : value}
        """

        self.filter_query.update(addition_query)


    def append_filter(self, filter : filters.UtilityFilterBase):
        """Updates filter query from utility filter
        """

        self.filter_query.update(filter)


    def find_data(self):
        """Finds  with applied earlier filters
        """
        
        self.found_data = Event.objects.filter(**self.filter_query)
        print(self.found_data)


    def get_raw_found_data(self):
        return self.found_data


    ## TODO
    def find_abstract_events_with_schedule(self, schedule : Schedule):
        # getting all events primary keys with expected schedule
        schedule_events_pks = Event.objects.filter(abstract_event__schedule = schedule).values_list("abstract_event__pk", flat=True).distinct()
        self.found_data = AbstractEvent.objects.filter(pk__in = schedule_events_pks)

    '''
    def get_teachers(self):
        print(self.found_data.values())'
        '''

    ## get расписание преподавателей для ПОАС


class WriteAPI:
    @staticmethod
    def create_event(_date : str|date, abstract_event : AbstractEvent):
        """Create new Event from abstract_event on specified date
        """

        if isinstance(_date, str):
            _date = date.fromisoformat(_date)

        event = Event()
        
        event.date = _date
        event.kind_override = abstract_event.kind
        event.subject_override = abstract_event.subject
        event.time_slot_override = abstract_event.time_slot
        event.abstract_event = abstract_event
        event.is_event_canceled = False
        
        event.save()

        event.participants_override.add(*abstract_event.participants.all())
        event.places_override.add(*abstract_event.places.all())


    @staticmethod
    def clear_not_overriden_events(additional_filter_query = {}):
        """Deletes all not overriden Events
        """
        
        filter_query = filters.EventFilter.not_overriden()
        filter_query.update(additional_filter_query)

        Event.objects.filter(**filter_query).delete()


    @staticmethod
    def get_semester_filling_parameters(abstract_event : AbstractEvent):
        """Intended for internal usage

        Returns:
            semester_start_date, 
            semester_end_date,
            fill_from_date,
            repetition_period
        """
        
        semester_start_date = abstract_event.schedule.start_date

        fill_from_date = semester_start_date

        # finding first week monday date

        # if start date in first week
        # finding previous first week monday date
        if abstract_event.schedule.starting_day_number.day_number < 7:
            fill_from_date -= timedelta(abstract_event.schedule.starting_day_number.day_number)
        # otherwise
        # finding next first week monday date
        else:
            fill_from_date += timedelta(14 - abstract_event.schedule.starting_day_number.day_number)

        # adding abstract_event delta from first week monday
        fill_from_date += timedelta(abstract_event.abstract_day.day_number)

        return semester_start_date, \
                abstract_event.schedule.end_date, \
                fill_from_date, \
                abstract_event.schedule.schedule_template.repetition_period


    @staticmethod
    def fill_semester(abstract_event : AbstractEvent):
        """Take abstract_event and fill semester
        """

        # creates single event if abstract_event holds on expected date
        if abstract_event.holds_on_date != None:
            WriteAPI.create_event(abstract_event.holds_on_date, abstract_event)
            return

        semester_start_date, semester_end_date, fill_from_date, repetition_period = WriteAPI.get_semester_filling_parameters(abstract_event)

        date = fill_from_date
        while date < semester_end_date:
            if date >= semester_start_date:
                WriteAPI.create_event(date, abstract_event)

                # creating Event for only first acceptable date
                # if abstract_event is not repeatable
                if not abstract_event.schedule.schedule_template.repeatable:
                    return
            
            date += timedelta(days=repetition_period)

    
    @staticmethod
    def fill_event_table(abstract_events):
        """Clear event table and fill it from abstract_events
        """

        WriteAPI.clear_not_overriden_events()

        for ae in abstract_events:
            WriteAPI.fill_semester(ae)

        return True


    @staticmethod
    def rewrite_events(changed_abstract_event):
        """Rewrite Events with specified AbstractEvent
        """

        WriteAPI.clear_not_overriden_events({'abstract_event__pk' : changed_abstract_event.pk})

        WriteAPI.fill_semester(changed_abstract_event)

        return True
    

    @staticmethod
    def move_event_to_date(event : Event, move_to_date : str|date):
        if isinstance(move_to_date, str):
            move_to_date = date.fromisoformat(move_to_date)

        event.date = move_to_date
        event.save()
