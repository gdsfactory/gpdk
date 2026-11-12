"""Cross-section factories re-exported from gdsfactory core.

gpdk does not vendor its own copy of the cross-sections; it re-exports the
canonical gdsfactory cross-sections so samples and routing code can import
them from ``gpdk.cross_section``.
"""

from gdsfactory.cross_section import *  # noqa: F403
from gdsfactory.cross_section import cross_sections  # noqa: F401
