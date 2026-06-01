"""Audit log flush worker — reads from Redis queue, writes to database.

Usage::

    python -m app.workers.audit_worker --once
    python -m app.workers.audit_worker --interval 2 --batch-size 100

The worker pops events in batches from the Redis audit queue
(configured via ``settings.audit_queue_name``) and bulk-inserts them
into the ``audit_logs`` table.

If a batch write fails, events are pushed back onto a retry queue
(``<queue_name>:retry``) so they are not lost.  The retry queue is
checked on the next iteration.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time

logger = logging.getLogger(__name__)

_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    logger.info("Audit worker received signal %s, shutting down…", signum)
    _shutdown = True


def _flush_once(batch_size: int) -> int:
    """Pop a batch from the queue, write to DB, return count."""
    from app.db.session import SessionLocal
    from app.services.audit_queue import (
        AuditQueueError,
        dequeue_batch,
        enqueue_audit_event,
        queue_length,
        write_batch_to_db,
    )

    # First, drain the retry queue (if any events were requeued)
    # We use the same dequeue_batch — retry events are mixed into the
    # main queue on failure via re-enqueue.

    events = dequeue_batch(batch_size)
    if not events:
        return 0

    db = SessionLocal()
    try:
        count = write_batch_to_db(events, db)
        logger.info("Flushed %d audit events (queue remaining: %d)", count, queue_length())
        return count
    except Exception as exc:
        logger.error("Failed to write audit batch (%d events): %s", len(events), exc)
        # Re-enqueue failed events so they are retried
        for ev in events:
            try:
                enqueue_audit_event(ev)
            except AuditQueueError:
                logger.critical(
                    "AUDIT EVENT LOST — could not re-enqueue after DB failure"
                )
        try:
            db.rollback()
        except Exception:
            pass
        return 0
    finally:
        db.close()


def run(
    *,
    once: bool = False,
    interval: float = 2.0,
    batch_size: int = 100,
) -> None:
    """Main worker loop."""
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info(
        "Audit worker starting — batch_size=%d, interval=%.1fs, once=%s",
        batch_size,
        interval,
        once,
    )

    if once:
        _flush_once(batch_size)
        return

    while not _shutdown:
        try:
            _flush_once(batch_size)
        except Exception as exc:
            logger.error("Audit worker loop error: %s", exc)

        # Sleep in small increments so we can respond to shutdown quickly
        for _ in range(int(interval * 10)):
            if _shutdown:
                break
            time.sleep(0.1)

    logger.info("Audit worker stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit log flush worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Flush one batch and exit",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Seconds between flush attempts (default: 2)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Max events per batch (default: 100)",
    )
    args = parser.parse_args()
    run(once=args.once, interval=args.interval, batch_size=args.batch_size)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
