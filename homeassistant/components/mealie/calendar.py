"""Calendar platform for Mealie."""

from datetime import datetime
from typing import override

from aiomealie import Mealplan, MealplanEntryType

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import LEGACY_MEALPLAN_ENTRY_TYPES, MEALIE_MULTIPLE_ENTRY_TYPES_VERSION
from .coordinator import MealieConfigEntry, MealieMealplanCoordinator
from .entity import MealieEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MealieConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the calendar platform for entity."""
    coordinator = entry.runtime_data.mealplan_coordinator
    version = entry.runtime_data.version

    supported_mealplan_entry_types: tuple[MealplanEntryType, ...]
    if version.valid and version < MEALIE_MULTIPLE_ENTRY_TYPES_VERSION:
        supported_mealplan_entry_types = LEGACY_MEALPLAN_ENTRY_TYPES
    else:
        # For Mealie 3.7.0 and newer and nightlies, add all current mealplan entry types
        supported_mealplan_entry_types = tuple(MealplanEntryType)

    async_add_entities(
        MealieMealplanCalendarEntity(coordinator, entry_type)
        for entry_type in supported_mealplan_entry_types
    )


def _get_event_from_mealplan(mealplan: Mealplan) -> CalendarEvent:
    """Create a CalendarEvent from a Mealplan."""
    description: str | None = mealplan.description
    name = mealplan.title or "No recipe"
    if mealplan.recipe:
        name = mealplan.recipe.name
        description = mealplan.recipe.description
    return CalendarEvent(
        start=mealplan.mealplan_date,
        end=mealplan.mealplan_date,
        summary=name,
        description=description,
    )


class MealieMealplanCalendarEntity(MealieEntity, CalendarEntity):
    """A calendar entity."""

    def __init__(
        self, coordinator: MealieMealplanCoordinator, entry_type: MealplanEntryType
    ) -> None:
        """Create the Calendar entity."""
        super().__init__(coordinator, entry_type.name.lower())
        self._entry_type = entry_type
        self._attr_translation_key = entry_type.name.lower()

    @property
    @override
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        mealplans = self.coordinator.data[self._entry_type]
        if not mealplans:
            return None
        sorted_mealplans = sorted(mealplans, key=lambda x: x.mealplan_date)
        return _get_event_from_mealplan(sorted_mealplans[0])

    @override
    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Get all events in a specific time frame."""
        mealplans = (
            await self.coordinator.client.get_mealplans(
                start_date.date(), end_date.date()
            )
        ).items
        return [
            _get_event_from_mealplan(mealplan)
            for mealplan in mealplans
            if mealplan.entry_type is self._entry_type
        ]
