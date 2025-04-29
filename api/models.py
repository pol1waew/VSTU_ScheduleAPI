from typing import Optional, Self

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver


class CommonModel(models.Model):
    class Meta:
        abstract = True

    idnumber = models.CharField(
        unique=True,
        blank=True,
        null=True,
        max_length=260,
        verbose_name="Уникальный строковый идентификатор",
    )
    datecreated = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания записи")
    datemodified = models.DateTimeField(auto_now_add=True, verbose_name="Дата изменения записи")
    dateaccessed = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата доступа к записи"
    )
    author = models.ForeignKey(
        User, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Автор записи"
    )
    note = models.TextField(
        null=True, blank=True, verbose_name="Комментарий для этой записи", max_length=1024
    )

    @classmethod
    def last_modified_record(cls) -> Optional[Self]:
        return cls.objects.order_by("-datemodified").first()

    def __str__(self):
        return self.__repr__()


class Subject(CommonModel):
    class Meta:
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"

    name = models.CharField(max_length=256, verbose_name="Название")

    def __repr__(self):
        return str(self.name)


class TimeSlot(CommonModel):
    class Meta:
        verbose_name = "Время проведения события"
        verbose_name_plural = "Времена проведения события"

    alt_name = models.TextField(null=True, verbose_name="Академ. часы пары")
    start_time = models.TimeField(verbose_name="Время начала")
    end_time = models.TimeField(null=True, verbose_name="Время окончания")

    def clean(self):
        if self.end_time and self.end_time <= self.start_time:
            raise ValidationError("Время проведения не корректно")

    def __repr__(self):
        res = self.start_time.strftime("%H:%M")
        if self.end_time:
            res += "-{}".format(self.end_time.strftime("%H:%M"))
        return f"{self.alt_name}ч. / {res}"


class EventPlace(CommonModel):
    class Meta:
        verbose_name = "Место проведения события"
        verbose_name_plural = "Места проведения события"

    building = models.CharField(max_length=128, verbose_name="Корпус")
    room = models.CharField(max_length=64, verbose_name="Аудитория")

    def __repr__(self):
        return f"{self.building} {self.room}"


class EventKind(CommonModel):
    class Meta:
        verbose_name = "Тип события"
        verbose_name_plural = "Типы событий"

    name = models.CharField(verbose_name="Название типа", max_length=64)

    def __repr__(self):
        return str(self.name)


class AbstractDay(CommonModel):
    class Meta:
        verbose_name = "Абстрактный день"
        verbose_name_plural = "Абстрактные дни"

    day_number = models.IntegerField(verbose_name="Смещение от начала повторяющгося фрагмента (пн. первой недели)")
    name = models.CharField(verbose_name="Имя дня в рамках шаблона", max_length=64)

    def __repr__(self):
        return f"{str(self.name)}"


class Organization(CommonModel):
    class Meta:
        verbose_name = "Учреждение"
        verbose_name_plural = "Учреждения"

    name = models.CharField(verbose_name="Имя учреждения", max_length=64)

    def __repr__(self):
        return str(self.name)


class Department(CommonModel):
    class Meta:
        verbose_name = "Подразделение"
        verbose_name_plural = "Подразделения"

    name = models.CharField(verbose_name="Имя подразделения", max_length=64)
    parent_department = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Родительское подразделение"
        )
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, verbose_name="Учреждение")

    def __repr__(self):
        return str(self.name)


class ScheduleTemplateMetadata(CommonModel):
    class Meta:
        verbose_name = "Метаданные шаблона расписания"
        verbose_name_plural = "Метаданные шаблона расписания"

    class Scope(models.TextChoices):
        BACHELOR = "bachelor", "Бакалавриат"
        MASTER = "master", "Магистратура"
        POSTGRADUATE = "postgraduate", "Аспирантура"
        CONSULTATION = "consultation", "Консультация"

    faculty = models.CharField(max_length=32, verbose_name="Факультет")
    scope = models.CharField(choices=Scope, max_length=32, verbose_name="Обучение")

    def __repr__(self):
        return f"{self.faculty}, {self.scope}"


class ScheduleMetadata(CommonModel):
    class Meta:
        verbose_name = "Метаданные расписания"
        verbose_name_plural = "Метаданные расписания"

    years = models.CharField(max_length=16, verbose_name="Учебный год")
    course = models.IntegerField(verbose_name="Курс")
    semester = models.IntegerField(verbose_name="Семестр")
    
    def __repr__(self):
        return f"{self.years}, {self.course}курс, {self.semester}сем"


class ScheduleTemplate(CommonModel):
    class Meta:
        verbose_name = "Шаблон расписания"
        verbose_name_plural = "Шаблоны расписаний"

    metadata = models.ForeignKey(ScheduleTemplateMetadata, null=True, on_delete=models.PROTECT, verbose_name="Факультет, обучение")
    repetition_period = models.IntegerField(verbose_name="Период повторения в днях")
    repeatable = models.BooleanField(verbose_name="Повторяется ли")
    aligned_by_week_day = models.IntegerField(verbose_name="Выравнивание относительно дня недели (null=0, пн=1, ...)")
    department = models.ForeignKey(Department, null=True, on_delete=models.SET_NULL, verbose_name="Подразделение")

    def __repr__(self):
        if self.repetition_period in [0, 5, 6, 7, 8, 9] or self.repetition_period // 10 == 1:
            return f"{self.department}, каждые {self.repetition_period} дней"
        
        if self.repetition_period % 10 == 1:
            return f"{self.department}, каждый {self.repetition_period} день"
        
        if self.repetition_period % 10 in [2, 3, 4]:
            return f"{self.department}, каждые {self.repetition_period} дня"
        
        return f"{self.department}"
    
    def save(self, **kwargs):
        super().save(**kwargs)

        from api.utilities import WriteAPI, ReadAPI

        reader = ReadAPI({"schedule__schedule_template" : self})
        # getting AbstractEvent with existing Event
        reader.append_filter({"pk__in" : Event.objects.values_list("abstract_event__pk", flat=True).distinct()})
        
        reader.find_models(AbstractEvent)

        for e in reader.get_found_models():
            WriteAPI.rewrite_events(e)


class Schedule(CommonModel):
    class Meta:
        verbose_name = "Расписание"
        verbose_name_plural = "Расписания"

    class Status(models.IntegerChoices):
        ACTIVE = 0, "Активно"
        DISABLED = 1, "Отключено"
        FUTURE = 2, "Будущее"
        ARCHIVE = 3, "Архивное"

    metadata = models.ForeignKey(ScheduleMetadata, null=True, on_delete=models.PROTECT, verbose_name="Курс, семестр, год")
    status = models.IntegerField(choices=Status, default=0, verbose_name="Текущий статус")
    start_date = models.DateField(null=True, verbose_name="День начала семестра (вкл.)")
    end_date = models.DateField(null=True, verbose_name="День окончания семестра (вкл.)")
    starting_day_number = models.ForeignKey(AbstractDay, null=True, on_delete=models.PROTECT, verbose_name="Номер дня начала первого повторяющегося цикла") 
    schedule_template = models.ForeignKey(ScheduleTemplate, null=True, on_delete=models.PROTECT, verbose_name="Шаблон расписания")

    def first_event(self):
        events = self.events.all()

        return events.annotate(min_date=models.Min("holdings__date")).order_by("min_date").first() ####

    def last_event(self):
        events = self.events.all()

        return events.annotate(max_date=models.Max("holdings__date")).order_by("-max_date").first()   ######

    def __repr__(self):
        return f"{self.schedule_template.metadata}, {self.metadata}"
    
    def save(self, **kwargs):
        super().save(**kwargs)
        
        from api.utilities import WriteAPI, ReadAPI

        reader = ReadAPI({"schedule" : self})
        # getting AbstractEvent with existing Event
        reader.append_filter({"pk__in" : Event.objects.values_list("abstract_event__pk", flat=True).distinct()})
        
        reader.find_models(AbstractEvent)

        for ae in reader.get_found_models():
            WriteAPI.rewrite_events(ae)


class EventParticipant(CommonModel):
    class Meta:
        verbose_name = "Участник события"
        verbose_name_plural = "Участники события"

    class Role(models.TextChoices):
        STUDENT = "student", "Студент"
        TEACHER = "teacher", "Преподаватель"
        ASSISTANT = "assistant", "Ассистент"

    name = models.CharField(max_length=255, verbose_name="Имя")
    role = models.CharField(choices=Role, max_length=48, null=False, verbose_name="Роль")
    is_group = models.BooleanField(verbose_name="Является группой", default=False)
    department = models.ForeignKey(Department, null=True, on_delete=models.SET_NULL, verbose_name="Подразделение")

    def __repr__(self):
        return f"{self.name} ({self.role})"


class AbstractEvent(CommonModel):
    class Meta:
        verbose_name = "Абстрактное событие"
        verbose_name_plural = "Абстрактные события"

    kind = models.ForeignKey(EventKind, on_delete=models.PROTECT, verbose_name="Тип")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, verbose_name="Предмет")
    participants = models.ManyToManyField(EventParticipant, verbose_name="Участники")
    places = models.ManyToManyField(EventPlace, verbose_name="Места")
    abstract_day = models.ForeignKey(AbstractDay, on_delete=models.PROTECT, verbose_name="Абстрактный день")
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.PROTECT, verbose_name="Временной интервал")
    # single date. for many dates you should create many events
    holds_on_date = models.DateField(null=True, blank=True, verbose_name="Проводится только в заданный день")
    schedule = models.ForeignKey(Schedule, null=True, on_delete=models.CASCADE, related_name="events", verbose_name="Расписание")

    def __repr__(self):
        return f"Занятие по {self.subject.name}, {self.time_slot.alt_name}ч."

@receiver(pre_save, sender=AbstractEvent)
def OnAbstractEventSave(sender, instance, **kwargs):
    '''if instance.abstract_day != AbstractEvent.objects.get(pk=instance.pk).abstract_day or \
        instance.time_slot != AbstractEvent.objects.get(pk=instance.pk).time_slot or \
        instance.time_slot != AbstractEvent.objects.get(pk=instance.pk).time_slot:'''
    
    from api.utilities import WriteAPI

    WriteAPI.rewrite_events(instance)
    

class DayDateOverride(CommonModel):
    class Meta:
        verbose_name = "Перенос дня на другую дату"
        verbose_name_plural = "Переносы дней на другие даты"

    day_source = models.DateField(blank=False, verbose_name="Перенести с даты")
    day_destination = models.DateField(blank=False, verbose_name="Перенести на дату")
    schedule = models.ManyToManyField(Schedule, related_name="day_overrides", verbose_name="Расписание")

    def __repr__(self):
        return f"Перенос с {self.day_source} на {self.day_destination}"
    
    def save(self, **kwargs):
        super().save(**kwargs)
        
        from api.utilities import WriteAPI, ReadAPI
        import api.utilityFilters as filters

        reader = ReadAPI(filters.DateFilter.from_singe_date(self.day_source))
        reader.append_filter(filters.EventFilter.by_schedule_in_range(self.schedule.all())) ## TODO протестировать с несколькими расписаниями
        
        reader.find_models(Event)
        print(reader.filter_query)
        
        WriteAPI.override_event_dates(self, reader.get_found_models())

@receiver(pre_delete, sender=DayDateOverride)
def OnDayDateOverrideDelete(sender, instance, **kwargs):
    from api.utilities import WriteAPI, ReadAPI

    reader = ReadAPI({"date_override" : instance})
        
    reader.find_models(Event)
    
    WriteAPI.override_event_dates(None, reader.get_found_models())


class Event(CommonModel):
    class Meta:
        verbose_name = "Событие"
        verbose_name_plural = "События"

    date = models.DateField(null=True, blank=False, verbose_name="Дата")
    date_override = models.ForeignKey(DayDateOverride, null=True, blank=True, on_delete=models.DO_NOTHING, verbose_name="Перенос дня")
    kind_override = models.ForeignKey(EventKind, null=True, on_delete=models.PROTECT, verbose_name="Тип")
    subject_override = models.ForeignKey(Subject, null=True, on_delete=models.PROTECT, verbose_name="Предмет")
    participants_override = models.ManyToManyField(EventParticipant, verbose_name="Участники")
    places_override = models.ManyToManyField(EventPlace, verbose_name="Места")
    time_slot_override = models.ForeignKey(TimeSlot, null=True, on_delete=models.PROTECT, verbose_name="Временной интервал")
    abstract_event = models.ForeignKey(AbstractEvent, null=True, on_delete=models.PROTECT, verbose_name="Абстрактное событие")
    is_event_canceled = models.BooleanField(verbose_name="Событие отменено", default=False)

    def __repr__(self):
        return f"Занятие по {self.abstract_event.subject.name}"


"""
    Если несколько DayDateOverride'ов хотят перенести event
    например:
    11.02 -> 15.02
    10.02 -> 15.02

    что делать? 
"""


## TODO
## оптимизация сохранения
## перенос дней
## уведомление о проблемных записях
## эндпоинт для визуализации (обобщённый класс)
## заполнение евентов из schedule
## Администрирование Django -> Администрирование расписания

## обновить test_data