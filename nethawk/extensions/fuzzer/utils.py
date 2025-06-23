import string
import hashlib
import random

def colored_status(code: int):
    if 200 <= code < 300:
        color = "bold green"
    elif 300 <= code < 400:
        color = "bold blue1"
    elif 400 <= code < 500:
        color = "bold magenta"
    elif 500 <= code < 600:
        color = "bold red"
    else:
        color = "bold yellow"
    return color

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_content_hash(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()

def is_probably_directory(path, code, location, text):
    if path.endswith("/"):
        return True

    if code in (301, 302) and location.endswith("/"):
        return True

    if "Index of" in text or "<title>Index of" in text:
        return True

    return False  # Unknown