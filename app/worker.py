"""Celery application: the durable queue between the API and the workers.

    celery -A app.worker worker -Q cpu -c 8                         digital statements
    celery -A app.worker worker -Q ocr --pool=solo -n ocr@%h        GPU OCR (one per GPU)
    celery -A app.worker beat                                       purge + stuck-task reaper

Every file is one task. It starts on the "cpu" queue; when a page needs OCR
it is re-queued on "ocr", so scanned statements never hold a CPU worker and
digital ones never wait behind the GPU.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time

import redis
from celery import Celery
from celery.signals import worker_ready, worker_shutdown

from .config import settings

log = logging.getLogger("bsx.worker")

QUEUE_CPU = "cpu"
QUEUE_OCR = "ocr"
HEARTBEAT_PREFIX = "bsx:worker:"
HEARTBEAT_TTL = 120

celery_app = Celery("impera_cam", broker=settings.redis_url, include=["app.tasks"])
celery_app.conf.update(
    task_ignore_result=True,            # state lives in MySQL, not a result backend
    task_acks_late=True,                # a worker that dies mid-file gives the task back
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,       # long tasks: never reserve more than one
    task_default_queue=QUEUE_CPU,
    task_serializer="json",
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    # after a crash, an unacknowledged task is redelivered once this passes.
    # A normal stop is a warm shutdown: running files finish first (see the
    # stop_grace_period of the workers in docker-compose.yml)
    broker_transport_options={"visibility_timeout": settings.broker_visibility_seconds},
    beat_schedule={
        "purge-expired": {"task": "bsx.purge", "schedule": settings.purge_interval_seconds},
        "reap-stuck": {"task": "bsx.reap_stuck", "schedule": 300},
    },
)

_redis = None


def redis_client() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(settings.redis_url, socket_timeout=2,
                                      socket_connect_timeout=2)
    return _redis


# ---------------------------------------------------------------------------
# Heartbeats: /api/health reads these to show which queues have a live worker
# ---------------------------------------------------------------------------

_stop = threading.Event()


def _queues_of(consumer) -> list[str]:
    try:
        return sorted(q.name for q in consumer.task_consumer.queues)
    except Exception:                                      # noqa: BLE001
        return sorted(celery_app.amqp.queues.consume_from or [QUEUE_CPU])


@worker_ready.connect
def _start_heartbeat(sender=None, **_kw):
    from .core.ocr import probe

    queues = _queues_of(sender)
    hostname = getattr(sender, "hostname", None) or f"{socket.gethostname()}:{os.getpid()}"
    ocr = probe() if QUEUE_OCR in queues else None
    body = json.dumps({"host": hostname, "queues": queues, "ocr": ocr})
    key = HEARTBEAT_PREFIX + hostname

    def beat():
        while not _stop.is_set():
            try:
                redis_client().set(key, body, ex=HEARTBEAT_TTL)
            except redis.RedisError:
                log.warning("heartbeat: redis unavailable")
            _stop.wait(HEARTBEAT_TTL / 4)
        try:
            redis_client().delete(key)
        except redis.RedisError:
            pass

    threading.Thread(target=beat, name="bsx-heartbeat", daemon=True).start()
    log.info("worker ready queues=%s ocr=%s", ",".join(queues),
             (ocr or {}).get("device") if ocr else "-")


@worker_shutdown.connect
def _stop_heartbeat(**_kw):
    _stop.set()
    time.sleep(0.2)


def live_workers() -> list[dict]:
    out = []
    r = redis_client()
    for key in r.scan_iter(HEARTBEAT_PREFIX + "*"):
        raw = r.get(key)
        if raw:
            try:
                out.append(json.loads(raw))
            except ValueError:
                continue
    return out
