DROP VIEW available_celebrations;
ALTER TABLE saints DROP COLUMN review_status;
ALTER TABLE saints DROP COLUMN review_notes;
ALTER TABLE import_runs DROP COLUMN status;
ALTER TABLE import_runs ADD COLUMN source_pdf BLOB;
UPDATE import_runs SET report_json = json_remove(report_json, '$.review_status');
UPDATE import_runs SET report_json = json_set(report_json, '$.warnings', json(
    (SELECT json_group_array(value) FROM json_each(import_runs.report_json, '$.warnings')
     WHERE value NOT LIKE '%fachliche Freigabe%')
));
CREATE UNIQUE INDEX import_runs_year_idx ON import_runs(diocese, liturgical_year);
CREATE VIEW available_celebrations AS
SELECT * FROM saints WHERE disabled = 0
AND observance_status IN ('observed','optional','commemoration_only');
