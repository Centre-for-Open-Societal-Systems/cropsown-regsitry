"""The db-seed sample loader: the pack's sample farmers seeded as approved farmer references, their crop
records entered as stage intakes and approved at both stages by the sample approvers."""

import ast
import importlib.util
import itertools
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "docker/db-seed"


@pytest.fixture(scope="module")
def loader():
    extras = types.ModuleType("psycopg2.extras")
    extras.Json = lambda value: ("json", value)
    stubs = {"psycopg2": types.ModuleType("psycopg2"), "psycopg2.extras": extras}
    saved = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location("crop_sample_loader", SEED / "load_sample_data.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


def test_loader_signs_in_like_the_portal_and_writes_only_the_farmer_reference():
    source = (SEED / "load_sample_data.py").read_text(encoding="utf-8")
    code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
    for forbidden in ("grant_type", "KEYCLOAK_ADMIN", "admin-cli", "/admin/realms", "directAccessGrants",
                      "UPDATE ", "DELETE FROM", "/approve_change_request", "g2p_register_crop_sowns\" (",
                      "INSERT INTO g2p_register_crop", "INSERT INTO \"public\".\"g2p_register_crop"):
        assert forbidden not in code, forbidden
    # The only rows written directly: the farmer copy, its reference, and the intake's link to it.
    written = sorted(set(__import__("re").findall(r'INSERT INTO "?(?:public"\.")?"?(\w+)', code)))
    assert written == ["coss_farmer_references", "coss_farmer_submission_dependencies", "g2p_register_farmers"]
    for required in ("/auth/start_authentication_transaction", "kc-form-login", "/auth/callback",
                     "/intake-form-data/finalize_intake_form_submission", "/awe/submit_task_decision",
                     "INTAKE_SEED_APPROVER_1", "INTAKE_SEED_APPROVER_2", "INTAKE_SEED_PASSWORD"):
        assert required in code, required
    imported = {a.name.split(".")[0] for node in ast.walk(ast.parse(source))
                if isinstance(node, ast.Import) for a in node.names}
    assert not imported & {"requests", "httpx", "keycloak"}


def test_the_image_carries_the_loader_and_the_pinned_pack():
    dockerfile = (SEED / "Dockerfile").read_text(encoding="utf-8")
    assert "ARG OPENG2P_DATA_REPO=https://github.com/Centre-for-Open-Societal-Systems/openg2p-data.git" in dockerfile
    assert "docker/db-seed/load_sample_data.py /seed/" in dockerfile
    assert dockerfile.index("load_sample_data.py") > dockerfile.index("rm -rf /seed/")


PLACES = {
    "ET": {"level_value_id": "ET", "level_id": "l0", "level_value_mnemonic": "Ethiopia", "parent_level_value_id": None},
    "ET01": {"level_value_id": "ET01", "level_id": "l1", "level_value_mnemonic": "Tigray",
             "parent_level_value_id": "ET"},
    "ET0101": {"level_value_id": "ET0101", "level_id": "l2", "level_value_mnemonic": "North Western",
               "parent_level_value_id": "ET01"},
    "ET010101": {"level_value_id": "ET010101", "level_id": "l3", "level_value_mnemonic": "Tahtay Adiyabo",
                 "parent_level_value_id": "ET0101"},
    "ET01010102": {"level_value_id": "ET01010102", "level_id": "l4", "level_value_mnemonic": "Badme",
                   "parent_level_value_id": "ET010101"},
}
PEOPLE = [
    {"individual_id": "ETH-IND-0001", "given_name": "Berhanu", "fathers_name": "Abebe", "gender": "MALE",
     "birth_date": "1984-08-06", "phone": "+251941923320", "national_id": "502628318720",
     "geo_pcode": "ET01010102", "latitude": 14.4, "longitude": 37.7},
    {"individual_id": "ETH-IND-0002", "given_name": "Tsehay", "fathers_name": "Kebede", "gender": "FEMALE",
     "birth_date": "1988-02-29", "phone": "+251911000002", "national_id": "721996394985",
     "geo_pcode": "ET01010102", "latitude": 14.4, "longitude": 37.7},
]
FARMS = {"ETH-IND-0001": {"farmer": {"grandfathers_name": "Assefa"}},
         "ETH-IND-0002": {"farmer": {"grandfathers_name": "Tadesse"}}}
FARMER_IDS = {"ETH-IND-0001": "FR-100000000001", "ETH-IND-0002": "FR-100000000002"}
CROPS = [
    {"individual_id": "ETH-IND-0001", "production_season": "SEASON_MEHER", "location": {"latitude": 14.4,
                                                                                          "longitude": 37.7},
     "planning": [{"land_ref": "L1", "land_id": "Plot 1", "season": "SEASON_MEHER", "commodity": "CROP_TEFF",
                   "planned_date": "2026-05-10", "planned_area": 0.5}],
     "clusters": [{"land_ref": "L1", "land_id": "Plot 1", "cluster_name": "Badme Teff"}],
     "cultivation": [{"land_ref": "L1", "land_id": "Plot 1", "season": "SEASON_MEHER", "commodity": "CROP_TEFF",
                      "actual_cultivation_date": "2026-06-12"}],
     "sowing": [{"land_ref": "L1", "land_id": "Plot 1", "commodity": "CROP_TEFF", "cluster_status": "INDEPENDENT",
                 "area_sown": 0.5, "sowing_date": "2026-07-10"}],
     "infestations": [{"land_ref": "L1", "land_id": "Plot 1", "observation_date": "2026-08-02"}],
     "harvest": [{"land_ref": "L1", "land_id": "Plot 1", "commodity": "CROP_TEFF", "cluster_status": "INDEPENDENT",
                  "harvest_date": "2026-11-20", "qty_harvested": 6}]},
    {"individual_id": "ETH-IND-0002", "production_season": "SEASON_MEHER",
     "planning": [{"land_ref": "L1", "land_id": "Plot 1", "season": "SEASON_MEHER", "commodity": "CROP_MAIZE",
                   "planned_date": "2026-02-28"}]},
]
YEAR = 2028


def plan(loader, crops=CROPS, people=PEOPLE):
    ids = (f"id-{n}" for n in itertools.count(1))
    return loader.plan(people, FARMS, FARMER_IDS, crops, PLACES, YEAR, new_id=lambda: next(ids))


def test_each_stage_with_rows_is_one_intake_in_stage_order(loader):
    planned = plan(loader)
    assert [[s["form"][:2] for s in p["stages"]] for p in planned] == [["1.", "2.", "3.", "4."], ["1."]]
    planning = planned[0]["stages"][0]["sections"]
    root = planned[0]["stages"][0]["root"]
    assert list(planning) == ["crop_farmer_lookup", "cropsown_intake_season_section_01",
                              "cropsown_cropsown_location_section_03", "cropsown_planning_details_section_01",
                              "cropsown_cluster_details_section_01"]
    assert planning["crop_farmer_lookup"] == [{"internal_record_id": root, "farmer_id": "FR-100000000001",
                                               "fayda_id": "502628318720"}]
    assert planning["cropsown_intake_season_section_01"][0]["crop_year"] == "2028"
    line = planning["cropsown_planning_details_section_01"][0]
    assert line["link_internal_record_id"] == root and "land_ref" not in line and line["land_id"] == "Plot 1"
    sowing = planned[0]["stages"][2]["sections"]
    assert "cropsown_common_intake_season_section_01" in sowing and "cropsown_infestation_details_section_01" in sowing
    roots = {s["root"] for s in planned[0]["stages"]}
    assert len(roots) == 4  # every stage intake is its own record


def test_pack_dates_move_to_the_crop_year(loader):
    planned = plan(loader)
    assert planned[0]["stages"][3]["sections"]["cropsown_harvest_details_section_01"][0]["harvest_date"] \
        == "2028-11-20"
    assert planned[1]["stages"][0]["sections"]["cropsown_planning_details_section_01"][0]["planned_date"] \
        == "2028-02-28"
    assert loader.in_year("2026-02-28", 2027) == "2027-02-28" and loader.in_year("Plot 1", 2027) == "Plot 1"


def test_the_farmer_copy_is_the_reference_profile_with_location_and_search_text(loader):
    farmer = plan(loader)[0]["farmer"]
    assert farmer["farmer_id"] == "FR-100000000001" and farmer["fayda_fin"] == "502628318720"
    assert (farmer["first_name"], farmer["middle_name"], farmer["last_name"]) == ("Berhanu", "Abebe", "Assefa")
    assert farmer["mobile_number"] == "0941923320"
    assert farmer["kebele_id"] == "ET01010102" and farmer["region_name"] == "Tigray"
    assert [u["level_value_id"] for u in farmer["geo_code_hierarchy_json"]["hierarchy"]] == \
        ["ET", "ET01", "ET0101", "ET010101", "ET01010102"]
    assert "FR-100000000001" in farmer["search_text"] and "502628318720" in farmer["search_text"]


@pytest.mark.parametrize("change, message", [
    ({"crops": [{**CROPS[1], "individual_id": "ETH-IND-0099"}]}, "not a sample person"),
    ({"people": [PEOPLE[0], {**PEOPLE[1], "national_id": None}]}, "no Fayda ID"),
    ({"people": [PEOPLE[0], {**PEOPLE[1], "geo_pcode": "ET99"}]}, "pack's geography"),
])
def test_bad_samples_fail(loader, change, message):
    with pytest.raises(RuntimeError, match=message):
        plan(loader, **change)


class FakeRegistry:
    def __init__(self, previous=None, existing=None):
        self.previous, self.existing = dict(previous or {}), dict(existing or {})
        self.status, self.waited, self.pending, self.seeded = {}, [], [], []

    def ensure_farmer(self, farmer, created_by, approved_by, source_record_id):
        if farmer["fayda_fin"] in self.existing:
            farmer_id, how = self.existing[farmer["fayda_fin"]]
            return {"reference_id": "ref-existing", "farmer_id": farmer_id, "local_farmer_id": "local-existing",
                    "seeded": how}
        self.seeded.append((farmer["farmer_id"], created_by, approved_by, source_record_id))
        return {"reference_id": f"ref-{source_record_id}", "farmer_id": farmer["farmer_id"],
                "local_farmer_id": "local", "seeded": "seeded"}

    def stage_intakes(self, form_id, fin, year):
        return self.previous.get((form_id, fin), [])

    def approval_status(self, submission_id):
        return self.status.get(submission_id)

    def wait_for(self, table, record_id, timeout):
        self.waited.append((table, record_id))


class FakeApprover:
    """An approver whose task list holds one open task at its stage for every pending intake."""

    def __init__(self, name, stage, registry, calls):
        self.username, self.stage, self.registry, self.calls = name, stage, registry, calls

    def post(self, path, payload, once=False):
        self.calls.append((self.username, path))
        decided = getattr(self.registry, "decided", set())
        self.registry.decided = decided
        if path == "/awe/list_my_tasks":
            if payload["status"] != "open":
                return {"data": {"items": []}}
            return {"data": {"items": [{"id": f"task-{sid}-{self.stage}", "artifact_id": sid,
                                        "stage_order": self.stage} for sid in self.registry.pending
                                       if (sid, self.stage) not in decided
                                       and (self.stage == 1 or (sid, 1) in decided)]}}
        if path == "/awe/submit_task_decision":
            assert payload["current_stage"] == self.stage and payload["action"] == "approve"
            decided.add((payload["artifact_id"], self.stage))
            if self.stage == 2:
                self.registry.status[payload["artifact_id"]] = "APPROVED"
        return {}


def run(loader, registry):
    calls, submitted = [], []
    runner = loader.Loader.__new__(loader.Loader)
    runner.registry, runner.approve_timeout, runner.ingest_timeout, runner.year = registry, 5, 5, YEAR
    runner.submitter = types.SimpleNamespace(username="alex.carter")
    runner.approvers = [FakeApprover("alex.carter", 1, registry, calls), FakeApprover("nina.patel", 2, registry, calls)]
    runner.forms = {form: (f"form-{form[:1]}", "register", {}) for form, _, _ in loader.STAGES}

    def submit(stage, reference_id, draft=None):
        if draft:
            submitted.append(("draft", draft))
            registry.pending.append(draft)
            return draft
        sid = f"sub-{len(submitted) + 1}"
        submitted.append((stage["form"][:1], reference_id, stage["sections"]["crop_farmer_lookup"][0]["farmer_id"]))
        registry.pending.append(sid)
        return sid

    runner.submit = submit
    return runner.run(plan(loader)), submitted, calls


def test_farmers_are_seeded_and_every_stage_intake_approved_at_stage_1_then_stage_2(loader):
    registry = FakeRegistry()
    done, submitted, calls = run(loader, registry)
    assert done == {"farmers seeded": 2, "farmers restored": 0, "farmers referenced": 0, "intakes approved": 5,
                    "resumed": 0, "drafts completed": 0, "skipped": 0, "left for the next run": 0, "failed": 0}
    assert registry.seeded[0] == ("FR-100000000001", "alex.carter", "nina.patel", "ETH-IND-0001")
    assert [s[:2] for s in submitted] == [("1", "ref-ETH-IND-0001"), ("2", "ref-ETH-IND-0001"),
                                          ("3", "ref-ETH-IND-0001"), ("4", "ref-ETH-IND-0001"),
                                          ("1", "ref-ETH-IND-0002")]
    decisions = [c for c in calls if c[1] == "/awe/submit_task_decision"]
    assert decisions == [("alex.carter", "/awe/submit_task_decision"), ("nina.patel", "/awe/submit_task_decision")] * 5
    assert [t for t, _ in registry.waited] == ["g2p_register_crop_sowns"] * 5


@pytest.mark.parametrize("how", ["referenced", "restored"])
def test_a_farmer_already_referenced_keeps_its_farmer_id(loader, how):
    registry = FakeRegistry(existing={"502628318720": ("FR-209610506580", how)})
    done, submitted, _ = run(loader, registry)
    assert done[f"farmers {how}"] == 1 and done["farmers seeded"] == 1
    assert {s[2] for s in submitted[:4]} == {"FR-209610506580"} and submitted[0][1] == "ref-existing"


def test_a_rerun_skips_approved_stages_and_resumes_waiting_ones(loader):
    registry = FakeRegistry(previous={
        ("form-1", "502628318720"): [("sub-old", "FINAL", "APPROVED", "root-old")],
        ("form-2", "502628318720"): [("sub-draft", "DRAFT", None, "x"), ("sub-wait", "FINAL", "PENDING", "root-wait")],
    })
    registry.pending = ["sub-wait"]
    done, submitted, _ = run(loader, registry)
    assert done == {"farmers seeded": 2, "farmers restored": 0, "farmers referenced": 0, "intakes approved": 3,
                    "resumed": 1, "drafts completed": 0, "skipped": 1, "left for the next run": 0, "failed": 0}
    assert [s[0] for s in submitted] == ["3", "4", "1"]
    assert ("g2p_register_crop_sowns", "root-wait") in registry.waited


class FakeCursor:
    """A cursor over one reference row and the farmer copies, recording the statements it runs."""

    def __init__(self, reference=None, copies=()):
        self.reference, self.copies, self.statements, self._result = reference, set(copies), [], []

    def execute(self, sql, params=()):
        self.statements.append((" ".join(sql.split()), params))
        if "FROM coss_farmer_references" in sql:
            self._result = [self.reference] if self.reference else []
        elif "WHERE internal_record_id = %s" in sql:
            self._result = [(1,)] if params[0] in self.copies else []
        elif "FROM g2p_register_farmers" in sql:
            self._result = []
        else:
            self._result = []

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return self._result


def inserts(cur):
    return [sql.split(" (")[0] for sql, _ in cur.statements if sql.startswith("INSERT")]


def test_a_new_farmer_gets_a_copy_and_an_approved_reference(loader):
    cur = FakeCursor()
    farmer = plan(loader)[0]["farmer"]
    got = loader.Registry._ensure_farmer(cur, farmer, "alex.carter", "nina.patel", "ETH-IND-0001")
    assert got["seeded"] == "seeded" and got["farmer_id"] == "FR-100000000001"
    assert inserts(cur) == ['INSERT INTO "public"."g2p_register_farmers"', "INSERT INTO coss_farmer_references"]
    reference = [p for sql, p in cur.statements if sql.startswith("INSERT INTO coss_farmer_references")][0]
    assert reference[1:5] == ("farmer-registry", "ETH-IND-0001", "FR-100000000001", "502628318720")


def test_a_reference_whose_copy_was_deleted_gets_its_copy_back_under_its_own_ids(loader):
    cur = FakeCursor(reference=("ref-1", "FR-579834743732", "local-1", "APPROVED"))
    got = loader.Registry._ensure_farmer(cur, plan(loader)[0]["farmer"], "alex.carter", "nina.patel", "ETH-IND-0001")
    assert got == {"reference_id": "ref-1", "farmer_id": "FR-579834743732", "local_farmer_id": "local-1",
                   "seeded": "restored"}
    assert inserts(cur) == ['INSERT INTO "public"."g2p_register_farmers"']
    copy = [p for sql, p in cur.statements if sql.startswith('INSERT INTO "public"."g2p_register_farmers"')][0]
    assert "local-1" in copy and "FR-579834743732" in copy
    assert any("FR-579834743732" in str(v) and "Berhanu" in str(v) for v in copy)  # search text under its id


def test_an_intact_reference_is_used_as_it_is_and_a_pending_one_stops_the_load(loader):
    cur = FakeCursor(reference=("ref-1", "FR-209610506580", "local-1", "APPROVED"), copies={"local-1"})
    got = loader.Registry._ensure_farmer(cur, plan(loader)[0]["farmer"], "a", "b", "ETH-IND-0001")
    assert got["seeded"] == "referenced" and inserts(cur) == []
    with pytest.raises(RuntimeError, match="PENDING, not APPROVED"):
        loader.Registry._ensure_farmer(FakeCursor(reference=("ref-1", "FR-1", "local-1", "PENDING")),
                                       plan(loader)[0]["farmer"], "a", "b", "ETH-IND-0001")


KEYCLOAK_TOKEN = "https://keycloak.example.org/realms/staff/protocol/openid-connect/token"


@pytest.mark.parametrize("environ, expected", [
    ({"STAFF_IAM_URL": "https://iam.example.org", "STAFF_TOKEN_URL": KEYCLOAK_TOKEN}, "https://iam.example.org"),
    ({"STAFF_TOKEN_URL": KEYCLOAK_TOKEN}, "https://staff-iam.example.org"),
    ({"STAFF_TOKEN_URL": "https://keycloak.registry.example.org/realms/staff/protocol/openid-connect/token"},
     "https://staff-iam.registry.example.org"),
])
def test_staff_iam_is_the_public_host_next_to_keycloak(loader, monkeypatch, environ, expected):
    for name in ("STAFF_IAM_URL", "STAFF_TOKEN_URL"):
        monkeypatch.delenv(name, raising=False)
    for name, value in environ.items():
        monkeypatch.setenv(name, value)
    assert loader.staff_iam_url() == expected


@pytest.mark.parametrize("token_url", [None, "https://auth.example.org/realms/staff/protocol/openid-connect/token"])
def test_staff_iam_needs_the_address_when_keycloak_is_not_keycloak_domain(loader, monkeypatch, token_url):
    monkeypatch.delenv("STAFF_IAM_URL", raising=False)
    monkeypatch.delenv("STAFF_TOKEN_URL", raising=False)
    if token_url:
        monkeypatch.setenv("STAFF_TOKEN_URL", token_url)
    with pytest.raises(RuntimeError):
        loader.staff_iam_url()


class FlakyOpener:
    """Answers with the given outcomes in turn: an exception to raise, or a status code."""

    def __init__(self, *outcomes):
        self.outcomes, self.calls = list(outcomes), 0

    def open(self, request, timeout):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if outcome >= 400:
            raise __import__("urllib.error").error.HTTPError(request.full_url, outcome, "x", {}, __import__("io").BytesIO(b"{}"))
        response = __import__("io").BytesIO(b"{}")
        response.status, response.headers = outcome, {}
        response.__enter__ = lambda: response
        return __import__("contextlib").nullcontext(response)


def test_network_errors_and_gateway_statuses_are_retried(loader, monkeypatch):
    monkeypatch.setattr(loader.time, "sleep", lambda seconds: None)
    request = __import__("urllib.request").request.Request("https://staff-iam.example.org/x")
    opener = FlakyOpener(__import__("urllib.error").error.URLError("connection reset"), TimeoutError("timed out"), 503, 200)
    status, _, _ = loader.fetch(opener, request)
    assert status == 200 and opener.calls == 4


def test_other_statuses_are_returned_and_lasting_failures_raise(loader, monkeypatch):
    monkeypatch.setattr(loader.time, "sleep", lambda seconds: None)
    request = __import__("urllib.request").request.Request("https://staff-iam.example.org/x")
    opener = FlakyOpener(401)
    assert loader.fetch(opener, request)[0] == 401 and opener.calls == 1
    opener = FlakyOpener(*[OSError("unreachable")] * loader.NETWORK_ATTEMPTS)
    with pytest.raises(RuntimeError, match="unreachable"):
        loader.fetch(opener, request)


def test_tls_checks_follow_the_chart_setting(loader, monkeypatch):
    import ssl
    monkeypatch.setenv("INTAKE_SEED_VERIFY_TLS", "false")
    assert loader.tls_context().verify_mode == ssl.CERT_NONE
    monkeypatch.delenv("INTAKE_SEED_VERIFY_TLS")
    assert loader.tls_context().verify_mode == ssl.CERT_REQUIRED


def test_the_task_is_found_on_a_later_page(loader):
    class Pages:
        username = "nina.patel"

        def __init__(self):
            self.pages = []

        def post(self, path, payload):
            self.pages.append(payload["page"])
            if payload["page"] == 1:
                return {"data": {"items": [{"id": f"t{i}", "artifact_id": "other", "stage_order": 2}
                                           for i in range(loader.TASK_PAGE_SIZE)]}}
            return {"data": {"items": [{"id": "mine", "artifact_id": "sub-1", "stage_order": 2}]}}

    approver = Pages()
    assert loader.Loader.open_task(approver, "sub-1", 2)["id"] == "mine" and approver.pages == [1, 2]


def test_a_draft_left_by_a_failed_run_is_completed_not_entered_again(loader):
    registry = FakeRegistry(previous={("form-1", "502628318720"): [("sub-draft", "DRAFT", None, "x")]})
    done, submitted, _ = run(loader, registry)
    assert submitted[0] == ("draft", "sub-draft") and done["drafts completed"] == 1


def test_no_intake_starts_once_the_time_budget_is_used(loader):
    registry = FakeRegistry()
    loader.Loader.time_budget, saved = -1, loader.Loader.time_budget
    try:
        done, submitted, _ = run(loader, registry)
    finally:
        loader.Loader.time_budget = saved
    assert submitted == [] and done["left for the next run"] == sum(len(p["stages"]) for p in plan(loader))


def test_one_failing_farmer_does_not_stop_the_others(loader):
    registry = FakeRegistry()
    real = registry.ensure_farmer

    def ensure_farmer(farmer, *args):
        if farmer["fayda_fin"] == "502628318720":
            raise RuntimeError("this registry already holds another farmer")
        return real(farmer, *args)

    registry.ensure_farmer = ensure_farmer
    done, submitted, _ = run(loader, registry)
    assert done["failed"] == 1 and done["farmers seeded"] == 1 and submitted


def test_a_request_sent_once_is_not_retried(loader):
    import urllib.error
    import urllib.request

    request = urllib.request.Request("https://crop.example.org/awe/submit_task_decision")
    opener = FlakyOpener(urllib.error.URLError("connection reset"), 200)
    with pytest.raises(RuntimeError, match="connection reset"):
        loader.fetch(opener, request, attempts=1)
    assert opener.calls == 1


def test_the_retry_log_leaves_out_the_query(loader, monkeypatch):
    logged = []
    monkeypatch.setattr(loader.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(loader, "log", logged.append)
    request = __import__("urllib.request").request.Request("https://staff-iam.example.org/auth/callback?code=secret")
    loader.fetch(FlakyOpener(503, 200), request)
    assert logged and all("secret" not in line for line in logged)


class StageTwoApprover:
    """Stage 1 was approved by an earlier run; the stage 2 task waits, claimed or open."""

    def __init__(self, stage, claimed, registry, calls):
        self.username, self.stage, self.claimed, self.registry, self.calls = f"u{stage}", stage, claimed, registry, calls

    def post(self, path, payload, once=False):
        self.calls.append((self.username, path, once))
        if path == "/awe/list_my_tasks":
            wanted = "claimed" if self.claimed else "open"
            if self.stage == 2 and payload["status"] == wanted and self.registry.get("sub-1") != "APPROVED":
                return {"data": {"items": [{"id": "t2", "artifact_id": "sub-1", "stage_order": 2}]}}
            return {"data": {"items": []}}
        if path == "/awe/submit_task_decision":
            self.registry["sub-1"] = "APPROVED"
        return {}


@pytest.mark.parametrize("claimed", [False, True])
def test_approval_resumes_at_the_stage_reached(loader, claimed):
    status, calls = {}, []
    runner = loader.Loader.__new__(loader.Loader)
    runner.registry = types.SimpleNamespace(approval_status=status.get)
    runner.approve_timeout = 5
    runner.approvers = [StageTwoApprover(1, claimed, status, calls), StageTwoApprover(2, claimed, status, calls)]
    runner.approve("sub-1")
    sent = [(user, path) for user, path, once in calls if path != "/awe/list_my_tasks"]
    assert sent == ([] if claimed else [("u2", "/awe/claim_task")]) + [("u2", "/awe/submit_task_decision")]
    assert all(once for _, path, once in calls if path != "/awe/list_my_tasks")


def test_a_lost_decision_is_read_again_not_resent(loader, monkeypatch):
    monkeypatch.setattr(loader.time, "sleep", lambda seconds: None)
    status, calls = {}, []

    class LostAnswer(StageTwoApprover):
        def post(self, path, payload, once=False):
            reply = super().post(path, payload, once)
            if path == "/awe/submit_task_decision":
                raise RuntimeError("POST /awe/submit_task_decision: timed out")
            return reply

    runner = loader.Loader.__new__(loader.Loader)
    runner.registry = types.SimpleNamespace(approval_status=status.get)
    runner.approve_timeout = 5
    runner.approvers = [LostAnswer(1, True, status, calls), LostAnswer(2, True, status, calls)]
    runner.approve("sub-1")
    assert [path for _, path, _ in calls].count("/awe/submit_task_decision") == 1
