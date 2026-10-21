# New-dev registry routing

The existing `cropsown-registry` release in namespace `crop` uses:

| Component | Host |
| --- | --- |
| Staff UI | `crop-registry.development.oanstaging.com` |
| Staff API | `staff-crop.development.oanstaging.com` |
| Partner API | `partner-crop.development.oanstaging.com` |

All three VirtualServices use `istio-system/development`. The deployment script
`ci/deploy-crop-dev.sh` writes these public settings after the saved release
values, so an older `internal` Gateway or old hostname cannot win that merge.
Its defaults also select canonical shared Keycloak, IAM and MinIO URLs and the
cookie domain `.development.oanstaging.com`. Id-generator and dashboard private
hosts retain their namespace-specific routing; the unauthenticated dashboard API
stays on `internal`.

Before `helm upgrade`, the script converts the exact render to JSON with
`kubectl create --dry-run=client --validate=false` and runs the stdlib-only
`ci/check-new-dev-routes.py`. This rejects missing/wrong registry routes, old
public URLs (including encoded login configuration), old cookie scope, public
routes on the wrong Gateway and private routes on the shared public Gateway.
Only resource counts/status are logged; manifests and Secret values are not.
Python 3 and kubectl must be available on the deployment node.

Saved private environment overrides can still contain old literal URLs. The
guard intentionally stops the upgrade in that case; reconcile those individual
entries using the reviewed OAN Helm URL-migration guide, without replacing
custom lists, Secret references or live image settings. Legacy browser redirects
and API proxy aliases remain environment-owned compatibility resources: this
chart must not install another release over them or remove them.

This fixes future new-dev deployment inputs; merging a PR is not a deployment.
The existing deploy behavior for images, initialization/seed hooks, credentials
and resource ownership remains in place. A normal app rollout may run migrations
or seed hooks. For a separate URL-only repair, back up the current release and
suppress both hooks and ordinary initialization Jobs; TTL-cleaned Jobs can be
recreated even when their manifests have not changed. Helm rollback cannot undo
database migrations.

Run the guard's adversarial tests without cluster access:

```sh
python3 test/test_new_dev_routes.py
```

Validate the actual render with the same deployment guard before a rollout, then
run `scripts/check-registry-public-urls.py` from the OAN Helm repository. That
read-only live Postman regression verifies canonical UI/API routes and temporary
old URL compatibility. Rendering alone does not prove live public reachability.
