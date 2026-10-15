ALTER TABLE events ADD COLUMN name TEXT NOT NULL DEFAULT '';
ALTER TABLE events ADD COLUMN parishes_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(parishes_json));
ALTER TABLE events ADD COLUMN weeks_json TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(weeks_json));
UPDATE events SET name=coalesce(nullif(json_extract(title_json,'$.de'),''),nullif(json_extract(title_json,'$.sl'),''),'Termin ' || id), parishes_json=json_array(parish_name);
