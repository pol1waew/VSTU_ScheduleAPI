from datetime import date, timedelta


class UtilityFilterBase:
    """Base parent class for filters   
    """


class DateFilter(UtilityFilterBase):
    @staticmethod
    def from_singe_date(_date : str|date):
        if isinstance(_date, str):
            _date = date.fromisoformat(_date)

        return {"date" : _date}


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
    def take_whole_week(_date : str|date):
        if isinstance(_date, str):
            _date = date.fromisoformat(_date)

        return DateFilter.from_range(_date, _date.weekday(), 6 - _date.weekday())


    @staticmethod
    def this_week():
        return DateFilter.take_whole_week(date.today())
    

    @staticmethod
    def next_week():
        return DateFilter.take_whole_week(date.today() + timedelta(weeks=1))
    

