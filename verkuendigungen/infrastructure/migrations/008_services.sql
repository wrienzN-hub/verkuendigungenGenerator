CREATE TABLE dated_services (
 parish_name TEXT NOT NULL COLLATE NOCASE,
 service_date TEXT NOT NULL,
 services_json TEXT NOT NULL CHECK(json_valid(services_json)),
 revision INTEGER NOT NULL DEFAULT 1,
 PRIMARY KEY(parish_name,service_date)
);
INSERT OR REPLACE INTO dated_services(parish_name,service_date,services_json)
SELECT json_extract(d.payload_json,'$.parish.id'),json_extract(day.value,'$.date'),json_extract(day.value,'$.services')
FROM document_payloads d,json_each(d.payload_json,'$.days') day
ORDER BY d.updated_at,d.id;
