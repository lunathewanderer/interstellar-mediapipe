"""One reader thread drains the webcam; inference consumes only its latest frame."""
import threading


class LatestFrameCapture:
    def __init__(self, capture):
        self.capture = capture
        self.condition = threading.Condition()
        self.stop = threading.Event()
        self.sequence = self.consumed = 0
        self.frame = None
        self.failed = False
        self.thread = threading.Thread(target=self._run, name='GalaxyWebcam', daemon=True)
        self.thread.start()

    def _run(self):
        try:
            while not self.stop.is_set():
                ok, frame = self.capture.read()
                with self.condition:
                    if not ok:
                        self.failed = True
                        self.condition.notify_all()
                        break
                    self.frame = frame
                    self.sequence += 1
                    self.condition.notify_all()
        finally:
            # Release on the same thread that reads; no concurrent camera calls.
            self.capture.release()
            with self.condition:
                self.failed = True
                self.condition.notify_all()

    def read(self):
        with self.condition:
            ready = self.condition.wait_for(
                lambda: self.sequence != self.consumed or self.failed or self.stop.is_set(), timeout=3.)
            if not ready or self.sequence == self.consumed:
                return False, None
            self.consumed = self.sequence
            return True, self.frame.copy()

    def release(self):
        self.stop.set()
        with self.condition:
            self.condition.notify_all()
        self.thread.join(timeout=3.)
