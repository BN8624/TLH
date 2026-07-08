# TLH live worker limit 라우팅과 metadata 기록을 검증한다.

from __future__ import annotations

import os
from pathlib import Path

from tlh import dispatcher
from tlh.live_routing import LiveRoutingDecision
from tlh.schemas import TaskCard, WorkerResult
from tlh.vault import init_project


def card(task_id: str, backend_hint: str = "") -> TaskCard:
    return TaskCard(
        task_id=task_id,
        run_id="run-limit",
        loop_index=0,
        title=f"Task {task_id}",
        goal="Validate live worker limit.",
        worker_role="builder",
        expected_output="WorkerResult",
        attach_point="FinalPacket.Scope",
        merge_key="s4_limit_policy",
        backend_hint=backend_hint,
    )


def test_live_worker_limit_caps_auto_backend(monkeypatch, tmp_path: Path) -> None:
    init_project(tmp_path)
    rows = [card("T001").to_dict(), card("T002").to_dict(), card("T003").to_dict()]
    monkeypatch.setenv("TLH_WORKER_BACKEND", "auto")
    monkeypatch.setenv("TLH_GEMMA_API_KEY", "SECRET_VALUE")
    monkeypatch.setenv("TLH_LIVE_WORKER_LIMIT", "2")
    calls: list[tuple[str, str, int | None, int]] = []

    def fake_run_worker(
        task_card: TaskCard,
        env: dict[str, str] | None = None,
        routing_decision: LiveRoutingDecision | None = None,
    ) -> WorkerResult:
        assert env is not None
        assert routing_decision is not None
        backend = routing_decision.selected_backend
        calls.append(
            (
                task_card.task_id,
                backend,
                routing_decision.live_worker_index,
                routing_decision.max_live_workers,
            )
        )
        return WorkerResult(
            task_id=task_card.task_id,
            worker_id=f"{backend}-{task_card.worker_role}",
            summary=f"{backend} result",
            findings=[f"scope: {backend} result"],
            attach_notes=["target: FinalPacket.Scope | content: result"],
            stub_generated=backend != "live",
            live_generated=backend == "live",
            backend=backend,
            metadata={
                "backend": backend,
                "live_worker_limit": routing_decision.max_live_workers,
                "policy_mode": routing_decision.policy_mode,
                "requested_backend": routing_decision.requested_backend,
                "selected_backend": backend,
                "routing_reason": routing_decision.routing_reason,
                **({"live_worker_index": routing_decision.live_worker_index} if backend == "live" else {}),
            },
        )

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)

    results = dispatcher.dispatch(tmp_path, "run-limit", rows)

    assert [result.backend for result in results] == ["live", "live", "stub"]
    assert calls == [("T001", "live", 1, 2), ("T002", "live", 2, 2), ("T003", "stub", None, 2)]
    assert [result.metadata["live_worker_limit"] for result in results] == [2, 2, 2]
    assert [result.metadata.get("live_worker_index") for result in results] == [1, 2, None]
    assert "SECRET_VALUE" not in (tmp_path / "machine" / "runs" / "run-limit" / "worker_results.jsonl").read_text(
        encoding="utf-8"
    )


def test_live_worker_limit_zero_forces_stub(monkeypatch, tmp_path: Path) -> None:
    init_project(tmp_path)
    rows = [card("T001").to_dict(), card("T002").to_dict()]
    monkeypatch.setenv("TLH_WORKER_BACKEND", "live")
    monkeypatch.setenv("TLH_GEMMA_API_KEY", "SECRET_VALUE")
    monkeypatch.setenv("TLH_LIVE_WORKER_LIMIT", "0")

    def fake_run_worker(
        task_card: TaskCard,
        env: dict[str, str] | None = None,
        routing_decision: LiveRoutingDecision | None = None,
    ) -> WorkerResult:
        assert env is not None
        assert routing_decision is not None
        backend = routing_decision.selected_backend
        return WorkerResult(
            task_id=task_card.task_id,
            worker_id=f"{backend}-{task_card.worker_role}",
            summary=f"{backend} result",
            backend=backend,
            stub_generated=backend != "live",
            live_generated=backend == "live",
            metadata={"backend": backend, "live_worker_limit": routing_decision.max_live_workers},
        )

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)

    results = dispatcher.dispatch(tmp_path, "run-limit", rows)

    assert [result.backend for result in results] == ["stub", "stub"]
    assert all(result.metadata["live_worker_limit"] == 0 for result in results)


def test_live_worker_limit_does_not_mutate_process_env(monkeypatch, tmp_path: Path) -> None:
    init_project(tmp_path)
    monkeypatch.setenv("TLH_WORKER_BACKEND", "auto")
    monkeypatch.setenv("TLH_GEMMA_API_KEY", "SECRET_VALUE")
    monkeypatch.setenv("TLH_LIVE_WORKER_LIMIT", "1")

    def fake_run_worker(
        task_card: TaskCard,
        env: dict[str, str] | None = None,
        routing_decision: LiveRoutingDecision | None = None,
    ) -> WorkerResult:
        assert env is not None
        assert routing_decision is not None
        return WorkerResult(
            task_id=task_card.task_id,
            worker_id="stub-builder",
            summary="stub result",
            backend=routing_decision.selected_backend,
            metadata={"backend": routing_decision.selected_backend},
        )

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)

    dispatcher.dispatch(tmp_path, "run-limit", [card("T001").to_dict(), card("T002").to_dict()])

    assert os.environ.get("TLH_FORCE_WORKER_BACKEND") is None
    assert os.environ.get("TLH_LIVE_WORKER_INDEX") is None


def test_dispatch_uses_rotating_key_health_pool_for_live_workers(monkeypatch, tmp_path: Path) -> None:
    init_project(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(f"GOOGLE_API_KEY_{slot}=SECRET_{slot}" for slot in range(1, 23)),
        encoding="utf-8",
    )
    rows = [card(f"T{index:03d}").to_dict() for index in range(1, 12)]
    monkeypatch.setenv("TLH_WORKER_BACKEND", "auto")
    monkeypatch.delenv("TLH_GEMMA_API_KEY", raising=False)
    monkeypatch.setenv("TLH_LIVE_WORKER_LIMIT", "11")

    def fake_run_worker(
        task_card: TaskCard,
        env: dict[str, str] | None = None,
        routing_decision: LiveRoutingDecision | None = None,
        retry_budget=None,
        key_health_pool=None,
    ) -> WorkerResult:
        del retry_budget
        assert env is not None
        assert routing_decision is not None
        backend = routing_decision.selected_backend
        key_slot = None
        if backend == "live":
            assert key_health_pool is not None
            assert "TLH_GEMMA_API_KEY" not in env
            lease = key_health_pool.select_key(worker_index=routing_decision.worker_index)
            assert lease is not None
            key_slot = lease.key_slot
        return WorkerResult(
            task_id=task_card.task_id,
            worker_id=f"{backend}-{task_card.worker_role}",
            summary=f"{backend} result",
            findings=[f"scope: {backend} result"],
            backend=backend,
            stub_generated=backend != "live",
            live_generated=backend == "live",
            metadata={
                "backend": backend,
                "selected_backend": backend,
                "requested_backend": routing_decision.requested_backend,
                "key_slot": int(key_slot) if key_slot else None,
                "available_key_slots": int(env.get("TLH_GEMMA_KEY_POOL_AVAILABLE_SLOTS", "0")),
                "key_pool_mode": env.get("TLH_GEMMA_KEY_POOL_MODE", ""),
            },
        )

    monkeypatch.setattr(dispatcher, "run_worker", fake_run_worker)

    results = dispatcher.dispatch(tmp_path, "run-limit", rows)

    assert [result.backend for result in results] == ["live"] * 11
    assert [result.metadata["key_slot"] for result in results] == list(range(1, 12))
    written = (tmp_path / "machine" / "runs" / "run-limit" / "worker_results.jsonl").read_text(encoding="utf-8")
    assert "SECRET_" not in written
