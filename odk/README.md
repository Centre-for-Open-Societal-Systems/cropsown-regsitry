# Crop sown ODK forms

One form per stage, each with its own connector pipeline (all data model
`CSR_DATA_MODEL`, partner `crop-partner`). The form id at the front of the
connector's message id picks the stage's intake form
(`zz_cropsown_odk_ingestion.sql`).

| Form | Stage | Published as |
| --- | --- | --- |
| `crop_sown_registry_plan.xlsx` | 1. Planning | `v0` |
| `crop_sown_registry_prep.xlsx` | 2. Cultivation & land preparation | `v0` |
| `crop_sown_registry_sown.xlsx` | 3. Sowing (and infestation) | `v0` |
| `crop_sown_registry_harvest.xlsx` | 4. Harvesting | `v0` |

All four are on ODK Central dev, `https://odk-central-development.oanstaging.com`,
project 15. `media/` holds the lookups they read: `crop_name.csv` (all four),
plus `region.csv`, `zone.csv`, `woreda.csv`, `kebele1.csv`, `crop_variety.csv`
and `seed_variety.csv` (planning and cultivation). A file with the same name is
the same file in every form that uses it.

The XLSX files are as uploaded to Central, exported from there
(`GET /v1/projects/15/forms/<form id>.xlsx`). Central set the published version
(`v0`) at publish time, so the `version` cell in each settings sheet (`1.0` to
`1.2`) is not what Collect shows. To publish a change, bump that cell to
something Central has not seen, upload it as a new draft of the same form id
(the connector polls it by name), attach its CSVs, test the draft, publish, and
commit the new XLSX here.

`test/test_odk_forms.py` checks that the four form ids match the connector
pipelines, that every CSV a form reads is in `media/`, and that every photo
question is one the transform maps.

## Photos

The forms ask no photo today. The pipeline is ready for them:

1. The connector downloads a submission's attachments from Central and sends
   each inline as `{"__type": "File", "name", "type", "data": <base64>}`
   (`embed_attachments`, on by default; files over 10 MiB are skipped).
2. `csr_odk_transform.j2` maps these inline photos (a bare file name means the
   file did not come along, and it is left out):

   | Question name | Where in the form | Stored in |
   | --- | --- | --- |
   | `record_photo` | `farmer_identity` or `farmer_plot` | CropSown `record_image_document_id` |
   | `geo_tagged_photo` | a `sowing_details` entry | Sowing `geo_tagged_photo_document_id` |
   | `infestation_photo` | an `infestation_incidents` entry | Infestation `geo_tagged_photo_document_id` |

3. On save, the CropSown, Sowing and Infestation services upload it to the
   documents bucket and store the document id
   (`register_domain/services/embedded_files.py`).

So adding an `image` question under one of those names is the only step left.
A photo question under any other name fails `test_odk_forms.py` until the
transform maps it.

The transform is read from the MinIO `templates` bucket, not from the image.
`ci/deploy-crop-dev.sh` uploads templates only with `SEED_MINIO_ASSETS=true`, so
after changing `csr_odk_transform.j2`, deploy once with that set, or upload it:
`mc cp cropsown-extension/src/openg2p_registry_cropsown_extension/templates/csr_odk_transform.j2 <alias>/templates/`.

## Fayda ID

The register wants the Fayda ID as four groups of four digits
(`1234 5678 9000 3456`). Agents type it without spaces, with dashes or with
stray spaces; the transform regroups any 16 digits. Anything else is sent
unchanged and rejected by the validator, with its message in the ingestion log.

## Following a submission

The connector and the registry both write JSON-lines ingestion logs: the
connector to `/app/logs/odk-ingest.jsonl`, the registry's partner API and celery
workers to `logs/odk-ingest.jsonl` (`REGISTRY_EXTENSIONS_ODK_INGEST_LOG_FILE`).
All of them also go to stdout.

| Where | Events |
| --- | --- |
| connector | `poll_started` / `poll_finished` / `poll_failed`, `record_received`, `attachment_embedded` / `attachment_not_uploaded` / `attachment_too_large` / `attachment_download_failed`, `sent`, `send_failed`, `duplicate_ignored` |
| partner API | `ingest_request_failed` |
| transformation worker | `submission_received` (files inline / name only), `file_missing`, `transformed`, `transform_failed` |
| ingest worker | `file_stored` / `file_rejected`, `ingest_succeeded`, `ingest_retry_scheduled`, `ingest_failed` (the error, the attempt, and what to do next) |

```sh
kubectl -n crop logs deploy/cropsown-connector-worker | grep '"source_event_id": "crop_sown_registry_sown:uuid:<id>"'
kubectl -n crop logs deploy/cropsown-registry-celery-worker | grep '"ingest_id": "<ingest id>"'
```

The registry events carry `ingest_id` (`incoming_classified_data.ingest_id`);
`submission_received` also has the ODK `instance_id`, which links the two.
