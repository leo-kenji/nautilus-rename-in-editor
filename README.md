# nautilus-rename-in-editor

This extension adds a menu item in Nautilus which allows you to do a batch renaming of files in your text editor.

## Usage

To use the extension just select the files that you want to rename, right click and select `Rename in text editor`, then your text editor will open with the file paths for renaming.

The extension is conservative in the fact that in any error is found mid renaming, or detected before it, it will refuse to continue, exit and create a log, the logs are currently created in your home folder.

The extension never overwrite a file (unless an very specific case where the file is renamed externally in the time between the check for its existence and the actual renaming, this is very improbable).

The code is divided into two files, the extension "glue" to Nautilus, and the actual renaming logic. The renaming logic can be used as an stand alone script if you may wish for whatever reason, or adapt into an extension for other file managers (WARNING, this script will run unsanitized data passed by CLI, use it with care, the extension itself is safe).

## Dependencies

You will need to have nautilus-python installed on your system.

## Caveats

Currently the only editor supported is vscode, but more options will be supported, see [TODO](#todo).

This was only tested on Python 3.11 and Nautilus 45.2, it might not work in other versions.

This extension is not meant for enormous renaming, for this, you will probably be better off using the current Nautilus batch renaming, which can use regex for a more automated process.

## Installation

For now, you must place the `.py` files into the folders where scripts are loaded (i.e., `~/.local/share/nautilus-python/extensions` for local installation). See [nautilus-python #Running Extensions](https://gitlab.gnome.org/GNOME/nautilus-python#running-extensions) for a list of possible folders.

Then, reload nautilus by running

```bash
nautilus -q
```

and the script should be working.

## Uninstall

Remove the `.py` files from where you placed then during installation.

## Inspiration

This project was inspired by the batch renaming of the [nnn](https://github.com/jarun/nnn/tree/master) file manager.

## TODO

- [ ] Add installation script.
- [ ] Add AUR package.
- [ ] Finish typing extension file.
- [ ] Add support for localization.
- [ ] Add ability to configure the editor via dconf like in [nautilus-open-any-terminal](https://github.com/Stunkymonkey/nautilus-open-any-terminal).
- [ ] Add docstrings to files.
- [ ] Move log file location to more adequate place.
