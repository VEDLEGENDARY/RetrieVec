import threading
import unittest
from unittest.mock import MagicMock

import psycopg
from retrievec.registry.supervisor import serve_worker


class WorkerSupervisorTests(unittest.TestCase):
    def test_lost_database_session_closes_before_reacquisition(self):
        stopped = threading.Event()
        events = []
        registry = MagicMock()

        def connect():
            events.append("connect")
            session = MagicMock()
            session.__enter__.return_value = session
            session.execute.return_value.fetchone.return_value = {"acquired": True}
            session.__exit__.side_effect = lambda *_: events.append("closed")
            return session

        registry.connect.side_effect = connect
        attempts = 0

        def tick():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise psycopg.OperationalError("connection lost")
            stopped.set()
            return True

        stop = MagicMock()
        stop.is_set.side_effect = stopped.is_set
        stop.wait.side_effect = lambda seconds: events.append(("wait", seconds))
        serve_worker(registry, 7823403, tick, stop=stop)
        self.assertEqual(attempts, 2)
        self.assertEqual(events, ["connect", "closed", ("wait", 1), "connect", "closed"])

    def test_another_worker_owns_guard_without_running_work(self):
        registry, tick = MagicMock(), MagicMock()
        guard = registry.connect.return_value.__enter__.return_value
        guard.execute.return_value.fetchone.return_value = {"acquired": False}
        with self.assertRaises(SystemExit):
            serve_worker(registry, 7823402, tick)
        tick.assert_not_called()

    def test_programming_errors_are_not_retried(self):
        registry = MagicMock()
        guard = registry.connect.return_value.__enter__.return_value
        guard.execute.return_value.fetchone.return_value = {"acquired": True}
        tick = MagicMock(side_effect=ValueError("invalid configuration"))
        with self.assertRaises(ValueError):
            serve_worker(registry, 7823403, tick)
        self.assertEqual(tick.call_count, 1)
