import os
from enum import Enum
from src.utils import fetch_json_data

# Settings
ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(ROOT_PATH, r"resources\settings.json")
SETTINGS_DICT = fetch_json_data(SETTINGS_PATH)

# Styles
STANDARD_STYLE_DICT = {}
ERROR_STYLE_DICT = {"color": "red"}

# App
APP_NAME = "Hotel Pricing Manager"


class Version(Enum):
    FREE = 1
    PREMIUM = 2


# Web Browser
EDGE_VERSION = None  # 105.0.1343.50
