import os
import sys
from platformdirs import user_data_dir

def get_app_data_dir() -> str:
    app_name = "XadbyPad"
    return user_data_dir(app_name, appauthor=False)

def get_resource_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)