"""Approvals: a message is required to approve or reject (intake forms and change requests).
The server refuses an empty or blank message before the decision reaches the workflow engine;
the platform's approval card shows the refusal as an error toast."""
import asyncio
from types import SimpleNamespace
from unittest import mock

import pytest

pytest.importorskip("openg2p_registry_core")

from openg2p_registry_core.controller_services import G2PAweProxyControllerService  # noqa: E402
from openg2p_registry_core.errors import G2PRegistryException  # noqa: E402

from openg2p_registry_cropsown_extension.awe_proxy import ScopedAweProxyControllerService  # noqa: E402


def decide(comment):
    service = object.__new__(ScopedAweProxyControllerService)
    payload = SimpleNamespace(task_id="t1", action="approve", comment=comment)
    with mock.patch.object(G2PAweProxyControllerService, "submit_task_decision",
                           new=mock.AsyncMock(return_value={"decision": "ok"})) as platform:
        result = asyncio.run(service.submit_task_decision(payload, bearer_token="token"))
    return result, platform


@pytest.mark.parametrize("comment", [None, "", "   "])
def test_an_empty_message_is_refused_before_the_workflow_engine(comment):
    with mock.patch.object(G2PAweProxyControllerService, "submit_task_decision",
                           new=mock.AsyncMock()) as platform:
        service = object.__new__(ScopedAweProxyControllerService)
        with pytest.raises(G2PRegistryException) as error:
            asyncio.run(service.submit_task_decision(
                SimpleNamespace(task_id="t1", action="reject", comment=comment), bearer_token="token"))
    assert error.value.message == "A message is required to approve or reject"
    platform.assert_not_awaited()


def test_a_message_passes_the_decision_to_the_platform():
    result, platform = decide("Checked the land details")
    assert result == {"decision": "ok"}
    platform.assert_awaited_once()
