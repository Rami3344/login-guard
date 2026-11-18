import os
from datetime import datetime

import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
hasher = PasswordHasher()
DATABASE_URL = os.environ["DATABASE_URL"]


class Credentials(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str
    ip: str  # SIMULATION ONLY: a real API uses request.client.host, never a client-sent IP
    device_id: str
    at: datetime     # SIMULATION ONLY: a real API lets the DB set the time


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/signup", status_code=201)
def signup(body: Credentials):
    password_hash = hasher.hash(body.password)
    with psycopg.connect(DATABASE_URL) as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (body.username, password_hash),
            )
        except psycopg.errors.UniqueViolation:
            raise HTTPException(status_code=409, detail="username taken")
    return {"username": body.username}


@app.post("/login")
def login(body: LoginRequest):
    with psycopg.connect(DATABASE_URL) as conn:
        # 1. find the user (None if the username does not exist)
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = %s",
            (body.username,),
        ).fetchone()

        # 2. check the password only if the user exists
        user_id = None
        success = False
        if row is not None:
            user_id = row[0]
            stored_hash = row[1]
            try:
                hasher.verify(stored_hash, body.password)
                success = True
            except VerifyMismatchError:
                success = False

        # 3. ALWAYS record the attempt (unknown user and wrong password too)
        event_id = conn.execute(
            "INSERT INTO login_events (user_id, username, ip, device_id, success, created_at)"
            " VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (user_id, body.username, body.ip, body.device_id, success, body.at),
        ).fetchone()[0]
    # 4. the `with` block has ended → the INSERT is committed. Only NOW raise the 401.
    if not success:
        raise HTTPException(status_code=401, detail={"error": "invalid credentials", "event_id": event_id})
    return {"status": "ok", "event_id": event_id}
