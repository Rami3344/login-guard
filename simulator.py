import csv
import json
import random
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API = "http://127.0.0.1:8000"
START = datetime(2026, 11, 1, tzinfo=timezone.utc)
DAYS = 7
WARMUP_DAYS = 7   # history only: normal logins BEFORE START, stored in the DB but NOT labelled
random.seed(42)


def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(API + path, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:          # 401 / 409 are normal answers here
        return e.code, json.loads(e.read())


def random_public_ip():
    # SAME pool for travelling users and attackers -> "IP looks foreign" is not a free giveaway
    return f"{random.randint(11, 220)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def random_time():
    return START + timedelta(seconds=random.randint(0, DAYS * 24 * 3600))


# ---------- 1. create users ----------
users = []
for i in range(1, 51):
    user = {
        "username": f"user{i:02d}",
        "password": f"pw-{random.randint(100000, 999999)}",
        "home_ip": f"10.0.{i}.{random.randint(1, 254)}",
        "home_device": f"user{i:02d}-laptop",
    }
    status, _ = post("/signup", {"username": user["username"], "password": user["password"]})
    users.append(user)
print("users ready:", len(users))

# ---------- 2. plan all attempts (not sent yet) ----------
attempts = []   # each: username, password, ip, device_id, at, is_attack, kind


def add(user, password, ip, device, at, is_attack, kind):
    attempts.append({"username": user["username"], "password": password, "ip": ip,
                     "device_id": device, "at": at, "is_attack": is_attack, "kind": kind})


# normal users: 0-3 logins per day
# days -7..-1 = warm-up week (history only), days 0..6 = the real week
for user in users:
    for day in range(-WARMUP_DAYS, DAYS):
        if day < 0:
            kind_ok = "warmup"
            kind_typo = "warmup"
        else:
            kind_ok = "normal"
            kind_typo = "normal_typo"
        for n in range(random.randint(0, 3)):
            at = START + timedelta(days=day, seconds=random.randint(0, 24 * 3600 - 1))
            ip = user["home_ip"]
            device = user["home_device"]
            if random.random() < 0.10:                       # 10%: new phone / travel
                ip = random_public_ip()
                device = f"{user['username']}-new-{random.randint(1, 999)}"
            if random.random() < 0.05:                       # 5%: typo, then the right password
                add(user, user["password"] + "x", ip, device, at, 0, kind_typo)
                at = at + timedelta(seconds=20)
            if random.random() < 0.02:                       # 2%: typo in the USERNAME (unknown user)
                typo_user = {"username": user["username"] + "_"}
                add(typo_user, user["password"], ip, device, at, 0, kind_typo)
                at = at + timedelta(seconds=20)
            add(user, user["password"], ip, device, at, 0, kind_ok)

# brute force: 6 bots, 15 wrong passwords each, 2 s apart, one IP + one device
for b in range(6):
    victim = random.choice(users)
    ip = random_public_ip()
    at = random_time()
    for k in range(15):
        add(victim, f"guess{k}", ip, f"bot-{b}", at + timedelta(seconds=2 * k), 1, "brute_force")

# username guessing: 4 bots try common usernames that do NOT exist, 3 s apart, one IP + one device
COMMON_NAMES = ["admin", "test", "root", "support", "guest", "info", "demo", "oracle", "webmaster", "user"]
for b in range(4):
    ip = random_public_ip()
    at = random_time()
    for k in range(len(COMMON_NAMES)):
        fake_user = {"username": COMMON_NAMES[k]}
        add(fake_user, "123456", ip, f"guesser-{b}", at + timedelta(seconds=3 * k), 1, "unknown_user")

# stolen password: correct password, new device + IP
for s in range(20):
    victim = random.choice(users)
    add(victim, victim["password"], random_public_ip(), f"device-{random.randint(1000, 9999)}",
        random_time(), 1, "stolen_password")

# ---------- 3. send in time order, write labels SEPARATELY ----------
attempts.sort(key=lambda a: a["at"])
with open("labels.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["event_id", "is_attack", "kind"])
    for a in attempts:
        status, reply = post("/login", {"username": a["username"], "password": a["password"],
                                        "ip": a["ip"], "device_id": a["device_id"],
                                        "at": a["at"].isoformat()})
        if status == 200:
            event_id = reply["event_id"]
        else:
            event_id = reply["detail"]["event_id"]
        if a["kind"] == "warmup":      # sent to the API (becomes history) but never labelled
            continue
        writer.writerow([event_id, a["is_attack"], a["kind"]])

print("attempts sent:", len(attempts))
