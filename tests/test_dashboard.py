from app.dashboard import _configure_utf8_output


class ReconfigurableStream:
    def __init__(self) -> None:
        self.options: dict[str, str] = {}

    def reconfigure(self, **kwargs: str) -> None:
        self.options = kwargs


def test_configure_utf8_output() -> None:
    stream = ReconfigurableStream()

    _configure_utf8_output(stream)  # type: ignore[arg-type]

    assert stream.options == {"encoding": "utf-8", "errors": "replace"}
