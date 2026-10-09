# Crop Sown Registry — ODK forms

Development agents record a farm plot's season in four stage forms in ODK
Collect (or the browser). ODK Central stores the submissions; the crop sown
connector polls each form and posts every submission to the registry, which
turns it into an intake for that stage.

```
ODK Collect / web form → ODK Central → cropsown connector (4 pipelines, photos inline)
  → partner API → celery: classify by form → csr_odk_transform.j2 (MinIO) → stage intake
```

## At a glance

| Form file | Form id | Stage | Published on dev | Location lists |
| --- | --- | --- | --- | --- |
| `crop_sown_registry_plan.xlsx` | `crop_sown_registry_plan` | 1. Planning | `v0` | yes |
| `crop_sown_registry_prep.xlsx` | `crop_sown_registry_prep` | 2. Cultivation & land preparation | `v0` | yes |
| `crop_sown_registry_sown.xlsx` | `crop_sown_registry_sown` | 3. Sowing (and infestation) | `v0` | no |
| `crop_sown_registry_harvest.xlsx` | `crop_sown_registry_harvest` | 4. Harvesting | `v0` | no |

| | |
| --- | --- |
| ODK Central (dev) | `https://odk-central-development.oanstaging.com`, project **15** |
| Media | `media/`: `region.csv`, `zone.csv`, `woreda.csv`, `kebele1.csv` (location), `crop_name.csv` (all four), `crop_variety.csv`, `seed_variety.csv` (planning, cultivation). Same name, same file, in every form that uses it |
| Location lists | generated from the registry's hierarchy: `build_location_media.py` |
| Transform | `cropsown-extension/.../templates/csr_odk_transform.j2`, read from the MinIO `templates` bucket |
| Connector | `ci/connector/` (release `cropsown-connector`, namespace `crop`): one pipeline per form, data model `CSR_DATA_MODEL`, partner `crop-partner` |
| Registry routing | `zz_cropsown_odk_ingestion.sql`: the form id at the front of the message id picks the stage's intake form |

The XLSX files are the files as uploaded to Central, exported from there
(`GET /v1/projects/15/forms/<form id>.xlsx`). Central set the published
version (`v0`) at publish time, so each settings sheet's `version` cell (`1.0`
to `1.2`) is not what Collect shows.

## What the forms ask

| Form | Groups |
| --- | --- |
| Planning | `farmer_identity` (farmer id, Fayda FAN, crop year, season), `address` (region → zone → woreda → kebele, GPS), `planning` repeat per plot (land, plot location, season dates, crop, variety, area, seed, fertiliser, water, `cluster_information`) |
| Cultivation & land prep | `farmer_identity`, `cult_land_prep` (cluster location, land preparation, inputs) |
| Sowing | `farmer_plot` (Fayda, crop year, season), `sowing_details` repeat (land, cluster status, independent / clustered details, surveyor), `infestation_incidents` repeat (pest, weed, disease, nutrient deficiency, climate shock) |
| Harvesting | `farmer_plot`, `independant_harvest` / `harvesting` (harvest repeat: date, area, yield, storage, losses, sales) |

## Location lists

Planning and cultivation pick region → zone → woreda → kebele from
`media/region.csv`, `zone.csv`, `woreda.csv` and `kebele1.csv` (each filtered by
its parent). They are generated from the registry's own geo attribute values
(`meta_data/lookup-data/g2p_attribute_values.sql`: `REGION_ET04`,
`ZONE_ET0408`, `WOREDA_ET040801`, `KEBELE_ET040801101001`), which are the
shared Ethiopia hierarchy every registry's Master Data uses (14 regions, 125
zones, 1,379 woredas, 19,535 kebeles). So the forms offer exactly the places the
registry knows, under the registry's names, and every pick becomes an id it
resolves:

| Level | CSV value | `csr_odk_transform.j2` sends |
| --- | --- | --- |
| region | `region_et04` | `REGION_ET04` (`region_map`) |
| zone | `ET0408` | `ZONE_ET0408` |
| woreda | `ET040801` | `WOREDA_ET040801` |
| kebele | `ET040801101001` | `KEBELE_ET040801101001` |

The ingest worker fills region / zone / woreda / kebele names from Master Data.

The lists were rebuilt on 2026-10-09. Before that most picks did not resolve:
8 of the 14 region keys were not in the transform's `region_map` (`addis`,
`oromiya`, `hareri`, `ethiopia_somali`, …), 36 zones and 414 woredas lacked
the `ET` prefix (giving `ZONE_1402`, `WOREDA_140101`), 260 kebeles were not in
the hierarchy (35 under woredas it lacks, 225 `…_pula_new` rows), and names
differed from the registry's (`Wereda 01` for Akaki Kality Sub City).

**When the hierarchy changes:**

```sh
python docs/odk/build_location_media.py          # rewrites media/{region,zone,woreda,kebele1}.csv
python docs/odk/build_location_media.py --check  # what CI runs (test/test_odk_location_media.py)
```

then publish the new CSVs on the planning and cultivation forms (below).

## Photos

The forms ask no photo today. The pipeline is ready for them: the connector
sends ODK attachments inline as `{"__type": "File", ...}` (`embed_attachments`,
on by default; over 10 MiB is skipped), and the transform maps these question
names (a file that arrived as a name only is left out):

| Question name | Where | Stored in |
| --- | --- | --- |
| `record_photo` | `farmer_identity` or `farmer_plot` | CropSown `record_image_document_id` |
| `geo_tagged_photo` | a `sowing_details` entry | Sowing `geo_tagged_photo_document_id` |
| `infestation_photo` | an `infestation_incidents` entry | Infestation `geo_tagged_photo_document_id` |

On save, the CropSown, Sowing and Infestation services upload the file to the
documents bucket and store its document id
(`register_domain/services/embedded_files.py`). Adding an `image` question
under one of these names is the only step left; `test/test_odk_forms.py` fails
on a photo question the transform does not map.

## Fayda ID

The register wants `1234 5678 9000 3456`. Agents type it without spaces, with
dashes or stray spaces; the transform regroups any 16 digits. Anything else is
sent as typed and rejected by the validator, with its message in the log.

## Publishing

The connector polls each form by id, so **keep the form ids**.

**New CSVs only** (location lists, crop lists): in ODK Central, project 15 →
the form → **Create a new draft** → **Media Files** → upload the changed CSVs →
test the draft → **Publish**, giving a new version (`v1`, …). With the API:

```sh
C=https://odk-central-development.oanstaging.com; P=15
T=$(curl -s $C/v1/sessions -H 'Content-Type: application/json' -d '{"email":"…","password":"…"}' | jq -r .token)
for F in crop_sown_registry_plan crop_sown_registry_prep; do
  curl -s -X POST "$C/v1/projects/$P/forms/$F/draft" -H "Authorization: Bearer $T"     # copies the published version
  for m in region.csv zone.csv woreda.csv kebele1.csv; do
    curl -s -X POST "$C/v1/projects/$P/forms/$F/draft/attachments/$m" -H "Authorization: Bearer $T" \
      -H 'Content-Type: text/csv' --data-binary @docs/odk/media/$m; done
  curl -s -X POST "$C/v1/projects/$P/forms/$F/draft/publish?version=<new version>" -H "Authorization: Bearer $T"
done
```

**A changed form:** bump the settings `version` cell past what Central has
seen, upload the XLSX as a new draft (`POST …/forms/<id>/draft` with the XLSX
body and `X-XlsForm-FormId-Fallback: <id>`), attach its CSVs, test, publish,
and commit the XLSX here.

**A changed transform:** it is read from MinIO, and `ci/deploy-crop-dev.sh`
uploads templates only with `SEED_MINIO_ASSETS=true`. Deploy once with that
set, or `mc cp cropsown-extension/src/openg2p_registry_cropsown_extension/templates/csr_odk_transform.j2 <alias>/templates/`.

## Connector

`ci/connector/README.md`. Four pipelines (Crop Sown 1–4), each: ODK Central base
URL, project 15, its form id, `CSR_DATA_MODEL`, `partner-id: crop-partner`,
`resolve_nav_links` and `embed_attachments` on. `default_pipelines.py` seeds
them from `CONNECTOR_ODK_*` when set. Each submission is sent **once**: an edit
in Central is not re-sent; make a new submission instead.

## Following a submission

The connector and the registry write JSON lines to `odk-ingest.jsonl` and stdout:

| Where | Events |
| --- | --- |
| connector | `poll_*`, `record_received`, `attachment_*` / `attachments_summary`, `sent` / `send_failed`, `duplicate_ignored` |
| partner API | `ingest_request_failed` |
| transformation worker | `submission_received` (files inline / name only), `file_missing`, `transformed`, `transform_failed` |
| ingest worker | `file_stored` / `file_rejected`, `ingest_succeeded`, `ingest_retry_scheduled`, `ingest_failed` (error, attempt, next step) |

```sh
kubectl -n crop logs deploy/cropsown-connector-worker | grep 'crop_sown_registry_sown:uuid:<id>'
kubectl -n crop logs deploy/cropsown-registry-celery-worker | grep '"ingest_id": "<ingest id>"'
```

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| Web form: "This form does not exist … (Attempted to access form with ID: )" | Enketo's link was made under an older Central hostname; the Central admin regenerates the form's Enketo id. Collect is unaffected. |
| `ingest_failed`: "Fayda ID must be 16 digits …" | not 16 digits as typed; fix in ODK and resubmit |
| Location blank or a raw code on the intake | a pick that does not resolve: the forms' CSVs are older than these (publish them) or the transform in MinIO is stale |
| Nothing arrives | connector `poll_failed` / `send_failed`; an edited submission is not re-sent |
