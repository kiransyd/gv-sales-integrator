from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.settings import Settings, get_settings
from app.services.event_store_service import load_event
from app.services.idempotency_service import get_processed_value

router = APIRouter(prefix="/debug")


def _require_debug(settings: Settings = Depends(get_settings)) -> Settings:
    if not settings.ALLOW_DEBUG_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Not found")
    return settings


@router.get("/ping")
def ping(_: Settings = Depends(_require_debug)) -> dict:
    return {"ok": True}


@router.get("/info")
def info(settings: Settings = Depends(_require_debug)) -> dict[str, Any]:
    # Avoid leaking secrets; this is intentionally small.
    return {
        "env": settings.ENV,
        "dry_run": settings.DRY_RUN,
        "redis_url": settings.REDIS_URL,
        "rq_queue_name": settings.RQ_QUEUE_NAME,
        "llm_provider": settings.LLM_PROVIDER,
    }


@router.get("/echo_json")
def echo_json(raw: str, _: Settings = Depends(_require_debug)) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/events/{event_id}")
def debug_event(event_id: str, _: Settings = Depends(_require_debug)) -> dict[str, Any]:
    ev = load_event(event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return {
        "id": ev.event_id,
        "source": ev.source,
        "event_type": ev.event_type,
        "external_id": ev.external_id,
        "idempotency_key": ev.idempotency_key,
        "received_at": ev.received_at,
        "status": ev.status,
        "attempts": ev.attempts,
        "last_error": ev.last_error,
        "payload": ev.payload,
    }


@router.get("/idem/{idempotency_key}")
def debug_idem(idempotency_key: str, _: Settings = Depends(_require_debug)) -> dict[str, Any]:
    v = get_processed_value(idempotency_key)
    return {"idempotency_key": idempotency_key, "processed": v == "1", "value": v}


@router.get("/status")
def system_status(settings: Settings = Depends(_require_debug)) -> dict[str, Any]:
    """
    Comprehensive system status endpoint showing:
    - Server health (API, Redis, settings)
    - Worker status (active, failed, workers)
    - Queue metrics (pending, processing, failed, finished)
    - Recent activity (events, jobs)
    - Integration status (Zoho, Apollo, Gemini, BrandFetch)
    - System metrics (memory, uptime)
    """
    import time
    import psutil
    from datetime import datetime, timezone
    from redis import Redis
    from rq import Queue, Worker
    from rq.registry import (
        StartedJobRegistry,
        FinishedJobRegistry,
        FailedJobRegistry,
        ScheduledJobRegistry,
    )

    status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "server": {},
        "redis": {},
        "queue": {},
        "workers": {},
        "recent_activity": {},
        "integrations": {},
        "system": {},
    }

    # ========== SERVER HEALTH ==========
    try:
        status["server"] = {
            "status": "healthy",
            "environment": settings.ENV,
            "dry_run_mode": settings.DRY_RUN,
            "debug_endpoints_enabled": settings.ALLOW_DEBUG_ENDPOINTS,
            "base_url": settings.BASE_URL,
        }
    except Exception as e:
        status["server"] = {"status": "error", "error": str(e)}

    # ========== REDIS CONNECTION ==========
    try:
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_info = redis_client.info()
        redis_ping = redis_client.ping()

        status["redis"] = {
            "status": "connected" if redis_ping else "disconnected",
            "ping": redis_ping,
            "version": redis_info.get("redis_version", "unknown"),
            "uptime_seconds": redis_info.get("uptime_in_seconds", 0),
            "connected_clients": redis_info.get("connected_clients", 0),
            "used_memory_human": redis_info.get("used_memory_human", "unknown"),
            "total_connections_received": redis_info.get("total_connections_received", 0),
            "total_commands_processed": redis_info.get("total_commands_processed", 0),
            "keyspace": redis_info.get("db0", {}),
        }
    except Exception as e:
        status["redis"] = {"status": "error", "error": str(e)}

    # ========== QUEUE METRICS ==========
    try:
        redis_client = Redis.from_url(settings.REDIS_URL)
        queue = Queue(settings.RQ_QUEUE_NAME, connection=redis_client)

        # Get registries
        started_registry = StartedJobRegistry(queue.name, connection=redis_client)
        finished_registry = FinishedJobRegistry(queue.name, connection=redis_client)
        failed_registry = FailedJobRegistry(queue.name, connection=redis_client)
        scheduled_registry = ScheduledJobRegistry(queue.name, connection=redis_client)

        # Get job counts
        pending_count = queue.count
        started_count = len(started_registry)
        finished_count = len(finished_registry)
        failed_count = len(failed_registry)
        scheduled_count = len(scheduled_registry)

        # Get job IDs for active jobs
        started_job_ids = started_registry.get_job_ids()
        failed_job_ids = failed_registry.get_job_ids()[:10]  # Last 10 failed jobs

        # Get details of currently running jobs
        active_jobs = []
        for job_id in started_job_ids:
            try:
                job = queue.fetch_job(job_id)
                if job:
                    active_jobs.append({
                        "id": job.id,
                        "func_name": job.func_name if hasattr(job, 'func_name') else "unknown",
                        "created_at": job.created_at.isoformat() if hasattr(job, 'created_at') and job.created_at else None,
                        "started_at": job.started_at.isoformat() if hasattr(job, 'started_at') and job.started_at else None,
                        "timeout": job.timeout if hasattr(job, 'timeout') else None,
                    })
            except Exception:
                pass

        # Get details of recent failed jobs
        failed_jobs = []
        for job_id in failed_job_ids:
            try:
                job = queue.fetch_job(job_id)
                if job:
                    failed_jobs.append({
                        "id": job.id,
                        "func_name": job.func_name if hasattr(job, 'func_name') else "unknown",
                        "failed_at": job.ended_at.isoformat() if hasattr(job, 'ended_at') and job.ended_at else None,
                        "exc_info": job.exc_info[:200] if hasattr(job, 'exc_info') and job.exc_info else None,
                    })
            except Exception:
                pass

        status["queue"] = {
            "status": "healthy",
            "name": settings.RQ_QUEUE_NAME,
            "counts": {
                "pending": pending_count,
                "started": started_count,
                "finished": finished_count,
                "failed": failed_count,
                "scheduled": scheduled_count,
                "total": pending_count + started_count + scheduled_count,
            },
            "active_jobs": active_jobs,
            "recent_failed_jobs": failed_jobs,
        }
    except Exception as e:
        status["queue"] = {"status": "error", "error": str(e)}

    # ========== WORKER STATUS ==========
    try:
        redis_client = Redis.from_url(settings.REDIS_URL)
        workers = Worker.all(connection=redis_client)

        worker_list = []
        for worker in workers:
            worker_list.append({
                "name": worker.name,
                "state": worker.get_state(),
                "current_job_id": worker.get_current_job_id(),
                "successful_job_count": worker.successful_job_count if hasattr(worker, 'successful_job_count') else 0,
                "failed_job_count": worker.failed_job_count if hasattr(worker, 'failed_job_count') else 0,
                "birth_date": worker.birth_date.isoformat() if hasattr(worker, 'birth_date') and worker.birth_date else None,
            })

        status["workers"] = {
            "status": "healthy" if len(workers) > 0 else "no_workers",
            "count": len(workers),
            "workers": worker_list,
        }
    except Exception as e:
        status["workers"] = {"status": "error", "error": str(e)}

    # ========== RECENT ACTIVITY ==========
    try:
        from app.services.event_store_service import _event_key
        redis_client = Redis.from_url(settings.REDIS_URL)

        # Get recent event IDs (last 20)
        event_keys = []
        for key in redis_client.scan_iter(match="event:*", count=100):
            event_keys.append(key.decode('utf-8'))

        # Sort by timestamp (event IDs are timestamped)
        event_keys.sort(reverse=True)
        recent_event_keys = event_keys[:20]

        recent_events = []
        for key in recent_event_keys:
            try:
                event_data = redis_client.hgetall(key)
                if event_data:
                    recent_events.append({
                        "event_id": event_data.get(b"event_id", b"").decode('utf-8'),
                        "source": event_data.get(b"source", b"").decode('utf-8'),
                        "event_type": event_data.get(b"event_type", b"").decode('utf-8'),
                        "status": event_data.get(b"status", b"").decode('utf-8'),
                        "received_at": event_data.get(b"received_at", b"").decode('utf-8'),
                    })
            except Exception:
                pass

        status["recent_activity"] = {
            "total_events": len(event_keys),
            "recent_events": recent_events[:10],  # Show last 10
        }
    except Exception as e:
        status["recent_activity"] = {"status": "error", "error": str(e)}

    # ========== INTEGRATION STATUS ==========
    integrations = {}

    # Zoho
    integrations["zoho"] = {
        "configured": bool(settings.ZOHO_CLIENT_ID and settings.ZOHO_CLIENT_SECRET and settings.ZOHO_REFRESH_TOKEN),
        "data_center": settings.ZOHO_DC,
        "dry_run": settings.DRY_RUN,
    }

    # Apollo
    integrations["apollo"] = {
        "configured": bool(settings.APOLLO_API_KEY),
    }

    # Gemini
    integrations["gemini"] = {
        "configured": bool(settings.GEMINI_API_KEY),
        "model": settings.GEMINI_MODEL,
        "provider": settings.LLM_PROVIDER,
    }

    # BrandFetch
    integrations["brandfetch"] = {
        "configured": bool(settings.BRAND_FETCH_API),
    }

    # Calendly
    integrations["calendly"] = {
        "configured": bool(settings.CALENDLY_SIGNING_KEY),
    }

    # Read.ai
    integrations["readai"] = {
        "configured": bool(settings.READAI_SHARED_SECRET),
    }

    # Website scraping
    integrations["website_scraping"] = {
        "enabled": settings.ENABLE_WEBSITE_SCRAPING,
        "crawl4ai": True,  # Always available
        "scraperapi": bool(settings.SCRAPER_API_KEY),
    }

    # Auto enrichment
    integrations["auto_enrichment"] = {
        "enabled": settings.ENABLE_AUTO_ENRICH_CALENDLY,
    }

    status["integrations"] = integrations

    # ========== SYSTEM METRICS ==========
    try:
        process = psutil.Process()
        memory_info = process.memory_info()

        status["system"] = {
            "cpu_percent": process.cpu_percent(interval=0.1),
            "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
            "memory_percent": round(process.memory_percent(), 2),
            "num_threads": process.num_threads(),
            "uptime_seconds": round(time.time() - process.create_time(), 2),
        }
    except Exception as e:
        status["system"] = {"status": "error", "error": str(e)}

    return status


