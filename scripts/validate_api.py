import inspect
import logging
import os
import types
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import yaml

from playwright.sync_base import mapping

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


_dirname = Path(os.path.dirname(os.path.abspath(__file__)))


def _get_protocol() -> Dict[str, Any]:
    resp = requests.get(
        "https://raw.githubusercontent.com/microsoft/playwright/master/src/rpc/protocol.yml"
    )
    return yaml.load(resp.text, Loader=yaml.Loader)


def _validate(
    mapping: Dict[str, Any],
    class_name: str,
    py_class: Any,
    reference_class: Optional[Any] = None,
) -> None:
    if not reference_class:
        reference_class = py_class
    members = {k: v for k, v in inspect.getmembers(py_class)}
    if "commands" in mapping:
        for command in mapping["commands"]:
            if command not in members:
                logging.warning("%s.%s is not existing", class_name, command)
                continue
            if not isinstance(members[command], types.FunctionType):
                logging.warning("%s.%s has wrong function type", class_name, command)
                continue
    if "initializer" in mapping:
        for initializer in mapping["initializer"]:
            if initializer not in members:
                logging.warning("%s.%s is not existing", class_name, initializer)
                continue
            if not isinstance(members[initializer], property):
                logging.warning(
                    "%s.%s has wrong function type", class_name, initializer
                )
                continue

    if "events" in mapping:
        if not hasattr(reference_class, "Events"):
            logging.warning(
                "%s has no Events (%s is missing)",
                class_name,
                ",".join(mapping["events"].keys()),
            )
            return
        protocol_events = {v: k for k, v in vars(reference_class.Events).items()}
        for event in mapping["events"]:
            if event not in protocol_events:
                logging.warning("Event %s of %s is not existing", event, class_name)
                continue
            pass


def main() -> None:
    upstream_protocol = _get_protocol()
    for async_class, sync_class in mapping.mapping.items():
        class_name = async_class.__name__
        if class_name not in upstream_protocol:
            logger.warning("%s is not available in upstream protocol", class_name)
            continue
        protocol_mapping = upstream_protocol[class_name]
        _validate(protocol_mapping, f"Sync{class_name}", sync_class, async_class)
        _validate(protocol_mapping, class_name, async_class)


if __name__ == "__main__":
    main()
