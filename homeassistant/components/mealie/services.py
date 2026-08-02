"""Define services for the Mealie integration."""

from collections.abc import Callable, Coroutine
from dataclasses import asdict
from functools import wraps
from typing import Any

from aiomealie import (
    MealieConnectionError,
    MealieNotFoundError,
    MealieValidationError,
    MealplanEntryType,
)
from awesomeversion import AwesomeVersion
import voluptuous as vol

from homeassistant.components.todo import DOMAIN as TODO_DOMAIN
from homeassistant.const import ATTR_CONFIG_ENTRY_ID, ATTR_DATE
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, service
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_END_DATE,
    ATTR_ENTRY_TYPE,
    ATTR_INCLUDE_TAGS,
    ATTR_MEALPLAN_ID,
    ATTR_NOTE_TEXT,
    ATTR_NOTE_TITLE,
    ATTR_RECIPE_ID,
    ATTR_RESULT_LIMIT,
    ATTR_SEARCH_TERMS,
    ATTR_START_DATE,
    ATTR_URL,
    DOMAIN,
    LEGACY_MEALPLAN_ENTRY_TYPES,
    MEALIE_MULTIPLE_ENTRY_TYPES_VERSION,
)
from .coordinator import MealieConfigEntry

SERVICE_GET_MEALPLAN = "get_mealplan"
SERVICE_GET_MEALPLAN_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Optional(ATTR_START_DATE): cv.date,
        vol.Optional(ATTR_END_DATE): cv.date,
    }
)

SERVICE_GET_RECIPE = "get_recipe"
SERVICE_GET_RECIPE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_RECIPE_ID): str,
    }
)

SERVICE_GET_RECIPES = "get_recipes"
SERVICE_GET_RECIPES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Optional(ATTR_SEARCH_TERMS): str,
        vol.Optional(ATTR_RESULT_LIMIT): int,
    }
)

SERVICE_GET_SHOPPING_LIST_ITEMS = "get_shopping_list_items"

SERVICE_IMPORT_RECIPE = "import_recipe"
SERVICE_IMPORT_RECIPE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_URL): str,
        vol.Optional(ATTR_INCLUDE_TAGS): bool,
    }
)

SERVICE_SET_RANDOM_MEALPLAN = "set_random_mealplan"
SERVICE_SET_RANDOM_MEALPLAN_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_DATE): cv.date,
        vol.Required(ATTR_ENTRY_TYPE): vol.In([x.lower() for x in MealplanEntryType]),
    }
)

# Shared building blocks for the set/update mealplan schemas: a mealplan entry either
# references a recipe or holds a free-form note.
_MEALPLAN_ENTRY_BASE: dict[Any, Any] = {
    vol.Required(ATTR_CONFIG_ENTRY_ID): str,
    vol.Required(ATTR_DATE): cv.date,
    vol.Required(ATTR_ENTRY_TYPE): vol.In([x.lower() for x in MealplanEntryType]),
}
_MEALPLAN_RECIPE_ENTRY: dict[Any, Any] = {
    **_MEALPLAN_ENTRY_BASE,
    vol.Required(ATTR_RECIPE_ID): str,
}
_MEALPLAN_NOTE_ENTRY: dict[Any, Any] = {
    **_MEALPLAN_ENTRY_BASE,
    vol.Required(ATTR_NOTE_TITLE): str,
    vol.Optional(ATTR_NOTE_TEXT): str,
}

SERVICE_SET_MEALPLAN = "set_mealplan"
SERVICE_SET_MEALPLAN_SCHEMA = vol.Any(
    vol.Schema(_MEALPLAN_RECIPE_ENTRY),
    vol.Schema(_MEALPLAN_NOTE_ENTRY),
)

SERVICE_UPDATE_MEALPLAN = "update_mealplan"
SERVICE_UPDATE_MEALPLAN_SCHEMA = vol.Any(
    vol.Schema({vol.Required(ATTR_MEALPLAN_ID): int, **_MEALPLAN_RECIPE_ENTRY}),
    vol.Schema({vol.Required(ATTR_MEALPLAN_ID): int, **_MEALPLAN_NOTE_ENTRY}),
)

SERVICE_DELETE_MEALPLAN = "delete_mealplan"
SERVICE_DELETE_MEALPLAN_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_MEALPLAN_ID): int,
    }
)


def _get_entry(call: ServiceCall) -> MealieConfigEntry:
    """Get the Mealie config entry targeted by the service call."""
    return service.async_get_config_entry(
        call.hass, DOMAIN, call.data[ATTR_CONFIG_ENTRY_ID]
    )


def _handle_mealie_errors[_R](
    func: Callable[[ServiceCall], Coroutine[Any, Any, _R]],
) -> Callable[[ServiceCall], Coroutine[Any, Any, _R]]:
    """Translate Mealie connection errors into a HomeAssistantError."""

    @wraps(func)
    async def wrapper(call: ServiceCall) -> _R:
        try:
            return await func(call)
        except MealieConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from err

    return wrapper


def _validate_mealplan_type(version: AwesomeVersion, entry_type: str) -> None:
    """Validate mealplan entry type, if prior to 3.7.0."""

    if (
        version.valid
        and version < MEALIE_MULTIPLE_ENTRY_TYPES_VERSION
        and entry_type not in {x.value for x in LEGACY_MEALPLAN_ENTRY_TYPES}
    ):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_mealplan_entry_type",
            translation_placeholders={"mealplan_type": entry_type},
        )


@_handle_mealie_errors
async def _async_get_mealplan(call: ServiceCall) -> ServiceResponse:
    """Get the mealplan for a specific range."""
    entry = _get_entry(call)
    start_date = call.data.get(ATTR_START_DATE, dt_util.now().date())
    end_date = call.data.get(ATTR_END_DATE, dt_util.now().date())
    if end_date < start_date:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="end_date_before_start_date",
        )
    client = entry.runtime_data.client
    mealplans = await client.get_mealplans(start_date, end_date)
    return {"mealplan": [asdict(x) for x in mealplans.items]}


@_handle_mealie_errors
async def _async_get_recipe(call: ServiceCall) -> ServiceResponse:
    """Get a recipe."""
    entry = _get_entry(call)
    recipe_id = call.data[ATTR_RECIPE_ID]
    client = entry.runtime_data.client
    try:
        recipe = await client.get_recipe(recipe_id)
    except MealieNotFoundError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="recipe_not_found",
            translation_placeholders={"recipe_id": recipe_id},
        ) from err
    return {"recipe": asdict(recipe)}


@_handle_mealie_errors
async def _async_get_recipes(call: ServiceCall) -> ServiceResponse:
    """Get recipes."""
    entry = _get_entry(call)
    search_terms = call.data.get(ATTR_SEARCH_TERMS)
    result_limit = call.data.get(ATTR_RESULT_LIMIT, 10)
    client = entry.runtime_data.client
    try:
        recipes = await client.get_recipes(search=search_terms, per_page=result_limit)
    except MealieNotFoundError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="no_recipes_found",
        ) from err
    return {"recipes": asdict(recipes)}


@_handle_mealie_errors
async def _async_import_recipe(call: ServiceCall) -> ServiceResponse:
    """Import a recipe."""
    entry = _get_entry(call)
    url = call.data[ATTR_URL]
    include_tags = call.data.get(ATTR_INCLUDE_TAGS, False)
    client = entry.runtime_data.client
    try:
        recipe = await client.import_recipe(url, include_tags)
    except MealieValidationError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="could_not_import_recipe",
        ) from err
    if call.return_response:
        return {"recipe": asdict(recipe)}
    return None


@_handle_mealie_errors
async def _async_set_random_mealplan(call: ServiceCall) -> ServiceResponse:
    """Set a random mealplan."""
    entry = _get_entry(call)
    mealplan_date = call.data[ATTR_DATE]
    entry_type = MealplanEntryType(call.data[ATTR_ENTRY_TYPE])
    client = entry.runtime_data.client

    _validate_mealplan_type(entry.runtime_data.version, entry_type.value)

    mealplan = await client.random_mealplan(mealplan_date, entry_type)
    if call.return_response:
        return {"mealplan": asdict(mealplan)}
    return None


@_handle_mealie_errors
async def _async_set_mealplan(call: ServiceCall) -> ServiceResponse:
    """Set a mealplan."""
    entry = _get_entry(call)
    mealplan_date = call.data[ATTR_DATE]
    entry_type = MealplanEntryType(call.data[ATTR_ENTRY_TYPE])
    client = entry.runtime_data.client

    _validate_mealplan_type(entry.runtime_data.version, entry_type.value)

    mealplan = await client.set_mealplan(
        mealplan_date,
        entry_type,
        recipe_id=call.data.get(ATTR_RECIPE_ID),
        note_title=call.data.get(ATTR_NOTE_TITLE),
        note_text=call.data.get(ATTR_NOTE_TEXT),
    )
    if call.return_response:
        return {"mealplan": asdict(mealplan)}
    return None


@_handle_mealie_errors
async def _async_update_mealplan(call: ServiceCall) -> ServiceResponse:
    """Update an existing mealplan entry."""
    entry = _get_entry(call)
    mealplan_id = call.data[ATTR_MEALPLAN_ID]
    mealplan_date = call.data[ATTR_DATE]
    entry_type = MealplanEntryType(call.data[ATTR_ENTRY_TYPE])
    client = entry.runtime_data.client

    _validate_mealplan_type(entry.runtime_data.version, entry_type.value)

    try:
        result = await client.update_mealplan(
            mealplan_id,
            mealplan_date,
            entry_type,
            recipe_id=call.data.get(ATTR_RECIPE_ID),
            note_title=call.data.get(ATTR_NOTE_TITLE),
            note_text=call.data.get(ATTR_NOTE_TEXT),
        )
    except MealieNotFoundError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="mealplan_not_found",
            translation_placeholders={"mealplan_id": str(mealplan_id)},
        ) from err
    await entry.runtime_data.mealplan_coordinator.async_request_refresh()
    if call.return_response:
        return {"mealplan": asdict(result)}
    return None


@_handle_mealie_errors
async def _async_delete_mealplan(call: ServiceCall) -> None:
    """Delete a mealplan entry."""
    entry = _get_entry(call)
    mealplan_id = call.data[ATTR_MEALPLAN_ID]
    client = entry.runtime_data.client
    try:
        await client.delete_mealplan(mealplan_id)
    except MealieNotFoundError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="mealplan_not_found",
            translation_placeholders={"mealplan_id": str(mealplan_id)},
        ) from err
    await entry.runtime_data.mealplan_coordinator.async_request_refresh()


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the services for the Mealie integration."""

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_MEALPLAN,
        _async_get_mealplan,
        schema=SERVICE_GET_MEALPLAN_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_RECIPE,
        _async_get_recipe,
        schema=SERVICE_GET_RECIPE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_RECIPES,
        _async_get_recipes,
        schema=SERVICE_GET_RECIPES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_RECIPE,
        _async_import_recipe,
        schema=SERVICE_IMPORT_RECIPE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_RANDOM_MEALPLAN,
        _async_set_random_mealplan,
        schema=SERVICE_SET_RANDOM_MEALPLAN_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MEALPLAN,
        _async_set_mealplan,
        schema=SERVICE_SET_MEALPLAN_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_GET_SHOPPING_LIST_ITEMS,
        entity_domain=TODO_DOMAIN,
        schema=None,
        func="async_get_shopping_list_items",
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_MEALPLAN,
        _async_update_mealplan,
        schema=SERVICE_UPDATE_MEALPLAN_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_MEALPLAN,
        _async_delete_mealplan,
        schema=SERVICE_DELETE_MEALPLAN_SCHEMA,
    )
