class APIError(Exception):
    """A safe, public error independent of the executable application module."""

    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message
