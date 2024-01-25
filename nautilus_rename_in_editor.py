import logging
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from typing import List
from urllib.parse import unquote, urlparse

from gi.repository import GObject, Nautilus


current_script = Path(__file__)

logger = logging.getLogger(__name__)


def config_log() -> None:
    # Logging to home for now, but eventually should be moved to a better place
    log_file = (Path.home() / current_script.name).with_suffix(".log")

    file_handler = logging.FileHandler(filename=log_file, delay=True)
    stdout_handler = logging.StreamHandler(stream=sys.stdout)

    formatter = logging.Formatter(logging.BASIC_FORMAT)
    file_handler.setFormatter(formatter)
    stdout_handler.setFormatter(formatter)

    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)


class RenameExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self) -> None:
        super().__init__()
        config_log()
        logger.debug(f"Initializing {current_script.stem}")

    def on_click(self, menu_item, files: List[Nautilus.FileInfo]) -> None:
        selected_files = []
        for file in files:
            p = unquote(urlparse(file.get_uri()).path)
            selected_files.append(p)

        plugin_name = "rename_in_editor.py"
        plugin_path = current_script.parent / plugin_name
        if not plugin_path.is_file():
            logger.critical(
                f"Did not found the plugin {plugin_name}, tried looking at {plugin_path}"
            )
            raise FileNotFoundError

        subprocess_args = [
            sys.executable,
            plugin_path,
            "--editor_command",
            "code",
            "--editor_args=--wait",
            "--files",
            *selected_files,
        ]

        # Do not wait for the process to return, since it requires human
        # intervention it will be slow, and while this function doesn't return
        # the menu will be stuck open.
        process = subprocess.Popen(subprocess_args)

        timeout = 0.1
        try:
            process.wait(timeout)
        except subprocess.TimeoutExpired:
            # Since the script expects human intervention, its improbable that
            # the subprocess will have finished in such a short amount of time,
            # so the timeout is the expected path.
            pass
        return_code = process.returncode

        if return_code is not None:
            logger.critical(
                dedent(
                    f"""\
                Subprocess returned before timeout of {timeout} seconds, that's too fast, something probably went wrong.
                Tried running subprocess {subprocess_args}, and it returned {return_code}
                """
                )
            )

    def get_file_items_full(
        self, provider, files: List[Nautilus.FileInfo]
    ) -> List[Nautilus.MenuItem]:
        top_menuitem = Nautilus.MenuItem(
            name="RenameExtension::Rename_in_text_editor",
            label="Rename in text editor",
            tip="",
            icon="",
        )

        top_menuitem.connect("activate", self.on_click, files)

        return [
            top_menuitem,
        ]
