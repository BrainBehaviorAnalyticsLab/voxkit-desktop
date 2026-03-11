from voxkit.gui.workers.worker_thread import WorkerThread


class TestWorkerThread:
    def test_success_signal(self, qtbot):
        worker = WorkerThread(lambda: "all good")

        with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
            worker.start()
        worker.wait()

        success, message = blocker.args
        assert success is True
        assert message == "all good"

    def test_success_none_returns_default_message(self, qtbot):
        worker = WorkerThread(lambda: None)

        with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
            worker.start()
        worker.wait()

        success, message = blocker.args
        assert success is True
        assert message == "Operation completed successfully"

    def test_failure_signal_on_exception(self, qtbot):
        def failing():
            raise ValueError("something broke")

        worker = WorkerThread(failing)

        with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
            worker.start()
        worker.wait()

        success, message = blocker.args
        assert success is False
        assert "something broke" in message

    def test_failure_signal_on_runtime_error(self, qtbot):
        def bad_op():
            raise RuntimeError("fatal")

        worker = WorkerThread(bad_op)

        with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
            worker.start()
        worker.wait()

        success, message = blocker.args
        assert success is False
        assert "fatal" in message
