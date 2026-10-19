# SPDX-License-Identifier: GPL-3.0-or-later
"""Puppet Pose: rigged mannequin + pose & camera from a single photo."""

bl_info = {  # used only when installed as a legacy add-on
    "name": "Puppet Pose",
    "author": "Superside",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > Puppet",
    "description": "Rigged mannequin with fingers; copy pose and camera from a photo",
    "category": "Rigging",
}

from . import deps, operators, properties, ui  # noqa: E402

_modules = (properties, operators, ui)


def register():
    deps.ensure_path()
    for m in _modules:
        m.register()


def unregister():
    for m in reversed(_modules):
        m.unregister()
