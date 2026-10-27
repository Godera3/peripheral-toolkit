"""
headset
=======
Shared driver package for the Razer Barracuda X Chroma.

Imported directly by the CLI (and later the GUI)::

    from headset import core
    core.get_battery()
    core.set_eq("movie")
    core.set_lights_off()
"""
from . import core, device, protocol
