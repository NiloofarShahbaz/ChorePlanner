import asyncio
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RadioButton,
    RadioSet,
    Select,
    Static,
)

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.chores_planner.models.calendar_event import CalendarEvent, StatusChoices
from src.chores_planner.models.chore import Chore
from src.chores_planner.serializers.chore import ChoreCreateModel
from src.chores_planner.services.google_calendar import GoogleCalendarService
from src.db import get_session


# -- Chore List Screen --------------------------------------------------------

class ChoreListScreen(Screen):
    BINDINGS = [
        Binding("n", "new_chore", "New Chore"),
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    #top-bar {
        height: 3;
        align: right middle;
        padding: 0 1;
    }
    #chore-table {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top-bar"):
            yield Button("+ New Chore", id="btn-new", variant="success")
        yield DataTable(id="chore-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("ID", "Name", "Duration", "Start From", "Schedule")
        self.load_chores()

    @work
    async def load_chores(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        async with get_session() as db:
            result = await db.execute(select(Chore).order_by(Chore.id))
            chores = result.scalars().all()
        for chore in chores:
            duration_mins = int(chore.duration.total_seconds() // 60)
            start = chore.start_from.strftime("%Y-%m-%d %H:%M") if chore.start_from else "-"
            schedule = ", ".join(chore.rrules) if chore.rrules else "-"
            table.add_row(
                str(chore.id),
                chore.name,
                f"{duration_mins} min",
                start,
                schedule,
                key=str(chore.id),
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        chore_id = int(event.row_key.value)
        self.app.push_screen(ChoreDetailScreen(chore_id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-new":
            self.action_new_chore()

    def action_new_chore(self) -> None:
        self.app.push_screen(CreateChoreScreen())

    def action_quit(self) -> None:
        self.app.exit()


# -- Create Chore Screen -----------------------------------------------------

ORDINAL_NAMES = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}


def nth_weekday_of_month(dt: datetime) -> tuple[int, int]:
    """Return (occurrence_number, weekday_index) for a date.
    E.g. 2nd Friday -> (2, 4)
    """
    return (dt.day - 1) // 7 + 1, dt.weekday()


FREQUENCY_OPTIONS = [
    ("None (one-time)", "none"),
    ("Daily", "DAILY"),
    ("Weekly", "WEEKLY"),
    ("Monthly", "MONTHLY"),
    ("Yearly", "YEARLY"),
]

WEEKDAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class CreateChoreScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    CSS = """
    CreateChoreScreen {
        align: center middle;
    }
    #create-form {
        width: 70;
        max-height: 80%;
        border: solid $accent;
        padding: 1 2;
    }
    #create-form Label {
        margin-top: 1;
    }
    #form-buttons {
        height: 3;
        margin-top: 1;
        align: center middle;
    }
    #form-buttons Button {
        margin: 0 1;
    }
    #create-status {
        margin-top: 1;
    }
    #weekday-row-1, #weekday-row-2 {
        height: 3;
        margin-top: 0;
    }
    #weekday-row-1 Checkbox, #weekday-row-2 Checkbox {
        width: auto;
        margin: 0 1 0 0;
    }
    .freq-conditional {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="create-form"):
            yield Label("[bold]Create New Chore[/bold]")

            yield Label("Name")
            yield Input(placeholder="e.g. Vacuum the house", id="input-name")

            yield Label("Duration in minutes (default: 30)")
            yield Input(placeholder="30", id="input-duration", value="30")

            yield Label("Start from (default: now)")
            yield Input(
                placeholder="YYYY-MM-DD HH:MM",
                id="input-start-from",
                value=datetime.now().strftime("%Y-%m-%d %H:%M"),
            )

            yield Label("Frequency")
            yield Select(FREQUENCY_OPTIONS, value="none", id="select-freq")

            yield Label("Repeat every N periods (default: 1)")
            yield Input(placeholder="1", id="input-interval", value="1")

            with Vertical(id="weekly-options", classes="freq-conditional"):
                yield Label("On days")
                with Horizontal(id="weekday-row-1"):
                    for code, label in zip(WEEKDAY_CODES[:4], WEEKDAY_LABELS[:4]):
                        yield Checkbox(label, id=f"day-{code}")
                with Horizontal(id="weekday-row-2"):
                    for code, label in zip(WEEKDAY_CODES[4:], WEEKDAY_LABELS[4:]):
                        yield Checkbox(label, id=f"day-{code}")

            with Vertical(id="monthly-options", classes="freq-conditional"):
                yield Label("Repeat on")
                with RadioSet(id="monthly-type"):
                    yield RadioButton("On day of month", id="radio-monthday", value=True)
                    yield RadioButton("On nth weekday", id="radio-nthday")
                yield Static("", id="monthly-description")

            yield Label("Generated rule (editable)")
            yield Input(placeholder="RRULE:FREQ=...", id="input-rrule")

            with Horizontal(id="form-buttons"):
                yield Button("Create", id="btn-create", variant="success")
                yield Button("Cancel", id="btn-cancel", variant="error")

            yield Static("", id="create-status")
        yield Footer()

    def on_mount(self) -> None:
        self._update_freq_visibility()

    @on(Select.Changed, "#select-freq")
    def on_freq_changed(self, event: Select.Changed) -> None:
        self._update_freq_visibility()
        self._update_rrule_preview()

    @on(Input.Changed, "#input-interval")
    def on_interval_changed(self, event: Input.Changed) -> None:
        self._update_rrule_preview()

    @on(Input.Changed, "#input-start-from")
    def on_start_changed(self, event: Input.Changed) -> None:
        self._update_monthly_description()
        self._update_rrule_preview()

    @on(RadioSet.Changed, "#monthly-type")
    def on_monthly_type_changed(self, event: RadioSet.Changed) -> None:
        self._update_rrule_preview()

    @on(Checkbox.Changed)
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        self._update_rrule_preview()

    def _get_start_date(self) -> datetime:
        start_str = self.query_one("#input-start-from", Input).value.strip()
        try:
            return datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return datetime.now()

    def _update_freq_visibility(self) -> None:
        freq = self.query_one("#select-freq", Select).value
        self.query_one("#input-interval").display = freq != "none"
        self.query_one("#weekly-options").display = freq == "WEEKLY"
        self.query_one("#monthly-options").display = freq == "MONTHLY"
        if freq == "MONTHLY":
            self._update_monthly_description()

    def _update_monthly_description(self) -> None:
        dt = self._get_start_date()
        nth, weekday_idx = nth_weekday_of_month(dt)
        day_name = WEEKDAY_LABELS[weekday_idx]
        ordinal = ORDINAL_NAMES.get(nth, f"{nth}th")
        desc = self.query_one("#monthly-description", Static)
        radio_monthday = self.query_one("#radio-monthday", RadioButton)
        radio_nthday = self.query_one("#radio-nthday", RadioButton)
        radio_monthday.label = f"On the {dt.day}th of every month"
        radio_nthday.label = f"On the {ordinal} {day_name} of every month"
        if radio_monthday.value:
            desc.update(f"[dim]BYMONTHDAY={dt.day}[/dim]")
        else:
            desc.update(f"[dim]BYDAY={WEEKDAY_CODES[weekday_idx]};BYSETPOS={nth}[/dim]")

    def _build_rrule(self) -> str | None:
        freq = self.query_one("#select-freq", Select).value
        if freq == "none" or freq == Select.BLANK:
            return None

        interval_str = self.query_one("#input-interval", Input).value.strip()
        interval = int(interval_str) if interval_str and interval_str.isdigit() else 1

        parts = [f"RRULE:FREQ={freq}"]
        if interval > 1:
            parts.append(f"INTERVAL={interval}")

        if freq == "WEEKLY":
            days = []
            for code in WEEKDAY_CODES:
                cb = self.query_one(f"#day-{code}", Checkbox)
                if cb.value:
                    days.append(code)
            if days:
                parts.append(f"BYDAY={','.join(days)}")

        if freq == "MONTHLY":
            dt = self._get_start_date()
            radio_monthday = self.query_one("#radio-monthday", RadioButton)
            if radio_monthday.value:
                parts.append(f"BYMONTHDAY={dt.day}")
            else:
                nth, weekday_idx = nth_weekday_of_month(dt)
                parts.append(f"BYDAY={WEEKDAY_CODES[weekday_idx]}")
                parts.append(f"BYSETPOS={nth}")

        return ";".join(parts)

    def _update_rrule_preview(self) -> None:
        rrule = self._build_rrule()
        input_rrule = self.query_one("#input-rrule", Input)
        input_rrule.value = rrule or ""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-create":
            self.create_chore()
        elif event.button.id == "btn-cancel":
            self.action_go_back()

    @work
    async def create_chore(self) -> None:
        status = self.query_one("#create-status", Static)
        status.update("")

        name = self.query_one("#input-name", Input).value.strip()
        if not name:
            status.update("[red]Name is required[/red]")
            return

        duration_str = self.query_one("#input-duration", Input).value.strip()
        try:
            duration = timedelta(minutes=int(duration_str)) if duration_str else timedelta(minutes=30)
        except ValueError:
            status.update("[red]Duration must be a number[/red]")
            return

        start_str = self.query_one("#input-start-from", Input).value.strip()
        try:
            start_from = datetime.strptime(start_str, "%Y-%m-%d %H:%M") if start_str else datetime.now()
        except ValueError:
            status.update("[red]Invalid date format. Use YYYY-MM-DD HH:MM[/red]")
            return

        rrule_str = self.query_one("#input-rrule", Input).value.strip()
        rrules = [rrule_str] if rrule_str else None

        try:
            chore_data = ChoreCreateModel(
                name=name,
                duration=duration,
                start_from=start_from,
                rrules=rrules,
            )
        except Exception as e:
            status.update(f"[red]Validation error: {e}[/red]")
            return

        status.update("[yellow]Creating chore & calendar event... (check your browser if login is needed)[/yellow]")

        try:
            svc = GoogleCalendarService()
            async with get_session() as db:
                await svc.create_calendar_events(chore_data, db)
            status.update(f"[green]Chore '{name}' created![/green]")
            await asyncio.sleep(1)
            self.app.pop_screen()
        except Exception as e:
            status.update(f"[red]Error: {e}[/red]")

    def action_go_back(self) -> None:
        self.app.pop_screen()


# -- Event Row Widget ---------------------------------------------------------

# -- Chore Detail Screen ------------------------------------------------------

EVENTS_PAGE_SIZE = 5


class ChoreDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    CSS = """
    #detail-header {
        height: auto;
        padding: 1 2;
        border-bottom: solid $accent;
    }
    #detail-title-row {
        height: 3;
    }
    #detail-title-row Static {
        width: 1fr;
        content-align-vertical: middle;
    }
    #detail-title-row Button {
        width: auto;
    }
    #confirm-delete-row {
        height: 3;
        width: auto;
    }
    #confirm-delete-row Static {
        width: auto;
        content-align-vertical: middle;
        margin: 0 1;
    }
    #confirm-delete-row Button {
        width: auto;
        margin: 0 1;
    }
    #events-section {
        height: 1fr;
        padding: 1 2;
    }
    #events-list {
        height: auto;
    }
    .event-row {
        height: 3;
        padding: 0 1;
        border-bottom: dashed $surface-lighten-2;
    }
    .event-row Static {
        width: 1fr;
        content-align-vertical: middle;
    }
    .event-row Button {
        width: auto;
    }
    #btn-show-more {
        margin: 1 0;
    }
    #detail-status {
        height: 1;
        margin: 0 2 1 2;
    }
    """

    def __init__(self, chore_id: int) -> None:
        super().__init__()
        self.chore_id = chore_id
        self.events_shown = EVENTS_PAGE_SIZE
        self._all_events: list[CalendarEvent] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="detail-header"):
            with Horizontal(id="detail-title-row"):
                yield Static("Loading...", id="chore-name")
                yield Button("Delete Chore", id="btn-delete", variant="error")
            yield Static("", id="chore-info")
        with VerticalScroll(id="events-section"):
            yield Label("[bold]Calendar Events[/bold]")
            yield Vertical(id="events-list")
            yield Button("Show More", id="btn-show-more", variant="primary")
        yield Static("", id="detail-status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#btn-show-more", Button).display = False
        self.load_detail()

    @work
    async def load_detail(self) -> None:
        async with get_session() as db:
            result = await db.execute(
                select(Chore)
                .options(selectinload(Chore.events))
                .where(Chore.id == self.chore_id)
            )
            chore = result.scalar_one_or_none()

        if chore is None:
            self.query_one("#chore-name", Static).update("[red]Chore not found[/red]")
            return

        self.query_one("#chore-name", Static).update(f"[bold]{chore.name}[/bold]")

        duration_mins = int(chore.duration.total_seconds() // 60)
        start = chore.start_from.strftime("%Y-%m-%d %H:%M") if chore.start_from else "-"
        schedule = ", ".join(chore.rrules) if chore.rrules else "No recurrence"
        self.query_one("#chore-info", Static).update(
            f"Duration: {duration_mins} min  |  Start: {start}  |  Schedule: {schedule}"
        )

        self._all_events = sorted(
            [e for e in chore.events if not e.is_parent],
            key=lambda e: e.starts_from,
        )
        self._render_events()

    def _render_events(self) -> None:
        container = self.query_one("#events-list", Vertical)
        container.remove_children()

        visible = self._all_events[: self.events_shown]

        if not visible:
            container.mount(Static("[dim]No calendar events yet[/dim]"))
        else:
            for ev in visible:
                date_str = ev.starts_from.strftime("%Y-%m-%d %H:%M")
                gcal_id = ev.calendar_event_id[:20]
                if ev.status == StatusChoices.DONE:
                    row = Horizontal(
                        Static(f"  [green]done[/green]  {date_str}  {gcal_id}"),
                        classes="event-row",
                    )
                else:
                    row = Horizontal(
                        Static(f"  [yellow]{ev.status.value.lower()}[/yellow]  {date_str}  {gcal_id}"),
                        Button("Mark Done", id=f"done-{ev.id}", variant="success"),
                        classes="event-row",
                    )
                container.mount(row)

        btn = self.query_one("#btn-show-more", Button)
        btn.display = len(self._all_events) > self.events_shown

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-show-more":
            self.events_shown += EVENTS_PAGE_SIZE
            self._render_events()
        elif event.button.id == "btn-delete":
            self.query_one("#btn-delete", Button).display = False
            confirm_row = Horizontal(
                Static("Are you sure?"),
                Button("Yes, delete", id="btn-confirm-delete", variant="error"),
                Button("Cancel", id="btn-cancel-delete"),
                id="confirm-delete-row",
            )
            self.query_one("#detail-title-row").mount(confirm_row)
        elif event.button.id == "btn-confirm-delete":
            self.delete_chore()
        elif event.button.id == "btn-cancel-delete":
            self.query_one("#confirm-delete-row").remove()
            self.query_one("#btn-delete", Button).display = True
        elif event.button.id and event.button.id.startswith("done-"):
            event_id = int(event.button.id.removeprefix("done-"))
            self.mark_event_done(event_id)

    @work
    async def mark_event_done(self, event_id: int) -> None:
        status_widget = self.query_one("#detail-status", Static)
        status_widget.update(f"[yellow]Marking event {event_id} as done... (check your browser if login is needed)[/yellow]")
        try:
            svc = GoogleCalendarService()
            async with get_session() as db:
                await svc.update_event_status(event_id, StatusChoices.DONE, db)
            status_widget.update(f"[green]Event {event_id} marked as done![/green]")
            self.load_detail()
        except Exception as e:
            status_widget.update(f"[red]Error: {e}[/red]")

    @work
    async def delete_chore(self) -> None:
        status_widget = self.query_one("#detail-status", Static)
        status_widget.update("[yellow]Deleting chore... (check your browser if login is needed)[/yellow]")
        try:
            svc = GoogleCalendarService()
            async with get_session() as db:
                await svc.delete_chore(self.chore_id, db)
            self.app.pop_screen()
        except Exception as e:
            status_widget.update(f"[red]Error: {e}[/red]")

    def action_go_back(self) -> None:
        self.app.pop_screen()


# -- Main App -----------------------------------------------------------------

class ChoresPlannerApp(App):
    TITLE = "ChoresPlanner"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def on_mount(self) -> None:
        self.push_screen(ChoreListScreen())

    def on_screen_resume(self, event) -> None:
        screen = self.screen
        if isinstance(screen, ChoreListScreen):
            screen.load_chores()


if __name__ == "__main__":
    app = ChoresPlannerApp()
    app.run()
