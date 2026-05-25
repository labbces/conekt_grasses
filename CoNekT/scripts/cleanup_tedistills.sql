-- Clean up only the TEdistill-related tables, leaving species/sequences/te_classes intact.
-- Safe to run multiple times. Run with:
--   mysql -u <DB_ADMIN> -p <DB_NAME> < cleanup_tedistills.sql

-- Use TRUNCATE for speed (resets auto-increment too), with FK checks off
-- so order doesn't matter. We re-enable them right after.
SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE sequence_tedistill;
TRUNCATE TABLE tedistill_te_class;
TRUNCATE TABLE tedistills;
TRUNCATE TABLE tedistill_methods;

SET FOREIGN_KEY_CHECKS = 1;

-- Quick sanity check
SELECT 'tedistill_methods' AS tbl, COUNT(*) AS rows_left FROM tedistill_methods
UNION ALL SELECT 'tedistills',         COUNT(*) FROM tedistills
UNION ALL SELECT 'tedistill_te_class', COUNT(*) FROM tedistill_te_class
UNION ALL SELECT 'sequence_tedistill', COUNT(*) FROM sequence_tedistill;