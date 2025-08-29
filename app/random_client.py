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

def fetch_code(length: int = 4) -> List[int]:
    # Parameters to send to random.org
    params = {
        "num": length,     # how many numbers we want -> Extension #1
        "min": 0,          # smallest allowed number
        "max": 7,          # largest allowed number
        "col": 1,          # one number per line
        "base": 10,        # normal decimal numbers
        "format": "plain", # plain text response
        "rnd": "new",      # always generate new numbers
    }

    # keep network quick; if it takes too long, we will just fallback
    timeout_seconds = 3.0

    try:
        # Make the HTTP request to random.org
        response = requests.get(RANDOM_URL, params=params, timeout=timeout_seconds)

        # If the response was not 200 OK, this will raise an error
        response.raise_for_status()

        # The body looks like:
        #   0\n3\n1\n2\n
        lines = response.text.splitlines()

        # Convert each line into an integer
        digits = []
        i = 0
        while i < len(lines):
            text = lines[i].strip()
            if text != "":
                # Turn the text into a number
                value = int(text)
                digits.append(value)
            i += 1

        # Check that we got exactly the requested number of digits
        if len(digits) != length:
            raise ValueError(f"random.org returned {len(digits)} values, expected {length}.")

        # Check each number is between 0 and 7
        j = 0
        while j < 4:
            if digits[j] < 0 or digits[j] > 7:
                raise ValueError("random.org number out of range 0..7.")
            j += 1

        # Everything looks good
        return digits

    except Exception:
        # Fallback: if the request fails, use Python's secure random
        # randbelow(8) gives us a number between 0 and 7
        fallback_digits = []
        k = 0
        while k < length:
            fallback_digits.append(randbelow(8))
            k += 1
        return fallback_digits
