-- Feature: failed logins from the same IP in the 10 minutes BEFORE each event.
-- e = the event we are deciding about (X), p = earlier events (A, B, C...).
SELECT
  e.id,
  e.ip,
  e.created_at,
  count(p.id) AS failed_ip_10m
FROM login_events e
LEFT JOIN login_events p
  ON  p.ip = e.ip
  AND p.success = false
  AND p.created_at >= e.created_at - interval '10 minutes'  -- not too old (drops A)
  AND p.created_at <  e.created_at                          -- strictly before (drops X itself and D)
GROUP BY e.id, e.ip, e.created_at
ORDER BY failed_ip_10m DESC
LIMIT 10;
