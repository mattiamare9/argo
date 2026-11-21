"""Coda di job persistente con retry, backoff e idempotenza. Non conosce il dominio."""

from app.modules.jobs.models import Job, JobStatus
from app.modules.jobs.service import (
    LEASE,
    MAX_BACKOFF,
    Handler,
    ManualActionRequired,
    PermanentError,
    backoff,
    by_group,
    claim,
    complete,
    enqueue,
    fail,
    resolve_manual,
    retry_now,
    run_once,
)

__all__ = [
    "LEASE",
    "MAX_BACKOFF",
    "Handler",
    "Job",
    "JobStatus",
    "ManualActionRequired",
    "PermanentError",
    "backoff",
    "by_group",
    "claim",
    "complete",
    "enqueue",
    "fail",
    "resolve_manual",
    "retry_now",
    "run_once",
]
