# Approved Farmer change notifications

New Dev uses the documented outgestion and ingestion pipelines:
Farmer approval → Celery transform → WebSub/Kafka → signed connector callback →
signed Partner ingestion → current consented Farmer lookup → normal Farmer
reference change request. No source name, phone or date of birth is trusted from
an event. A callback carries Farmer ID and FAN, so it is still sensitive data.

`config.yaml`, `notification.schema.json` and `update.json.j2` define the dedicated
model and UPDATE section. The register classifier resolves the existing local
Farmer by its functional ID. There is deliberately no ADD intake-form match:
an unknown Farmer is quarantined by normal classification failure, never created
by a notification. Existing native approval rules remain authoritative.

Apply the connector Secret overlay to the existing `cropsown-connector` release
with its current chart, values, images and owner retained. The same existing
approved Ed25519 identity signs the native ingest payload at
`$.body.message.payload`; signature validation stays enabled on Partner API.
The WebSub secret is dedicated, random and private. Configure the connector with
`webhook_verifier=hmac_sha256`, `websub_content_envelope=true`,
`sign_registry_payload=true`, this model mnemonic and the validation schema.
Keep it paused until the new verifier and notification enricher are deployed.

The two metadata classification passes, MinIO template/document catalog and
`raw_payload_enricher_class=G2PFarmerReferenceNotificationEnricher` are native
OpenG2P configuration. A failed lookup raises a retryable transformation error.
It cannot silently mark a notification processed. An older event whose pair no
longer matches is rejected; unchanged older pairs fetch current source details.
Repeated event IDs are serialized and reused by the connector. Retain DLQ and
pipeline failure monitoring; never reset all historical failures to retry one
event. Pending change requests still require their configured approval.

Source activation and publisher settings are owned by Farmer Registry. No
historical publication is requested. Test through a newly marked native approved
Farmer change, then trace its outgoing row, connector event, incoming row and
change request before enabling ongoing delivery.

References: [outgestion](https://docs.openg2p.org/products/registry/registry/design/outgestion-pipeline),
[ingestion](https://docs.openg2p.org/products/registry/registry/design/ingestion-pipeline).
