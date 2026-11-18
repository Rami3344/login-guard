-- ALL features, one row per login. Every feature looks ONLY at the past (created_at < e.created_at).
-- Each (SELECT count(*) ...) is the same idea as our self-join: "for this login e, count earlier rows p".
-- No trailing semicolon: the export command wraps this query in COPY (...) TO STDOUT.
SELECT
  e.id AS event_id,
  e.created_at,

  -- 1. does the username exist? (NULL user_id = unknown username; IS NULL, never = NULL)
  CASE WHEN e.user_id IS NULL THEN 0 ELSE 1 END AS username_exists,

  -- 2. new device for this user? (unknown user → never matches → 1, username_exists explains why)
  CASE WHEN (SELECT count(*) FROM login_events p
             WHERE p.user_id = e.user_id
               AND p.device_id = e.device_id
               AND p.created_at < e.created_at) = 0
       THEN 1 ELSE 0 END AS new_device,

  -- 3. new IP for this user?
  CASE WHEN (SELECT count(*) FROM login_events p
             WHERE p.user_id = e.user_id
               AND p.ip = e.ip
               AND p.created_at < e.created_at) = 0
       THEN 1 ELSE 0 END AS new_ip,

  -- 4. failed logins from the same IP in the 10 minutes before (brute force, username guessing)
  (SELECT count(*) FROM login_events p
   WHERE p.ip = e.ip
     AND p.success = false
     AND p.created_at >= e.created_at - interval '10 minutes'
     AND p.created_at <  e.created_at) AS failed_ip_10m,

  -- 5. failed logins on the same user in the 10 minutes before (any IP)
  (SELECT count(*) FROM login_events p
   WHERE p.user_id = e.user_id
     AND p.success = false
     AND p.created_at >= e.created_at - interval '10 minutes'
     AND p.created_at <  e.created_at) AS failed_user_10m,

  -- 6. hour of the day (0-23)
  EXTRACT(HOUR FROM e.created_at)::int AS hour

FROM login_events e
ORDER BY e.id
