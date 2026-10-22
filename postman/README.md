# Crop Farmer lookup fault simulation

Run `postman simulation run postman/simulations/farmer-enrichment.sim.yaml --port 49180`,
then `CROP_FARMER_SIMULATION_URL=http://127.0.0.1:49180/farmer python -m pytest test/test_farmer_enrichment_http.py`.
These tests execute the real helper and HTTP client, with generated test signing
keys. Responses model the documented DCI envelope, zero/ambiguous matches, denied
scope/identity, malformed bodies, proxy errors, timeout and connection failure.
They do not establish Partner Management or Consent authorization; live signed
checks cover those. Owner workspace discovery was unavailable without Postman
login; no cloud mock or workspace was created.
