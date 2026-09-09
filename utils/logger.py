from __future__ import annotations

from logging import (
    getLogRecordFactory,
    setLogRecordFactory
)
from os import getpid
from psutil import Process
from coloredlogs import install

def setup():
    factory = getLogRecordFactory()

    def create_record(*args, **kwargs):
        record = factory(*args, **kwargs)
        try:
            proc = Process(getpid())
            ram = proc.memory_info().rss / 1024 / 1024
            cpu = proc.cpu_percent()
            record.ram = f"{ram:.2f} mb"
            record.cpu = f"{cpu:.1f}%"
        except Exception:
            record.ram = "0.00 mb"
            record.cpu = "0.0%"
        return record

    setLogRecordFactory(create_record)
    styles = {
        "info": {"color": "green"},
        "warning": {"color": "yellow"},
        "error": {"color": "red"}
    }
    install(
        level="INFO",
        fmt="%(asctime)s [%(ram)s | %(cpu)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        level_styles=styles
    )
