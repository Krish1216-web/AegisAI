import time
import uuid
import threading
from typing import Optional, Dict, Any, Callable
from loguru import logger
from sqlalchemy.orm import Session

from app.core.queue import QueueManager
from app.core.config import settings
from app.services.workflow_scheduler import WorkflowSchedulerService
from app.services.worker_service import WorkerService


class SchedulerDaemon:
    """
    High-availability distributed scheduler daemon with Redis leader election.
    Only the active leader instance evaluates cron schedules, sweeps delayed queues,
    and triggers stale-job recovery.
    """

    def __init__(
        self,
        db_session_factory: Callable[[], Session],
        queue_mgr: Optional[QueueManager] = None,
        poll_interval: float = 5.0,
        leader_ttl: int = 15,
        instance_id: Optional[str] = None
    ):
        self.db_factory = db_session_factory
        self.queue_mgr = queue_mgr or QueueManager()
        self.poll_interval = poll_interval
        self.leader_ttl = leader_ttl
        self.instance_id = instance_id or f"scheduler_{uuid.uuid4().hex[:8]}"
        self.is_running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def run_cycle(self) -> Dict[str, Any]:
        """
        Executes one scheduler iteration. If this node is the leader, evaluates due jobs.
        """
        lock_key = QueueManager.LEADER_LOCK_KEY

        # Attempt to acquire or renew leader lock
        is_leader = self.queue_mgr.acquire_lock(lock_key, self.instance_id, ttl_seconds=self.leader_ttl)
        if not is_leader:
            # Check if we already own it and need renewal
            is_leader = self.queue_mgr.renew_lock(lock_key, self.instance_id, ttl_seconds=self.leader_ttl)

        if not is_leader:
            logger.debug(f"Scheduler '{self.instance_id}' is in STANDBY (not leader).")
            return {"is_leader": False, "status": "standby", "instance_id": self.instance_id}

        # Node is active leader
        logger.debug(f"Scheduler '{self.instance_id}' executing active cycle as LEADER.")
        enqueued_schedules_count = 0
        recovered_stale_count = 0
        delayed_jobs_pushed = 0

        # 1. Process delayed queue
        try:
            delayed_jobs = self.queue_mgr.poll_delayed_jobs()
            delayed_jobs_pushed = len(delayed_jobs)
        except Exception as e:
            logger.error(f"Scheduler error polling delayed jobs: {e}")

        # 2. Database evaluation
        db = self.db_factory()
        try:
            wf_scheduler = WorkflowSchedulerService(db)
            enqueued = wf_scheduler.enqueue_due_schedules(max_batch=50)
            enqueued_schedules_count = len(enqueued)

            worker_svc = WorkerService(db, queue_mgr=self.queue_mgr)
            recovered = worker_svc.recover_stale_jobs(stale_timeout_seconds=settings.WORKER_STALE_TIMEOUT_SECONDS)
            recovered_stale_count = len(recovered)
        except Exception as e:
            logger.error(f"Scheduler database cycle error: {e}")
        finally:
            db.close()

        return {
            "is_leader": True,
            "instance_id": self.instance_id,
            "enqueued_schedules": enqueued_schedules_count,
            "recovered_stale": recovered_stale_count,
            "delayed_pushed": delayed_jobs_pushed
        }

    def start(self) -> None:
        """Starts background daemon loop in separate thread."""
        if self.is_running:
            return

        self.is_running = True
        self._stop_event.clear()

        def _loop():
            logger.info(f"SchedulerDaemon '{self.instance_id}' started.")
            while not self._stop_event.is_set():
                try:
                    self.run_cycle()
                except Exception as e:
                    logger.error(f"Unexpected error in SchedulerDaemon loop: {e}")
                self._stop_event.wait(self.poll_interval)
            logger.info(f"SchedulerDaemon '{self.instance_id}' stopped.")

        self._thread = threading.Thread(target=_loop, name=f"Scheduler-{self.instance_id}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stops background daemon and safely releases leader lock if owned."""
        if not self.is_running:
            return

        self.is_running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)

        try:
            self.queue_mgr.release_lock(QueueManager.LEADER_LOCK_KEY, self.instance_id)
        except Exception as e:
            logger.debug(f"Could not release leader lock on shutdown: {e}")
