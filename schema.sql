CREATE TABLE IF NOT EXISTS users (
  id            serial PRIMARY KEY,
  username      text UNIQUE NOT NULL,
  password_hash text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS login_events (
  id          serial PRIMARY KEY,
  user_id     int REFERENCES users(id),     -- NULL allowed: unknown username
  username    text NOT NULL,                -- what was typed
  ip          text NOT NULL,
  device_id   text,
  success     boolean NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);
