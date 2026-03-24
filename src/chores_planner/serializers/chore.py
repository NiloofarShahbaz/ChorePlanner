from dateutil import rrule
from datetime import datetime, timedelta
from functools import cached_property
from typing import Self

import inflect
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    computed_field,
    model_validator,
    types,
)

p = inflect.engine()


# TODO: work on deduplication
class ChoreCreateModel(BaseModel):
    name: str = Field(max_length=255)
    # TODO: image
    duration: timedelta = timedelta(minutes=30)
    start_from: datetime = datetime.now()

    rrules: list[str] | None = None
    _rruleset: rrule.rruleset | rrule.rrule | None = None

    @model_validator(mode="after")
    def check_rrules(self) -> Self:
        if self.rrules is not None:
            try:
                self._rruleset = rrule.rrulestr(self.rrule_str)
            except Exception as e:
                raise ValueError("Rrule is not valid.") from e
        return self

    @property
    def rrule_str(self) -> str | None:
        if self.rrules is None:
            return None
        return '\n'.join(self.rrules)


def _translate_single_rrule(rule: rrule.rrule) -> str:
    DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    MONTHS = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    ORDINALS = {1: "first", 2: "second", 3: "third", 4: "fourth",
                -1: "last", -2: "second to last", -3: "third to last", -4: "fourth to last"}

    def ordinal_str(n: int) -> str:
        return ORDINALS[n] if n in ORDINALS else p.ordinal(str(n))

    freq = rule._freq
    interval = rule._interval

    match freq:
        case rrule.DAILY:
            base = "daily" if interval == 1 else f"every {interval} days"
        case rrule.WEEKLY:
            base = "every week" if interval == 1 else f"every {interval} weeks"
        case rrule.MONTHLY:
            base = "every month" if interval == 1 else f"every {interval} months"
        case rrule.YEARLY:
            base = "every year" if interval == 1 else f"every {interval} years"
        case _:
            return ""

    qualifier = ""
    original = rule._original_rule

    match freq:
        case rrule.WEEKLY:
            if rule._byweekday:
                day_strs = [DAY_NAMES[d] + "s" for d in rule._byweekday]
                qualifier = f"on {p.join(day_strs)}"
        case rrule.MONTHLY | rrule.YEARLY:
            if rule._bynweekday:
                parts = [f"{ordinal_str(n)} {DAY_NAMES[d]}" for d, n in rule._bynweekday]
                qualifier = f"on the {p.join(parts)}"
            elif rule._bysetpos and rule._byweekday:
                parts = [
                    f"{ordinal_str(pos)} {DAY_NAMES[d]}"
                    for pos in rule._bysetpos
                    for d in rule._byweekday
                ]
                qualifier = f"on the {p.join(parts)}"
            elif original.get("bymonthday") is not None:
                qualifier = f"on the {p.join([p.ordinal(str(d)) for d in rule._bymonthday])}"
            elif rule._bynmonthday:
                parts = ["last day" if d == -1 else f"{ordinal_str(d)} to last day" for d in rule._bynmonthday]
                qualifier = f"on the {p.join(parts)}"

            if freq == rrule.YEARLY and original.get("bymonth") is not None:
                month_str = p.join([MONTHS[m - 1] for m in rule._bymonth])
                qualifier = f"in {month_str}" + qualifier

    return f"{base} {qualifier}"


class ChoreGetModel(ChoreCreateModel):
    id: types.PositiveInt
    created_at: datetime
    updated_at: datetime

    @computed_field
    @cached_property
    def rrules_translation(self) -> str | None:
        if self.rrules is None:
            return None

        translations = []
        for rule_str in self.rrules:
            try:
                parsed = rrule.rrulestr(rule_str)
                rules = parsed._rrule if isinstance(parsed, rrule.rruleset) else [parsed]
                translations.extend(_translate_single_rrule(r) for r in rules)
            except Exception:
                translations.append(rule_str)

        return "; ".join(translations) if translations else None


ChoreListModel = TypeAdapter(list[ChoreGetModel])
