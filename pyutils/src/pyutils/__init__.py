"""pyutils: small, general, dependency-free Python utilities.

Extracted from the sm2 project (retired 2026-07; see the drill repo's
llm/decisions.md ADR-059) so these modules can be imported by any local
project rather than living inside one application. Standard-library only.

Currently provides:
    terminal_output -- terminal formatting: width-aware alignment, styling,
                       cards, tables, separators, and leveled message output.

Import as:
    from pyutils import terminal_output
    from pyutils.terminal_output import emit, format_card
"""

from pyutils import terminal_output

__all__ = ["terminal_output"]
