import os
import sys
import time
import signal
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Any, Optional, Set
from loguru import logger

from app.core.config import settings
from app.database.session import SessionLocal
from app.core.queue import QueueManager
from app.services.worker_service import WorkerService
from app.services.scheduler_daemon import SchedulerDaemon


class WorkerDaemon:
    """
    Production-grade background worker daemon.
    Executes claimed jobs in concurrent worker pool, sends periodic heartbeats,
    and handles graceful shutdown on SIGTERM / SIGINT.
    """

    def __init__(
        self,
        worker_id: Optional[str] = None,
        concurrency: Optional[int] = None,
        enable_scheduler: bool = True
    ):
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.concurrency = concurrency or settings.WORKER_CONCURRENCY
        self.enable_scheduler = enable_scheduler
        self.queue_mgr = QueueManager()
        self.start_time = time.time()

        self._shutdown_event = threading.Event()
        self._active_jobs: Dict[str, uuid.UUID] = {}  # future_id -> job_id
        self._lock = threading.Lock()

        self.executor = ThreadPoolExecutor(max_workers=self.concurrency, thread_name_prefix=f"WorkerPool-{self.worker_id}")
        self.scheduler: Optional[SchedulerDaemon] = None

        if self.enable_scheduler:
            self.scheduler = SchedulerDaemon(
                db_session_factory=SessionLocal,
                queue_mgr=self.queue_mgr,
                poll_interval=settings.SCHEDULER_POLL_INTERVAL_SECONDS,
                leader_ttl=settings.SCHEDULER_LEADER_TTL_SECONDS,
                instance_id=f"sched_{self.worker_id}"
            )

    def _register_signals(self) -> None:
        """Hooks SIGTERM and SIGINT for graceful drain."""
        def _handle_shutdown(signum, frame):
            logger.info(f"Received signal {signum}. Initiating graceful shutdown for worker '{self.worker_id}'...")
            self.stop()

        try:
            signal.signal(signal.SIGTERM, _handle_shutdown)
            signal.signal(signal.SIGINT, _handle_shutdown)
        except Exception as e:
            logger.debug(f"Signal registration limited in current environment: {e}")

    def get_health_status(self) -> Dict[str, Any]:
        """Returns runtime health and capacity metrics."""
        with self._lock:
            active_count = len(self._active_jobs)

        return {
            "status": "healthy" if not self._shutdown_event.is_set() else "draining",
            "worker_id": self.worker_id,
            "concurrency": self.concurrency,
            "active_jobs_count": active_count,
            "uptime_seconds": round(time.time() - self.start_time, 2),
            "scheduler_enabled": self.enable_scheduler,
            "is_scheduler_leader": bool(self.scheduler and self.scheduler.is_running)
        }

    def _execute_job_task(self, job_id: uuid.UUID) -> None:
        """Worker task executed in thread pool."""
        db = SessionLocal()
        try:
            worker_svc = WorkerService(db, queue_mgr=self.queue_mgr)
            worker_svc.process_job(job_id=job_id, worker_id=self.worker_id)
        except Exception as e:
            logger.error(f"Worker task error for job {job_id}: {e}")
        finally:
            db.close()
            with self._lock:
                # Remove from active tracking
                for k, v in list(self._active_jobs.items()):
                    if v == job_id:
                        del self._active_jobs[k]
                        break

    def run_heartbeat_loop(self) -> None:
        """Background thread updating worker and job heartbeats."""
        interval = settings.WORKER_HEARTBEAT_INTERVAL_SECONDS
        while not self._shutdown_event.is_set():
            try:
                # 1. Update worker node registry
                health = self.get_health_status()
                self.queue_mgr.register_worker_heartbeat(self.worker_id, health, ttl_seconds=interval * 3)

                # 2. Update active job heartbeats in DB
                with self._lock:
                    active_job_ids = list(self._active_jobs.values())

                if active_job_ids:
                    db = SessionLocal()
                    try:
                        worker_svc = WorkerService(db, queue_mgr=self.queue_mgr)
                        for jid in active_job_ids:
                            worker_svc.update_heartbeat(jid, self.worker_id)
                    except Exception as e:
                        logger.warning(f"Failed updating job heartbeats: {e}")
                    finally:
                        db.close()
            except Exception as e:
                logger.error(f"Heartbeat loop exception: {e}")

            self._shutdown_event.wait(interval)

    def start(self) -> None:
        """Starts worker loops, scheduler, and heartbeat coordinator."""
        logger.info(f"Starting WorkerDaemon '{self.worker_id}' with concurrency={self.concurrency}...")
        self._register_signals()

        # Start Scheduler if enabled
        if self.scheduler:
            self.scheduler.start()

        # Start Heartbeat thread
        hb_thread = threading.Thread(target=self.run_heartbeat_loop, name=f"Heartbeat-{self.worker_id}", daemon=True)
        hb_thread.start()

        # Main worker dequeue & claim loop
        logger.info(f"WorkerDaemon '{self.worker_id}' ready for background jobs.")
        while not self._shutdown_event.is_set():
            try:
                with self._lock:
                    available_slots = self.concurrency - len(self._active_jobs)

                if available_slots <= 0:
                    time.sleep(0.5)
                    continue

                # 1. Pop from Redis queue
                job_id_str = self.queue_mgr.dequeue(timeout_seconds=1)

                db = SessionLocal()
                try:
                    worker_svc = WorkerService(db, queue_mgr=self.queue_mgr)
                    claimed_job = None

                    if job_id_str:
                        try:
                            # Attempt atomic claim on dequeued job
                            claimed_job = worker_svc.claim_next_job(
                                worker_id=self.worker_id,
                                preferred_job_types=None,
                                max_tenant_concurrency=settings.MAX_TENANT_CONCURRENCY
                            )
                        except Exception as e:
                            logger.error(f"Error claiming dequeued job {job_id_str}: {e}")
                    else:
                        # Direct DB polling fallback
                        claimed_job = worker_svc.claim_next_job(
                            worker_id=self.worker_id,
                            preferred_job_types=None,
                            max_tenant_concurrency=settings.MAX_TENANT_CONCURRENCY
                        )

                    if claimed_job:
                        with self._lock:
                            task_key = str(uuid.uuid4())
                            self._active_jobs[task_key] = claimed_job.id
                            self.executor.submit(self._execute_job_task, claimed_job.id)
                    else:
                        # Sleep briefly when no work found
                        time.sleep(1.0)
                finally:
                    db.close()

            except Exception as e:
                logger.error(f"Error in worker main loop: {e}")
                time.sleep(1.0)

        logger.info(f"WorkerDaemon '{self.worker_id}' loop ended.")

    def stop(self) -> None:
        """Gracefully halts worker and drains running tasks."""
        if self._shutdown_event.is_set():
            return

        logger.info(f"WorkerDaemon '{self.worker_id}' shutting down...")
        self._shutdown_event.set()

        if self.scheduler:
            self.scheduler.stop()

        # Drain thread pool
        grace_period = settings.WORKER_SHUTDOWN_TIMEOUT_SECONDS
        logger.info(f"Draining worker pool (waiting up to {grace_period}s for in-flight tasks)...")
        self.executor.shutdown(wait=True, cancel_futures=False)
        logger.info(f"WorkerDaemon '{self.worker_id}' terminated cleanly.")


if __name__ == "__main__":
    enable_sched = os.getenv("ENABLE_SCHEDULER", "true").lower() in ("true", "1", "yes")
    concurrency_env = int(os.getenv("WORKER_CONCURRENCY", "10"))
    worker = WorkerDaemon(concurrency=concurrency_env, enable_scheduler=enable_sched)
    try:
        worker.start()
    except KeyboardInterrupt:
        worker.stop()
