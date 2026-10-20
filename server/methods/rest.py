"""Rest skeleton of the figure being posed.

Every fitting module reads the SAME dicts from here, so switching figure
(use("human") / use("mannequin")) changes the skeleton everywhere at once.
The rest pose must match the figure built in Blender for an exact transfer:
  mannequin -> assets/puppet_rest.json  (procedural wooden mannequin)
  human     -> assets/human_rest.json   (MHR human, tools/build_human.py)
"""

import json
import os
import threading

import numpy as np

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
FILES = {"mannequin": "puppet_rest.json", "human": "human_rest.json"}

REST = {}
PARENT = {}
TAIL = {}
LOCK = threading.RLock()     # fits are not re-entrant while the figure can change
current = None


def available():
    return [f for f, fn in FILES.items() if os.path.exists(os.path.join(ASSETS, fn))]


DEFAULT = os.environ.get("PUPPET_FIGURE") or ("human" if "human" in available() else "mannequin")


def use(figure=None):
    """Load the rest skeleton of `figure` (None -> default). Returns the name used."""
    global current
    figure = figure or DEFAULT
    if figure not in available():
        figure = "mannequin"
    if figure == current:
        return current
    with open(os.path.join(ASSETS, FILES[figure]), encoding="utf-8") as fh:
        d = json.load(fh)
    REST.clear()
    REST.update({k: np.array(v, dtype=np.float64) for k, v in d["rest"].items()})
    PARENT.clear()
    PARENT.update(d["parent"])
    TAIL.clear()
    TAIL.update(d["tail"])
    current = figure
    return current


use()
