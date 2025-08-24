"""
- HTTP call with clear fallback
Get 4 random digits (0..7) from random.org. If anything goes wrong (no internet,
timeout, bad response), we fall back to a local secure random generator so the game still works.
"""

import os
import requests
from secrets import randbelow
from typing import List

RANDOM_URL = "https://www.random.org/integers/"

def fetch_code() -> List[int]:
    params = {
        "num": 4,
        "min": 0,
        "max": 7,
        "col": 1,
        "base": 10,
        "format": "plain",
        "rnd": "new",
    }

    api_key = os.getenv("RANDOM_ORG_API_KEY")
    if api_key:
        params["apiKey"] = api_key

    # keep network quick; if it takes too long, we will just fallback
    timeout_seconds = 3.0

    try:
        response = requests.get(RANDOM_URL, params=params, timeout=timeout_seconds)
        response.raise_for_status()

        # Response is plain text like:
        # 0\n3\n1\n2\n
        lines = response.text.splitlines()

        # Parse lines
        digits = []
        i = 0
        while i < len(lines):
            text = lines[i].strip()
            if text != "":
                # may throw ValueError if not an int -> caught by except below
                value = int(text)
                digits.append(value)
            i += 1

        # Validate shape and range
        if len(digits) != 4:
            raise ValueError("random.org returned wrong amount of numbers.")

        j = 0
        while j < 4:
            if digits[j] < 0 or digits[j] > 7:
                raise ValueError("random.org number out of range.")
            j += 1

        return digits

    except Exception:
        # Fallback if error happens
        # randbelow(8) returns 0->7
        code = []
        k = 0
        while k < 4:
            code.append(randbelow(8))
            k += 1
        return code
