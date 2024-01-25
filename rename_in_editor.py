import argparse
import logging
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from collections.abc import ItemsView
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Self

current_script = Path(__file__)


logger = logging.getLogger(__name__)


def mangled_path(path: Path) -> Path:
    return path.with_name(path.name + "_temp_name_" + str(hash(path)))


def safe_rename(current_path: Path, new_path: Path) -> None:
    if new_path.exists():
        raise FileExistsError(f"File {new_path} already exists")
    if current_path == new_path:
        return
    current_path.replace(new_path)


def config_log() -> None:
    # Logging to home for now, but eventually should be moved to a better place
    log_file = (Path.home() / current_script.name).with_suffix(".log")

    file_handler = logging.FileHandler(filename=log_file, delay=True)
    stdout_handler = logging.StreamHandler(stream=sys.stdout)

    formatter = logging.Formatter(logging.BASIC_FORMAT)
    file_handler.setFormatter(formatter)
    stdout_handler.setFormatter(formatter)

    logger.setLevel(logging.ERROR)
    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)


class EnumeratedFiles:
    def __init__(self, enumerated_files: dict[int, Path]) -> None:
        names_list = enumerated_files.values()
        names_set = set(names_list)
        if len(names_set) != len(names_list):
            raise ValueError("Repeated path detected, will not continue")

        self.__enumerated_files = enumerated_files

    @classmethod
    def from_list(cls, file_list: list[str | os.PathLike[Any]]) -> Self:
        enumerated_files = {}
        for i, file_path in enumerate(file_list):
            enumerated_files[i] = Path(file_path)
        return cls(enumerated_files)

    @classmethod
    def from_str(cls, text: str) -> Self:
        # Meaning of the Regex pattern:
        # Capture any non-negative integer number followed by ';', and
        # capturing the subsequent file path. Ignoring all white space before
        # and after the number, and before and after the filepath.
        regex_pattern = re.compile(r"(\d+)\s*;\s*(.*\S).*")

        enumerated_files = {}
        lines = text.split("\n")
        for line in lines:
            match = re.search(regex_pattern, line)
            if match is None:
                continue
            i = int(match.group(1))
            file_path = match.group(2)
            enumerated_files[i] = Path(file_path)

        return cls(enumerated_files)

    def same_keys(self, other: Self) -> bool:
        self_keys = set(self.__enumerated_files.keys())
        other_keys = set(other.__enumerated_files.keys())

        return self_keys == other_keys

    def has_collision(self, new_paths: Self, key: int) -> bool:
        temp = deepcopy(self)

        temp.__enumerated_files.pop(
            key
        )  # Ignore cases where there is no change in the name of the file

        return new_paths.__enumerated_files[key] in temp.__enumerated_files.values()

    def __getitem__(self, item: int) -> Path:
        return self.__enumerated_files[item]

    def items(self) -> ItemsView[int, Path]:
        return self.__enumerated_files.items()

    def __str__(self) -> str:
        out = ""
        for i, file_path in self.__enumerated_files.items():
            out += f"{i}; {file_path}\n"
        return out


@dataclass(frozen=True, kw_only=True)
class TempNameRecord:
    name: Path
    temp_name: Path


class RenamePlugin:
    @staticmethod
    def rename_files(
        original_paths: EnumeratedFiles, new_paths: EnumeratedFiles
    ) -> None:
        if not original_paths.same_keys(new_paths):
            raise KeyError(
                "Original paths and new paths don't have the same indexes, refusing to change files"
            )

        temp_names: list[TempNameRecord] = []
        for key, old_name in original_paths.items():
            new_name = new_paths[key]

            if new_name == old_name:
                continue

            if original_paths.has_collision(new_paths, key):
                temp_name = mangled_path(new_name)
                temp_names.append(TempNameRecord(name=new_name, temp_name=temp_name))
                new_name = temp_name

            safe_rename(old_name, new_name)

        # Undo name mangling
        for record in temp_names:
            safe_rename(record.temp_name, record.name)

    @staticmethod
    def logic(
        files: list[str | os.PathLike[Any]],
        writer: Callable[[str | os.PathLike[Any], str], None],
        reader: Callable[[str | os.PathLike[Any]], str],
        editor_command: str,
        editor_flags: str,
    ) -> None:
        original_paths = EnumeratedFiles.from_list(files)

        with tempfile.NamedTemporaryFile(mode="w+b") as fp:
            writer(fp.name, str(original_paths))

            # print([editor_command, fp.name, *editor_flags])
            try:
                subprocess.run(
                    [editor_command, fp.name, *(editor_flags.split())], check=True
                )
            except subprocess.CalledProcessError as e:
                exit_msg = f"Call to editor returned {e.returncode} instead of 0, refusing to change files"
                logger.exception(exit_msg)
                sys.exit(exit_msg)

            text = reader(fp.name)

        new_paths = EnumeratedFiles.from_str(text)

        try:
            RenamePlugin.rename_files(original_paths, new_paths)
        except (KeyError, FileExistsError) as e:
            logger.exception()
            exit(str(e))


def file_writer(file_path: str | os.PathLike[Any], text: str) -> None:
    with open(file_path, "w") as file:
        file.write(text)


def file_reader(file_path: str | os.PathLike[Any]) -> str:
    with open(file_path, mode="r") as f:
        text = f.read()
    return text


def parse_cli_args() -> argparse.Namespace:
    CLI = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Batch file renaming tool using an external text editor.",
        epilog=textwrap.dedent(
            f"""\
            Example usage:
                {current_script.name} --editor_command code --editor_args="--wait" --files file1 file 2
        """
        ),
    )

    CLI.add_argument(
        "--editor_command",
        type=str,
        required=True,
        help="Command to launch the external text editor.",
    )
    CLI.add_argument(
        "--editor_args",
        type=str,
        default="",
        help='Must be passed as a single string separated by spaces example and between quotes: --editor_args="--arg1 --arg2"',
        required=True,
    )
    CLI.add_argument(
        "--files",
        nargs="*",
        type=str,
        default=[],
        required=True,
        help="List of files to be renamed.",
    )

    args = CLI.parse_args()
    return args


def main() -> None:
    """
    Note that technically this allows for arbitrary code execution.
    """
    config_log()

    args = parse_cli_args()

    try:
        RenamePlugin.logic(
            args.files, file_writer, file_reader, args.editor_command, args.editor_args
        )
    except Exception:
        # Yeah, catching all exceptions since I'm not sure of what are all the
        # possible exceptions, eventually they should be handled separately.

        # Not very descriptive error message, but  it is accompanied by a
        # traceback, and eventually all kinks should be removed individually
        logger.exception("Something went wrong")


if __name__ == "__main__":
    main()
