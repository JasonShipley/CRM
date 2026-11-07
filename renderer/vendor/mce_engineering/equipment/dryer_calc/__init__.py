"""MCE dryer calculator (Phase 1: rotary drum, complete; Phase 2: dryer type selector skeleton).

Engine and UI are separate: call `api.run(request_dict)` from the quote app or the
rotary-dryer-build agent; `report` renders the one-page PDF / HTML from the response.
"""

from .rotary import CALC_VERSION

__all__ = ["CALC_VERSION"]
