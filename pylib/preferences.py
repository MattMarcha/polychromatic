#!/usr/bin/python3
#
# Polychromatic is licensed under the GPLv3.
# Copyright (C) 2015-2020 Luke Horwell <code@horwell.me>
#
"""
This module is responsible for loading/saving persistent data used by Polychromatic's frontends.
"""

import os
import json
import shutil
import time
from . import common

version = 7

dbg = common.Debugging()


class Paths(object):
    # Default directories
    root = os.path.join(os.path.expanduser("~"), ".config", "polychromatic")
    cache = os.path.join(os.path.expanduser("~"), ".cache", "polychromatic")

    # XDG directories
    try:
        root = os.path.join(os.environ["XDG_CONFIG_HOME"], ".config", "polychromatic")
    except KeyError:
        pass

    try:
        root = os.path.join(os.environ["XDG_CACHE_HOME"], ".cache", "polychromatic")
    except KeyError:
        pass

    # Subdirectories
    effects = os.path.join(root, "effects")
    profiles = os.path.join(root, "profiles")
    device_images = os.path.join(root, "device_images")
    custom_icons = os.path.join(root, "custom_icons")

    # Files
    preferences = os.path.join(root, "preferences.json")
    colours = os.path.join(root, "colours.json")

    # Deprecated (v0.3.12 and earlier)
    old_profiles = os.path.join(root, "profiles.json")
    old_profile_folder = os.path.join(root, "profiles")
    old_profile_backups = os.path.join(root, "backups")
    old_devicestate = os.path.join(root, "devicestate.json")


def load_file(filepath):
    """
    Loads a JSON file from disk. If empty, it will be created.

    Params:
        filepath            String from the Path() object.

    Returns:
        {}                  Data (dictionary object)
    """
    if os.path.exists(filepath):
        try:
            with open(filepath) as stream:
                data = json.load(stream)
        except Exception as e:
            dbg.stdout(filepath + ": Read error!", dbg.error)
            dbg.stdout("Exception:\n" + common.get_exception_as_string(e), dbg.error)
            init_config(filepath)
            data = {}
    else:
        init_config(filepath)
        data = {}

    # Check preferences contain valid data and defaults.
    def _validate(group, item, data_type, default_value):
        try:
            data[group]
        except KeyError:
            data[group] = {}

        try:
            data[group][item]
        except KeyError:
            data[group][item] = default_value
            save_file(path.preferences, data)

        if type(data[group][item]) != data_type:
            data[group][item] = default_value
            save_file(path.preferences, data)

    if filepath == path.preferences:
        _validate("colours", "primary", str, "#00FF00")
        _validate("colours", "secondary", str, "#FF0000")
        _validate("effects", "live_preview", bool, True)
        _validate("general", "landing_tab", str, "devices")
        _validate("tray", "force_legacy_gtk_status", bool, False)
        _validate("tray", "icon", str, "ui/img/tray/light/polychromatic.svg")

    return(data)


def save_file(filepath, newdata):
    """
    Commit data to the disk.

    Params:
        filepath            String from the Path() object.
        newdata             Data (dictionary object)

    Returns:
        True                Save successful.
        False               Save failed.
    """
    # The preferences file stores the configuration version.
    if filepath == path.preferences:
        newdata["config_version"] = version

    # Create file if it doesn't exist.
    if not os.path.exists(filepath):
        open(filepath, "w").close()

    # Write new data to file.
    if os.access(filepath, os.W_OK):
        f = open(filepath, "w+")
        f.write(json.dumps(newdata, sort_keys=True, indent=4))
        f.close()
        return True
    else:
        return False


def set(group, item, value, filepath=None):
    """
    Commits a new preference value, then saves it to disk.
    A different file can be optionally specified.
    """
    # If haven't explicitly stated which file, assume preferences.
    if filepath == None:
        filepath = path.preferences

    data = load_file(filepath)

    # In case a boolean was incorrectly passed as a string, correct the data type.
    if value == "true":
        value = True
    if value == "false":
        value = False

    # Create group if non-existent.
    try:
        data[group]
    except:
        data[group] = {}

    # Write new setting and save.
    try:
        data[group][item] = value
        save_file(filepath, data)
    except Exception:
        dbg.stdout("{3}: Write error! '{0}' for item '{1}' in group '{2}'".format(value, item, group, filepath), dbg.error)


def get(group, item, default_value="", filepath=None):
    """
    Read data from memory.
    """
    # If no file explicitly stated, assume preferences.
    if filepath == None:
        filepath = path.preferences

    data = load_file(filepath)
    value = data[group][item]
    return value


def exists(group, item, filepath=None):
    """
    Returns a boolean whether preference exists or not.
    """
    # If no file explicitly stated, assume preferences.
    if filepath == None:
        filepath = path.preferences

    data = load_file(filepath)

    # Read data from preferences.
    try:
        value = data[group][item]
        return True
    except:
        return False


def init_config(filepath):
    """
    Prepares a configuration file for the first time.
    """
    try:
        # Backup if the JSON was invalid.
        if os.path.exists(filepath):
            dbg.stdout(filepath + ": JSON corrupt or unreadable. It will backed up then recreated.", dbg.error)
            os.rename(filepath, filepath + ".bak")

        # Touch new file
        save_file(filepath, {})
        dbg.stdout(filepath + ": New configuration written.", dbg.success)

    except Exception as e:
        # Couldn't create the default configuration.
        dbg.stdout(filepath + ": Init write error!", dbg.error)
        dbg.stdout("Exception: ", str(e), dbg.error)


def upgrade_old_pref():
    """
    Checks and updates the configuration from previous revisions.
    """
    try:
        with open(path.preferences, "r") as f:
            data = json.load(f)
        config_version = int(data["config_version"])
    except Exception:
        # Never mind, the parent function should fix this later.
        return

    # Is the configuration version up-to-date?
    if version == config_version:
        return

    # Is the config newer then the software? Wicked time travelling!
    if config_version > version:
        dbg.stdout("\nWARNING: Your preferences file is newer then the application!", dbg.error)
        dbg.stdout("It's likely you're running an older version. This is unsupported.", dbg.error)
        dbg.stdout("     Current Config Version:   v." + str(config_version), dbg.error)
        dbg.stdout("     Installed Config Version: v." + str(version), dbg.error)
        dbg.stdout("")
        return

    dbg.stdout("Upgrading configuration from v{0} to v{1}...".format(config_version, version), dbg.action)

    # v0.3.12
    if config_version < 5:
        # Ensure preferences.json is clean.
        data = load_file(path.preferences)
        for key in ["activate_on_save", "live_switch", "live_preview"]:
            try:
                value = data["editor"][key]
                if type(value) == str:
                    if value in ['true', 'True']:
                        data["editor"][key] = True
                    else:
                        data["editor"][key] = False
            except Exception:
                pass

        save_file(path.preferences, data)

    # v0.4.0 (dev)
    if config_version == 6:
        # The configuration will be reset.
        dbg.stdout("Development configuration detected. Preferences have been reset.", dbg.warning)
        for filepath in [path.preferences, path.colours, path.old_devicestate]:
            if os.path.exists(filepath):
                os.remove(filepath)
        return

    # v1.0.0 (dev)
    if config_version < 7:
        # Migrate preferences.json to new keys
        old_data = load_file(path.preferences)

        # -- Tray icon is now one key (a relative or absolute path)
        new_tray_value = ""
        try:
            old_type = old_data["tray_icon"]["type"]
            if old_type == "gtk":
                new_tray_value = common.get_path_from_gtk_icon_name(old_data["tray_icon"]["value"])
            elif old_type == "custom":
                new_tray_value = old_data["tray_icon"]["value"]
            elif old_type == "builtin":
                try:
                    mapping = {
                        "0": "ui/img/tray/light/humanity.svg",
                        "1": "ui/img/tray/dark/humanity.svg",
                        "2": "ui/img/tray/animated/chroma.gif",
                        "3": "ui/img/tray/light/breeze.svg",
                        "4": "ui/img/tray/dark/breeze.svg"
                    }
                    new_tray_value = mapping[old_data["tray_icon"]["value"]]
                except KeyError:
                    # Invalid data, discard.
                    pass
        except KeyError:
            # Invalid data, discard.
            pass

        try:
            old_live_preview = old_data["editor"]["live_preview"]
        except KeyError:
            old_live_preview = False

        new_data = {
            "colours": {
                "primary": "#00FF00",               # New
                "secondary": "#00FFFF"              # New
            },
            "effects": {
                "live_preview": old_live_preview    # Changed
            },
            "tray": {
                "force_legacy_gtk_status": False,   # New
                "icon": new_tray_value              # Changed
            }
        }

        os.remove(path.preferences)
        save_file(path.preferences, new_data)

        # devicestate.json now obsolete
        if os.path.exists(path.old_devicestate):
            os.remove(path.old_devicestate)

        # If the colours were unchanged from v0.3.12, reset to new ones.
        old_colours = load_file(path.colours)
        old_colour_json = {
            "1": {"name": "White", "col": [255, 255, 255]},
            "2": {"name": "Red", "col": [255, 0, 0]},
            "3": {"name": "Orange", "col": [255, 165, 0]},
            "4": {"name": "Yellow", "col": [255, 255, 0]},
            "5": {"name": "Signature Green", "col": [0, 255, 0]},
            "6": {"name": "Aqua", "col": [0, 255, 255]},
            "7": {"name": "Blue", "col": [0, 0, 255]},
            "8": {"name": "Purple", "col": [128, 0, 128]},
            "9": {"name": "Pink", "col": [255, 0, 255]}
        }

        if old_colours == old_colour_json:
            os.remove(path.colours)
        else:
            # Migrate colours from RGB lists to HEX strings.
            new_colours = []
            if type(old_colours) != list:
                old_ids = list(old_colours.keys())
                old_ids.sort()
                for uuid in old_ids:
                    new_name = old_colours[uuid]["name"]
                    new_hex = common.rgb_to_hex(old_colours[uuid]["col"])
                    new_colours.append({"name": new_name, "hex": new_hex})

                save_file(path.colours, new_colours)



    # Write new version number.
    data = load_file(path.preferences)
    data["config_version"] = version
    save_file(path.preferences, data)

    dbg.stdout("Configuration successfully upgraded.", dbg.success)


def get_custom_icons():
    """
    Returns a list of all the icons currently stored in the user's "custom icons"
    folder. This is used by the icon picker. Save data will reference images
    by a relative file name.
    """
    return os.listdir(path.custom_icons)


# Module Initalization
def start_initalization():
    """
    Prepares the preferences module for use.
    """
    # Create folders if they do not exist.
    for folder in [path.root, path.effects, path.profiles, path.cache, path.device_images, path.custom_icons]:
        if not os.path.exists(folder):
            dbg.stdout("Configuration folder does not exist. Creating: " + folder, dbg.action)
            os.makedirs(folder)

    # Create preferences if non-existent.
    for json_path in [path.preferences]:
        if not os.path.exists(json_path):
            init_config(json_path)

    # Check the configuration and software version matches.
    upgrade_old_pref()

    # Populate with defaults if none exists.
    ## Default Preferences
    data = load_file(path.preferences)
    if len(data) <= 2:
        save_file(path.preferences, {})

    ## Default Colours
    data = load_file(path.colours)
    if len(data) <= 2:
        default_data = [
            {"name": _("White"), "hex": "#FFFFFF"},
            {"name": _("Red"), "hex": "#FF0000"},
            {"name": _("Green"), "hex": "#00FF00"},
            {"name": _("Blue"), "hex": "#0000FF"},
            {"name": _("Aqua"), "hex": "#00FFFF"},
            {"name": _("Orange"), "hex": "#FFA500"},
            {"name": _("Pink"), "hex": "#FF00FF"},
            {"name": _("Purple"), "hex": "#8000FF"},
            {"name": _("Yellow"), "hex": "#FFFF00"},
            {"name": _("Light Grey"), "hex": "#C0C0C0"},
            {"name": _("Dark Grey"), "hex": "#7F7F7F"},
            {"name": _("Black"), "hex": "#000000"}
        ]
        save_file(path.colours, default_data)


_ = common.setup_translations(__file__, "polychromatic")
path = Paths()
start_initalization()
