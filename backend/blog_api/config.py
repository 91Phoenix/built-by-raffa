import os

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def content_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return env("CONTENT_DIR", os.path.join(here, "content"))


def deepseek_api_key() -> str:
    return env("DEEPSEEK_API_KEY")


def chat_model() -> str:
    return env("CHAT_MODEL", "deepseek-v4-flash")


def allowed_origin() -> str:
    return env("ALLOWED_ORIGIN", "*")
