# Farmer enrichment in New Dev

Crop intake uses a dedicated Partner Management identity, `Crop_sown_partner_internal`, with DCI key reference `PARTNER_CROP_SOWN_PARTNER_INTERNAL`. Its private Ed25519 key is held in Secret `crop/crop-farmer-lookup-signing-ed25519`, key `private-key.pem`. Public keys are approved under both references; rotate or disable both together.

`helm/environments/dev/farmer-enrichment.yaml` owns the non-secret settings and Secret reference. The dev deployment layers it over saved release values, then applies CI image overrides. It is included in Jenkins' deployment stash. Do not put lookup identities, development URLs or private keys into shared chart defaults.

On Submit, the existing two-approval flow looks up the Farmer ID and FAN together through Farmer Registry's signed DCI API. FAN display spaces are removed for lookup and consent. The consent binding uses audience `crop-registry`, controller `farmer-registry`, method `internal`, purpose `registry_intake`, scope `farmer_personal_details` and subject type `fayda_fan_id`.

A successful lookup raises a separate Farmer register change-request alongside the Crop intake approval item. Normal approval makes the local Farmer reference active. An existing active Farmer reference or pending Farmer request is reused without a duplicate. A lookup failure is logged and leaves the original Crop intake workflow running. This does not add autofill while typing FAN or replay historical submissions.

Both `CROPSOWN_FARMER_ENRICHMENT_ENABLED` and `CROPSOWN_TWO_CR_ENABLED` are required. Startup installs the existing helper once, after intake validation hooks. Enabled hook-installation failures fail startup. Jenkins checks configuration and signing Secret metadata before deployment, and checks both workloads and their hook-installation logs after rollout. Missing configuration or hooks fails the deployment stage.

Both identifiers must exist on the same active source Farmer. An empty source
`foundational_id` produces no match even when the Farmer ID is valid. Complete
and approve the source Farmer identity through its normal workflow before
retrying the reference operation; never copy an unverified intake FAN into the
source registry or weaken the lookup to an ID-only search. Draft intakes do not
trigger enrichment. Existing finalized submissions must be inspected before any
targeted retry; do not replay approval or ingestion to retry a lookup.

Lookup diagnostics use the application logger and omit Farmer IDs, FANs, tokens
and payloads. Even reuse of an active reference requires a successful identity
lookup. Missing/invalid identifiers, malformed/multiple results or a returned
UIN that differs from the requested FAN do not create a reference. Outages leave
the normal Crop approval workflow running; those submissions require a reviewed
retry after recovery. See `postman/README.md` for executable HTTP fault tests.
