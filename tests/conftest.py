import json
from pathlib import Path

import pytest

from sts_bot.protocol import Message

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def load_message():
    """Load a recorded message from tests/fixtures/<name>.json."""

    def load(name: str) -> Message:
        data = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
        return Message.from_dict(data)

    return load
