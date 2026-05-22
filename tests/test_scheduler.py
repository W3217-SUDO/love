from app.scheduler import start_scheduler, stop_scheduler


def test_start_stop_scheduler_idempotent():
    """Start twice -> second is no-op. Stop twice -> second is no-op."""
    start_scheduler()
    try:
        start_scheduler()  # idempotent
    finally:
        stop_scheduler()
        stop_scheduler()  # idempotent


def test_scheduler_registers_expected_jobs():
    import app.scheduler as sched_module
    sched_module._scheduler = None  # ensure fresh
    sched_module.start_scheduler()
    try:
        jobs = sched_module._scheduler.get_jobs()
        ids = {j.id for j in jobs}
        assert "backup_db" in ids
        assert "mirror_uploads" in ids
        assert "cleanup_orphan_media" in ids
    finally:
        sched_module.stop_scheduler()
