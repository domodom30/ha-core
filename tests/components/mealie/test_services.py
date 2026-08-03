"""Tests for the Mealie services."""

from datetime import date
from unittest.mock import AsyncMock

from aiomealie import (
    About,
    MealieAuthenticationError,
    MealieBadRequestError,
    MealieConnectionError,
    MealieNotFoundError,
    MealieValidationError,
    MealplanEntryType,
)
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion
import voluptuous as vol

from homeassistant.components.mealie.const import (
    ATTR_END_DATE,
    ATTR_ENTRY_TYPE,
    ATTR_INCLUDE_TAGS,
    ATTR_MEALPLAN_ID,
    ATTR_NOTE_TEXT,
    ATTR_NOTE_TITLE,
    ATTR_RATING,
    ATTR_RECIPE_ID,
    ATTR_RECIPE_INCREMENT_QUANTITY,
    ATTR_RECIPE_SLUG,
    ATTR_RESULT_LIMIT,
    ATTR_SEARCH_TERMS,
    ATTR_SHOPPING_LIST_ID,
    ATTR_START_DATE,
    ATTR_URL,
    DOMAIN,
)
from homeassistant.components.mealie.services import (
    SERVICE_ADD_RECIPE_FAVORITE,
    SERVICE_ADD_RECIPE_TO_SHOPPING_LIST,
    SERVICE_DELETE_MEALPLAN,
    SERVICE_GET_MEALPLAN,
    SERVICE_GET_RECIPE,
    SERVICE_GET_RECIPE_FAVORITES,
    SERVICE_GET_RECIPES,
    SERVICE_GET_SHOPPING_LIST_ITEMS,
    SERVICE_GET_SHOPPING_LISTS,
    SERVICE_IMPORT_RECIPE,
    SERVICE_RATE_RECIPE,
    SERVICE_REMOVE_RECIPE_FAVORITE,
    SERVICE_SET_MEALPLAN,
    SERVICE_SET_RANDOM_MEALPLAN,
    SERVICE_UPDATE_MEALPLAN,
)
from homeassistant.const import ATTR_CONFIG_ENTRY_ID, ATTR_DATE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from . import setup_integration

from tests.common import MockConfigEntry


async def test_service_mealplan(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the get_mealplan service."""

    await setup_integration(hass, mock_config_entry)

    freezer.move_to("2023-10-21T12:00:00-07:00")

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEALPLAN,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
        blocking=True,
        return_response=True,
    )
    assert mock_mealie_client.get_mealplans.call_args_list[1][0] == (
        date(2023, 10, 21),
        date(2023, 10, 21),
    )
    assert response == snapshot

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEALPLAN,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_START_DATE: "2023-10-22",
            ATTR_END_DATE: "2023-10-25",
        },
        blocking=True,
        return_response=True,
    )
    assert response
    assert mock_mealie_client.get_mealplans.call_args_list[2][0] == (
        date(2023, 10, 22),
        date(2023, 10, 25),
    )

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEALPLAN,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_START_DATE: "2023-10-19",
        },
        blocking=True,
        return_response=True,
    )
    assert response
    assert mock_mealie_client.get_mealplans.call_args_list[3][0] == (
        date(2023, 10, 19),
        date(2023, 10, 21),
    )

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MEALPLAN,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_END_DATE: "2023-10-22",
        },
        blocking=True,
        return_response=True,
    )
    assert response
    assert mock_mealie_client.get_mealplans.call_args_list[4][0] == (
        date(2023, 10, 21),
        date(2023, 10, 22),
    )

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_MEALPLAN,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                ATTR_START_DATE: "2023-10-22",
                ATTR_END_DATE: "2023-10-19",
            },
            blocking=True,
            return_response=True,
        )


async def test_service_recipe(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the get_recipe service."""

    await setup_integration(hass, mock_config_entry)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_RECIPE,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id, ATTR_RECIPE_ID: "recipe_id"},
        blocking=True,
        return_response=True,
    )
    assert response == snapshot


@pytest.mark.parametrize(
    "service_data",
    [
        # Default call
        {ATTR_CONFIG_ENTRY_ID: "mock_entry_id"},
        # With search terms and result limit
        {
            ATTR_CONFIG_ENTRY_ID: "mock_entry_id",
            ATTR_SEARCH_TERMS: "pasta",
            ATTR_RESULT_LIMIT: 5,
        },
    ],
)
async def test_service_get_recipes(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    service_data: dict,
) -> None:
    """Test the get_recipes service."""
    await setup_integration(hass, mock_config_entry)

    # Patch entry_id into service_data for each run
    service_data = {**service_data, ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id}

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_RECIPES,
        service_data,
        blocking=True,
        return_response=True,
    )
    assert response == snapshot


async def test_service_import_recipe(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the import_recipe service."""

    await setup_integration(hass, mock_config_entry)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_IMPORT_RECIPE,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_URL: "http://example.com",
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot
    mock_mealie_client.import_recipe.assert_called_with(
        "http://example.com", include_tags=False
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_IMPORT_RECIPE,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_URL: "http://example.com",
            ATTR_INCLUDE_TAGS: True,
        },
        blocking=True,
        return_response=False,
    )
    mock_mealie_client.import_recipe.assert_called_with(
        "http://example.com", include_tags=True
    )


async def test_service_set_random_mealplan(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the set_random_mealplan service."""

    await setup_integration(hass, mock_config_entry)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_RANDOM_MEALPLAN,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_DATE: "2023-10-21",
            ATTR_ENTRY_TYPE: "lunch",
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot
    mock_mealie_client.random_mealplan.assert_called_with(
        date(2023, 10, 21), MealplanEntryType.LUNCH
    )

    mock_mealie_client.random_mealplan.reset_mock()
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_RANDOM_MEALPLAN,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_DATE: "2023-10-21",
            ATTR_ENTRY_TYPE: "lunch",
        },
        blocking=True,
        return_response=False,
    )
    mock_mealie_client.random_mealplan.assert_called_with(
        date(2023, 10, 21), MealplanEntryType.LUNCH
    )


async def test_service_set_random_mealplan_invalid_entry_type(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the set_random_mealplan service with invalid entry types for version."""
    mock_mealie_client.get_about.return_value = About(version="v3.6.0")

    await setup_integration(hass, mock_config_entry)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_RANDOM_MEALPLAN,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                ATTR_DATE: "2023-10-21",
                ATTR_ENTRY_TYPE: "dessert",
            },
            blocking=True,
            return_response=True,
        )
    mock_mealie_client.random_mealplan.assert_not_called()


@pytest.mark.parametrize(
    ("payload", "kwargs"),
    [
        (
            {
                ATTR_RECIPE_ID: "recipe_id",
            },
            {"recipe_id": "recipe_id", "note_title": None, "note_text": None},
        ),
        (
            {
                ATTR_NOTE_TITLE: "Note Title",
                ATTR_NOTE_TEXT: "Note Text",
            },
            {"recipe_id": None, "note_title": "Note Title", "note_text": "Note Text"},
        ),
        (
            {
                ATTR_NOTE_TITLE: "Note Title",
            },
            {"recipe_id": None, "note_title": "Note Title", "note_text": None},
        ),
    ],
)
async def test_service_set_mealplan(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    payload: dict[str, str],
    kwargs: dict[str, str],
) -> None:
    """Test the set_mealplan service."""

    await setup_integration(hass, mock_config_entry)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_MEALPLAN,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_DATE: "2023-10-21",
            ATTR_ENTRY_TYPE: "lunch",
        }
        | payload,
        blocking=True,
        return_response=True,
    )
    assert response == snapshot
    mock_mealie_client.set_mealplan.assert_called_with(
        date(2023, 10, 21), MealplanEntryType.LUNCH, **kwargs
    )

    mock_mealie_client.random_mealplan.reset_mock()
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_MEALPLAN,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_DATE: "2023-10-21",
            ATTR_ENTRY_TYPE: "lunch",
        }
        | payload,
        blocking=True,
        return_response=False,
    )
    mock_mealie_client.set_mealplan.assert_called_with(
        date(2023, 10, 21), MealplanEntryType.LUNCH, **kwargs
    )


async def test_service_set_mealplan_invalid_entry_type(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the set_mealplan service with invalid entry types for version."""
    mock_mealie_client.get_about.return_value = About(version="v3.6.0")

    await setup_integration(hass, mock_config_entry)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_MEALPLAN,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                ATTR_DATE: "2023-10-21",
                ATTR_ENTRY_TYPE: "dessert",
                ATTR_NOTE_TITLE: "Note Title",
            },
            blocking=True,
            return_response=True,
        )
    mock_mealie_client.set_mealplan.assert_not_called()


@pytest.mark.parametrize(
    ("service", "payload"),
    [
        pytest.param(SERVICE_SET_MEALPLAN, {ATTR_RECIPE_ID: "recipe-id"}, id="set"),
        pytest.param(SERVICE_SET_RANDOM_MEALPLAN, {}, id="random"),
    ],
)
async def test_service_create_mealplan_refreshes_coordinator(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    service: str,
    payload: dict[str, str],
) -> None:
    """Test creating a mealplan refreshes the mealplan coordinator."""

    await setup_integration(hass, mock_config_entry)
    mock_mealie_client.get_mealplans.reset_mock()

    await hass.services.async_call(
        DOMAIN,
        service,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_DATE: "2023-10-21",
            ATTR_ENTRY_TYPE: "lunch",
        }
        | payload,
        blocking=True,
    )

    mock_mealie_client.get_mealplans.assert_called()


@pytest.mark.parametrize(
    ("service", "payload"),
    [
        pytest.param(SERVICE_SET_MEALPLAN, {}, id="set_neither"),
        pytest.param(
            SERVICE_SET_MEALPLAN,
            {ATTR_RECIPE_ID: "recipe-id", ATTR_NOTE_TITLE: "Note"},
            id="set_both",
        ),
        pytest.param(
            SERVICE_SET_MEALPLAN, {ATTR_NOTE_TEXT: "Text"}, id="set_note_text_only"
        ),
        pytest.param(
            SERVICE_UPDATE_MEALPLAN, {ATTR_MEALPLAN_ID: 1}, id="update_neither"
        ),
        pytest.param(
            SERVICE_UPDATE_MEALPLAN,
            {
                ATTR_MEALPLAN_ID: 1,
                ATTR_RECIPE_ID: "recipe-id",
                ATTR_NOTE_TITLE: "Note",
            },
            id="update_both",
        ),
    ],
)
async def test_mealplan_content_is_exclusive(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    service: str,
    payload: dict[str, str | int],
) -> None:
    """Test a mealplan entry must reference either a recipe or a note, never both."""

    await setup_integration(hass, mock_config_entry)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            service,
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                ATTR_DATE: "2023-10-21",
                ATTR_ENTRY_TYPE: "lunch",
            }
            | payload,
            blocking=True,
        )


@pytest.mark.parametrize(
    ("mealplan_id", "expected"),
    [
        pytest.param(1, 1, id="int"),
        pytest.param("1", 1, id="string"),
        pytest.param(1.0, 1, id="float"),
    ],
)
async def test_service_delete_mealplan_coerces_id(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    mealplan_id: str | float,
    expected: int,
) -> None:
    """Test the mealplan ID is coerced to an integer."""

    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_DELETE_MEALPLAN,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_MEALPLAN_ID: mealplan_id,
        },
        blocking=True,
    )

    mock_mealie_client.delete_mealplan.assert_called_with(expected)


@pytest.mark.parametrize(
    ("service", "payload", "return_response"),
    [
        pytest.param(
            SERVICE_DELETE_MEALPLAN, {ATTR_MEALPLAN_ID: 0}, False, id="mealplan_id_zero"
        ),
        pytest.param(
            SERVICE_DELETE_MEALPLAN,
            {ATTR_MEALPLAN_ID: -1},
            False,
            id="mealplan_id_negative",
        ),
        pytest.param(
            SERVICE_GET_RECIPES, {ATTR_RESULT_LIMIT: 0}, True, id="result_limit_zero"
        ),
        pytest.param(
            SERVICE_IMPORT_RECIPE,
            {ATTR_URL: "not-a-url"},
            False,
            id="url_malformed",
        ),
        pytest.param(
            SERVICE_ADD_RECIPE_TO_SHOPPING_LIST,
            {
                ATTR_SHOPPING_LIST_ID: "shopping-list-id",
                ATTR_RECIPE_ID: "recipe-id",
                ATTR_RECIPE_INCREMENT_QUANTITY: 0,
            },
            False,
            id="quantity_zero",
        ),
        pytest.param(
            SERVICE_RATE_RECIPE,
            {ATTR_RECIPE_SLUG: "pizza-recipe", ATTR_RATING: 6},
            False,
            id="rating_above_max",
        ),
        pytest.param(
            SERVICE_RATE_RECIPE,
            {ATTR_RECIPE_SLUG: "pizza-recipe", ATTR_RATING: -1},
            False,
            id="rating_negative",
        ),
    ],
)
async def test_services_reject_invalid_values(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    service: str,
    payload: dict[str, str | int],
    return_response: bool,
) -> None:
    """Test out-of-range and malformed values are rejected by the schemas."""

    await setup_integration(hass, mock_config_entry)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            service,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id} | payload,
            blocking=True,
            return_response=return_response,
        )


async def test_service_get_recipes_accepts_large_limit(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test result_limit is not capped server side, unlike the selector hint."""

    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_RECIPES,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id, ATTR_RESULT_LIMIT: 9999},
        blocking=True,
        return_response=True,
    )

    mock_mealie_client.get_recipes.assert_called_with(search=None, per_page=9999)


async def test_service_import_recipe_coerces_include_tags(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test include_tags accepts the usual Home Assistant boolean spellings."""

    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_IMPORT_RECIPE,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_URL: "http://example.com",
            ATTR_INCLUDE_TAGS: "true",
        },
        blocking=True,
    )

    mock_mealie_client.import_recipe.assert_called_with(
        "http://example.com", include_tags=True
    )


async def test_service_rate_recipe_uses_whole_stars(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the rating reaches the client as a whole number of stars."""

    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RATE_RECIPE,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_RECIPE_SLUG: "pizza-recipe",
            ATTR_RATING: "4",
        },
        blocking=True,
    )

    rating = mock_mealie_client.rate_recipe.call_args.kwargs["rating"]
    assert rating == 4
    assert isinstance(rating, int)


async def test_service_get_shopping_lists(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the get_shopping_lists service."""

    await setup_integration(hass, mock_config_entry)
    mock_mealie_client.get_shopping_lists.reset_mock()

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_SHOPPING_LISTS,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
        blocking=True,
        return_response=True,
    )

    assert response == snapshot
    mock_mealie_client.get_shopping_lists.assert_not_called()


@pytest.mark.parametrize(
    ("exception", "message"),
    [
        (MealieAuthenticationError, "Authentication failed"),
        (MealieBadRequestError, "unexpected error occurred"),
    ],
)
async def test_service_translates_remaining_mealie_errors(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    exception: type[Exception],
    message: str,
) -> None:
    """Test authentication and unexpected Mealie errors reach the user translated."""

    await setup_integration(hass, mock_config_entry)

    mock_mealie_client.get_mealplans.side_effect = exception

    with pytest.raises(HomeAssistantError, match=message):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_MEALPLAN,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
            blocking=True,
            return_response=True,
        )


async def test_service_get_shopping_list_items(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the get_shopping_list_items service."""

    await setup_integration(hass, mock_config_entry)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_SHOPPING_LIST_ITEMS,
        target={"entity_id": "todo.mealie_supermarket"},
        blocking=True,
        return_response=True,
    )
    assert response == snapshot


async def test_service_get_shopping_list_items_connection_error(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the get_shopping_list_items service with connection error."""

    await setup_integration(hass, mock_config_entry)

    mock_mealie_client.get_shopping_items.side_effect = MealieConnectionError

    with pytest.raises(HomeAssistantError, match="Error connecting to Mealie instance"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_GET_SHOPPING_LIST_ITEMS,
            target={"entity_id": "todo.mealie_supermarket"},
            blocking=True,
            return_response=True,
        )


async def test_service_update_mealplan(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the update_mealplan service."""

    await setup_integration(hass, mock_config_entry)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_UPDATE_MEALPLAN,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_MEALPLAN_ID: 1,
            ATTR_DATE: "2023-10-21",
            ATTR_ENTRY_TYPE: "lunch",
            ATTR_RECIPE_ID: "recipe-id",
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot
    mock_mealie_client.update_mealplan.assert_called_with(
        1,
        date(2023, 10, 21),
        MealplanEntryType.LUNCH,
        recipe_id="recipe-id",
        note_title=None,
        note_text=None,
    )


async def test_service_delete_mealplan(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the delete_mealplan service."""

    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_DELETE_MEALPLAN,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id, ATTR_MEALPLAN_ID: 1},
        blocking=True,
    )
    mock_mealie_client.delete_mealplan.assert_called_with(1)


async def test_service_get_recipe_favorites(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the get_recipe_favorites service returns only favorites."""

    await setup_integration(hass, mock_config_entry)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_RECIPE_FAVORITES,
        {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
        blocking=True,
        return_response=True,
    )
    assert response == snapshot


@pytest.mark.parametrize(
    ("service", "function"),
    [
        (SERVICE_ADD_RECIPE_FAVORITE, "add_recipe_favorite"),
        (SERVICE_REMOVE_RECIPE_FAVORITE, "remove_recipe_favorite"),
    ],
)
async def test_service_recipe_favorite(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    service: str,
    function: str,
) -> None:
    """Test the add/remove recipe favorite services."""

    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        service,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_RECIPE_SLUG: "pizza-recipe",
        },
        blocking=True,
    )
    getattr(mock_mealie_client, function).assert_called_with("pizza-recipe")


async def test_service_rate_recipe(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the rate_recipe service."""

    await setup_integration(hass, mock_config_entry)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RATE_RECIPE,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_RECIPE_SLUG: "pizza-recipe",
            ATTR_RATING: 4,
        },
        blocking=True,
    )
    mock_mealie_client.rate_recipe.assert_called_with("pizza-recipe", rating=4)


async def test_service_add_recipe_to_shopping_list(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the add_recipe_to_shopping_list service."""

    await setup_integration(hass, mock_config_entry)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_ADD_RECIPE_TO_SHOPPING_LIST,
        {
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_SHOPPING_LIST_ID: "shopping-list-id",
            ATTR_RECIPE_ID: "recipe-id",
            ATTR_RECIPE_INCREMENT_QUANTITY: 2,
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot
    mock_mealie_client.add_recipe_to_shopping_list.assert_called_with(
        "shopping-list-id", "recipe-id", scale=2
    )


@pytest.mark.parametrize(
    ("service", "payload", "function", "exception", "raised_exception", "message"),
    [
        (
            SERVICE_GET_MEALPLAN,
            {},
            "get_mealplans",
            MealieConnectionError,
            HomeAssistantError,
            "Error connecting to Mealie instance",
        ),
        (
            SERVICE_GET_RECIPE,
            {ATTR_RECIPE_ID: "recipe_id"},
            "get_recipe",
            MealieConnectionError,
            HomeAssistantError,
            "Error connecting to Mealie instance",
        ),
        (
            SERVICE_GET_RECIPE,
            {ATTR_RECIPE_ID: "recipe_id"},
            "get_recipe",
            MealieNotFoundError,
            ServiceValidationError,
            "Recipe with ID or slug `recipe_id` not found",
        ),
        (
            SERVICE_GET_RECIPES,
            {},
            "get_recipes",
            MealieConnectionError,
            HomeAssistantError,
            "Error connecting to Mealie instance",
        ),
        (
            SERVICE_GET_RECIPES,
            {ATTR_SEARCH_TERMS: "pasta"},
            "get_recipes",
            MealieNotFoundError,
            ServiceValidationError,
            "No recipes found matching your search",
        ),
        (
            SERVICE_IMPORT_RECIPE,
            {ATTR_URL: "http://example.com"},
            "import_recipe",
            MealieConnectionError,
            HomeAssistantError,
            "Error connecting to Mealie instance",
        ),
        (
            SERVICE_IMPORT_RECIPE,
            {ATTR_URL: "http://example.com"},
            "import_recipe",
            MealieValidationError,
            ServiceValidationError,
            "Mealie could not import the recipe from the URL",
        ),
        (
            SERVICE_SET_RANDOM_MEALPLAN,
            {ATTR_DATE: "2023-10-21", ATTR_ENTRY_TYPE: "lunch"},
            "random_mealplan",
            MealieConnectionError,
            HomeAssistantError,
            "Error connecting to Mealie instance",
        ),
        (
            SERVICE_SET_MEALPLAN,
            {
                ATTR_DATE: "2023-10-21",
                ATTR_ENTRY_TYPE: "lunch",
                ATTR_RECIPE_ID: "recipe_id",
            },
            "set_mealplan",
            MealieConnectionError,
            HomeAssistantError,
            "Error connecting to Mealie instance",
        ),
        (
            SERVICE_UPDATE_MEALPLAN,
            {
                ATTR_MEALPLAN_ID: 1,
                ATTR_DATE: "2023-10-21",
                ATTR_ENTRY_TYPE: "lunch",
                ATTR_RECIPE_ID: "recipe_id",
            },
            "update_mealplan",
            MealieConnectionError,
            HomeAssistantError,
            "Error connecting to Mealie instance",
        ),
        (
            SERVICE_UPDATE_MEALPLAN,
            {
                ATTR_MEALPLAN_ID: 1,
                ATTR_DATE: "2023-10-21",
                ATTR_ENTRY_TYPE: "lunch",
                ATTR_RECIPE_ID: "recipe_id",
            },
            "update_mealplan",
            MealieNotFoundError,
            ServiceValidationError,
            "Mealplan with ID `1` not found",
        ),
        (
            SERVICE_GET_RECIPE_FAVORITES,
            {},
            "get_recipe_favorites",
            MealieConnectionError,
            HomeAssistantError,
            "Error connecting to Mealie instance",
        ),
        (
            SERVICE_ADD_RECIPE_TO_SHOPPING_LIST,
            {ATTR_SHOPPING_LIST_ID: "list-id", ATTR_RECIPE_ID: "recipe_id"},
            "add_recipe_to_shopping_list",
            MealieConnectionError,
            HomeAssistantError,
            "Error connecting to Mealie instance",
        ),
        (
            SERVICE_ADD_RECIPE_TO_SHOPPING_LIST,
            {ATTR_SHOPPING_LIST_ID: "list-id", ATTR_RECIPE_ID: "recipe_id"},
            "add_recipe_to_shopping_list",
            MealieNotFoundError,
            ServiceValidationError,
            "Shopping list or recipe not found",
        ),
        (
            SERVICE_ADD_RECIPE_TO_SHOPPING_LIST,
            {ATTR_SHOPPING_LIST_ID: "list-id", ATTR_RECIPE_ID: "recipe_id"},
            "add_recipe_to_shopping_list",
            MealieValidationError,
            ServiceValidationError,
            "Shopping list or recipe not found",
        ),
    ],
)
async def test_services_connection_error(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    service: str,
    payload: dict[str, str],
    function: str,
    exception: Exception,
    raised_exception: type[Exception],
    message: str,
) -> None:
    """Test a connection error in the services."""

    await setup_integration(hass, mock_config_entry)

    getattr(mock_mealie_client, function).side_effect = exception

    with pytest.raises(raised_exception, match=message):
        await hass.services.async_call(
            DOMAIN,
            service,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id} | payload,
            blocking=True,
            return_response=True,
        )


@pytest.mark.parametrize(
    ("service", "payload", "function", "exception", "raised_exception", "message"),
    [
        (
            SERVICE_DELETE_MEALPLAN,
            {ATTR_MEALPLAN_ID: 1},
            "delete_mealplan",
            MealieConnectionError,
            HomeAssistantError,
            "Error connecting to Mealie instance",
        ),
        (
            SERVICE_DELETE_MEALPLAN,
            {ATTR_MEALPLAN_ID: 1},
            "delete_mealplan",
            MealieNotFoundError,
            ServiceValidationError,
            "Mealplan with ID `1` not found",
        ),
        (
            SERVICE_ADD_RECIPE_FAVORITE,
            {ATTR_RECIPE_SLUG: "pizza-recipe"},
            "add_recipe_favorite",
            MealieConnectionError,
            HomeAssistantError,
            "Error connecting to Mealie instance",
        ),
        (
            SERVICE_ADD_RECIPE_FAVORITE,
            {ATTR_RECIPE_SLUG: "pizza-recipe"},
            "add_recipe_favorite",
            MealieNotFoundError,
            ServiceValidationError,
            "Recipe with ID or slug `pizza-recipe` not found",
        ),
        (
            SERVICE_REMOVE_RECIPE_FAVORITE,
            {ATTR_RECIPE_SLUG: "pizza-recipe"},
            "remove_recipe_favorite",
            MealieConnectionError,
            HomeAssistantError,
            "Error connecting to Mealie instance",
        ),
        (
            SERVICE_RATE_RECIPE,
            {ATTR_RECIPE_SLUG: "pizza-recipe", ATTR_RATING: 4},
            "rate_recipe",
            MealieConnectionError,
            HomeAssistantError,
            "Error connecting to Mealie instance",
        ),
        (
            SERVICE_RATE_RECIPE,
            {ATTR_RECIPE_SLUG: "pizza-recipe", ATTR_RATING: 4},
            "rate_recipe",
            MealieNotFoundError,
            ServiceValidationError,
            "Recipe with ID or slug `pizza-recipe` not found",
        ),
    ],
)
async def test_services_without_response_error(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    service: str,
    payload: dict[str, str],
    function: str,
    exception: Exception,
    raised_exception: type[Exception],
    message: str,
) -> None:
    """Test error handling for services that do not return a response."""

    await setup_integration(hass, mock_config_entry)

    getattr(mock_mealie_client, function).side_effect = exception

    with pytest.raises(raised_exception, match=message):
        await hass.services.async_call(
            DOMAIN,
            service,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id} | payload,
            blocking=True,
        )


@pytest.mark.parametrize(
    ("service", "payload"),
    [
        (SERVICE_GET_MEALPLAN, {}),
        (SERVICE_GET_RECIPE, {ATTR_RECIPE_ID: "recipe_id"}),
        (SERVICE_GET_RECIPES, {}),
        (
            SERVICE_GET_RECIPES,
            {ATTR_SEARCH_TERMS: "pasta", ATTR_RESULT_LIMIT: 5},
        ),
        (SERVICE_IMPORT_RECIPE, {ATTR_URL: "http://example.com"}),
        (
            SERVICE_SET_RANDOM_MEALPLAN,
            {ATTR_DATE: "2023-10-21", ATTR_ENTRY_TYPE: "lunch"},
        ),
        (
            SERVICE_SET_MEALPLAN,
            {
                ATTR_DATE: "2023-10-21",
                ATTR_ENTRY_TYPE: "lunch",
                ATTR_RECIPE_ID: "recipe_id",
            },
        ),
        (
            SERVICE_UPDATE_MEALPLAN,
            {
                ATTR_MEALPLAN_ID: 1,
                ATTR_DATE: "2023-10-21",
                ATTR_ENTRY_TYPE: "lunch",
                ATTR_RECIPE_ID: "recipe_id",
            },
        ),
        (SERVICE_GET_RECIPE_FAVORITES, {}),
        (
            SERVICE_ADD_RECIPE_TO_SHOPPING_LIST,
            {ATTR_SHOPPING_LIST_ID: "list-id", ATTR_RECIPE_ID: "recipe_id"},
        ),
    ],
)
async def test_service_entry_availability(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    service: str,
    payload: dict[str, str],
) -> None:
    """Test the services without valid entry."""
    mock_config_entry.add_to_hass(hass)
    mock_config_entry2 = MockConfigEntry(domain=DOMAIN)
    mock_config_entry2.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            service,
            {ATTR_CONFIG_ENTRY_ID: mock_config_entry2.entry_id} | payload,
            blocking=True,
            return_response=True,
        )
    assert err.value.translation_key == "service_config_entry_not_loaded"

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            service,
            {ATTR_CONFIG_ENTRY_ID: "bad-config_id"} | payload,
            blocking=True,
            return_response=True,
        )
    assert err.value.translation_key == "service_config_entry_not_found"
