"""Shared test helpers."""

from PySide6.QtCore import QCoreApplication


def wait_for_worker(manager):
    """Wait for any background conversation worker to finish and deliver its signal."""
    if manager._worker is not None:
        manager._worker.wait(5000)
    QCoreApplication.processEvents()
