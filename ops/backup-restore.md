# Backup and restore

Backup: pg_dump | gzip. Restore: createdb new_db; gunzip -c file | psql new_db. Test a restore once before the demo (NFR-5).
