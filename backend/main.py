import importlib.util
import os
import sys


API_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "functions", "user-story-api")
API_MAIN_PATH = os.path.join(API_DIR, "main.py")

if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

spec = importlib.util.spec_from_file_location("user_story_api_main", API_MAIN_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"无法加载后端入口文件: {API_MAIN_PATH}")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

app = module.app
handler = module.handler