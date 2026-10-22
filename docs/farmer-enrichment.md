# Farmer enrichment in New Dev

Crop intake uses a dedicated Partner Management identity, `Crop_sown_partner_internal`, with DCI key reference `PARTNER_CROP_SOWN_PARTNER_INTERNAL`. Its private Ed25519 key is held in Secret `crop/crop-farmer-lookup-signing-ed25519`, key `private-key.pem`. Public keys are approved under both references; rotate or disable both together.

`helm/environments/dev/farmer-enrichment.yaml` owns the non-secret settings and Secret reference. The dev deployment layers it over saved release values, then applies CI image overrides. It is included in Jenkins' deployment stash. Do not put lookup identities, development URLs or private keys into shared chart defaults.

On Submit, the existing two-approval flow looks up the Farmer ID and FAN together through Farmer Registry's signed DCI API. FAN display spaces are removed for lookup and consent. The consent binding uses audience `crop-registry`, controller `farmer-registry`, method `internal`, purpose `registry_intake`, scope `farmer_personal_details` and subject type `fayda_fan_id`.

A successful lookup raises a separate Farmer register change-request alongside the Crop intake approval item. Normal approval makes the local Farmer reference active. An existing active Farmer reference or pending Farmer request is reused without a duplicate. A lookup failure is logged and leaves the original Crop intake workflow running. This does not add autofill while typing FAN or replay historical submissions.

Both `CROPSOWN_FARMER_ENRICHMENT_ENABLED` and `CROPSOWN_TWO_CR_ENABLED` are required. Startup installs the existing helper once, after intake validation hooks. Enabled hook-installation failures fail startup. Jenkins checks configuration and signing Secret metadata before deployment, and checks both workloads and their hook-installation logs after rollout. Missing configuration or hooks fails the deployment stage.
