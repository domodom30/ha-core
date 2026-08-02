"""Constants for the Mealie integration."""

import logging

from aiomealie import MealplanEntryType
from awesomeversion import AwesomeVersion

DOMAIN = "mealie"

LOGGER = logging.getLogger(__package__)

ATTR_START_DATE = "start_date"
ATTR_END_DATE = "end_date"
ATTR_RECIPE_ID = "recipe_id"
ATTR_URL = "url"
ATTR_INCLUDE_TAGS = "include_tags"
ATTR_ENTRY_TYPE = "entry_type"
ATTR_NOTE_TITLE = "note_title"
ATTR_NOTE_TEXT = "note_text"
ATTR_SEARCH_TERMS = "search_terms"
ATTR_RESULT_LIMIT = "result_limit"
ATTR_MEALPLAN_ID = "mealplan_id"
ATTR_RECIPE_SLUG = "recipe_slug"
ATTR_RATING = "rating"

MIN_REQUIRED_MEALIE_VERSION = AwesomeVersion("v2.0.0")

# Starting with Mealie 3.7.0, all mealplan entry types are supported. Prior to that,
# only breakfast, lunch, dinner and side were available.
MEALIE_MULTIPLE_ENTRY_TYPES_VERSION = AwesomeVersion("v3.7.0")
LEGACY_MEALPLAN_ENTRY_TYPES = (
    MealplanEntryType.BREAKFAST,
    MealplanEntryType.LUNCH,
    MealplanEntryType.DINNER,
    MealplanEntryType.SIDE,
)
