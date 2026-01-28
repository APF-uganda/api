-- Insert the authentication migration as if it was applied before admin
INSERT INTO django_migrations (app, name, applied)
VALUES ('authentication', '0001_initial', NOW())
ON CONFLICT DO NOTHING;
