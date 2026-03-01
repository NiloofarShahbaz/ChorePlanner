from enum import Enum, StrEnum
from typing import Annotated, Literal, Union

import inflect
from pydantic import (
    BaseModel,
    Field,
    TypeAdapter,
    computed_field,
    create_model,
    model_validator,
    types, SkipValidation,
)
from tortoise.contrib.pydantic import PydanticListModel, pydantic_model_creator

from src.chores_planner.models.chore import Chore, FrequencyChoices

BaseChoreCreateModel = pydantic_model_creator(
    Chore, exclude_readonly=True, exclude=("image",)
)
BaseChoreGetModel = pydantic_model_creator(Chore)
p = inflect.engine()


def pydantic_queryset_creator(
    submodel: type[BaseModel],
    name: str,
    exclude: tuple[str, ...] = (),
    include: tuple[str, ...] = (),
    computed: tuple[str, ...] = (),
    allow_cycles: bool | None = None,
    sort_alphabetically: bool | None = None,
) -> type[PydanticListModel]:
    model = create_model(
        name,
        __base__=PydanticListModel,
        root=(list[submodel], Field(default_factory=list)),  # type: ignore
    )
    # model.__doc__ = _cleandoc(cls)
    model.model_config["title"] = name or f"{submodel.model_config['title']}_list"
    model.model_config["submodel"] = submodel  # type: ignore
    return model


class ChoreGetModel(BaseChoreGetModel):
    id: types.PositiveInt  # defined because it's wierd to see -12345 in openAPI docs!
    frequency_interval: types.PositiveInt
    frequency_data: SkipValidation[FrequencyData]

    @computed_field
    @property
    def frequency_translation(self) -> str:
        frequency = (
            f"Every {self.frequency_interval} {self.frequency.translation}s"
            if self.frequency_interval > 1
            else f"Every {self.frequency.translation}"
        )

        match self.frequency:
            case FrequencyChoices.DAILY:
                return frequency
            case FrequencyChoices.WEEKLY:
                days_list = [
                    d.day.translation for d in self.frequency_data.by_days or []
                ]
                return f"{frequency} on {p.join(days_list)}"
            case FrequencyChoices.MONTHLY:
                if self.frequency_data.by_monthdays:
                    return f"{frequency} on day {self.frequency_data.by_monthdays}"
                bydays = []
                for byday in self.frequency_data.by_days or []:
                    if byday.occurance > 0:
                        bydays.append(
                            f"{p.number_to_words(p.ordinal(byday.occurance))} {byday.day.translation}"
                        )
                    elif byday.occurance == -1:
                        bydays.append(f"last {byday.day.translation}")
                return f"{frequency} on the {p.join(bydays)}"
            case FrequencyChoices.YEARLY:
                return f"{frequency} (nope, not going to translate this)."
        return ""


ChoreListModel = TypeAdapter(list[ChoreGetModel])


class WeekDay(StrEnum):
    SU = "SU", "Sunday"
    MO = "MO", "Monday"
    TU = "TU", "Tuesday"
    WE = "WE", "Wednesday"
    TH = "TH", "Thursday"
    FR = "FR", "Friday"
    SA = "SA", "Saturday"

    def __new__(cls, value, translation):
        self = str.__new__(cls)
        self._value_ = value
        self.translation = translation
        return self


class ByDay(BaseModel):
    occurance: Annotated[int, Field(lt=53, gt=-53)] | None = None
    day: WeekDay
    
    class Config:
        use_enum_values = True


class FrequencyData(BaseModel):
    by_days: list[ByDay] | None = None
    by_monthdays: list[Annotated[int, Field(lt=31, gt=-31)]] | None = None

    @model_validator(mode="after")
    def check_only_one_is_given(self):
        if self.by_days and self.by_monthdays:
            raise ValueError(
                "Only one of the 'by_days' or 'by_monthdays' fields can be specified."
            )
        return self


class ChoreCreateModel(BaseChoreCreateModel):
    frequency_data: FrequencyData

    @model_validator(mode="after")
    def check_frequency_data_with_frequency(self):
        match self.frequency:
            case FrequencyChoices.WEEKLY:
                if not self.frequency_data.by_days:
                    raise ValueError(
                        "'by_day' should be specified for WEEKLY frequency."
                    )
                elif any(f.occurance for f in self.frequency_data.by_days):
                    raise ValueError("You can't have occurance for WEEKLY frequency.")
            case FrequencyChoices.MONTHLY:
                if self.frequency_data.by_days and any(
                    d.occurance is None for d in self.frequency_data.by_days
                ):
                    raise ValueError(
                        "Occurance should be specified for MONTHLY frequency."
                    )
                elif self.frequency_data.by_days and any(
                    f.occurance > 5 or f.occurance < -1 or f.occurance == 0
                    for f in self.frequency_data.by_days
                ):
                    if any(-5 < f.occurance < -1 for f in self.frequency_data.by_days):
                        raise ValueError(
                            f"TBH the occurance value between -4 to -2 should be acceptable, but do you even understand this?! :))"
                        )
                    raise ValueError(
                        "Occurance should be in range of -4 to -1 and 1 to 4 for MONTHLY frequency."
                    )
                elif (
                    not self.frequency_data.by_monthdays
                    and not self.frequency_data.by_days
                ):
                    raise ValueError(
                        "One of the 'by_monthdays' or 'by_days' field should be specified."
                    )
            case FrequencyChoices.YEARLY:
                if self.frequency_data.by_monthdays:
                    raise ValueError("Invalid frequency data for YEARLY frequency.")
                if self.frequency_data.by_days and any(
                    f.occurance == 0 for f in self.frequency_data.by_days
                ):
                    raise ValueError("Occurance can't be zero.")
        return self
