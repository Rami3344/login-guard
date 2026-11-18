-- Feature: has this user used this device BEFORE this login? (seen_before = 0 -> new device)
-- e = the login we are deciding about (X), p = this user's earlier logins.
SELECT
  e.id,
  e.username,
  e.device_id,
  count(p.id) AS seen_before
FROM login_events e
LEFT JOIN login_events p
  ON  p.user_id    = e.user_id      -- same user
  AND p.device_id  = e.device_id    -- same device
  AND p.created_at < e.created_at   -- only the past (not itself, not the future)
GROUP BY e.id, e.username, e.device_id
ORDER BY e.id
LIMIT 20;
