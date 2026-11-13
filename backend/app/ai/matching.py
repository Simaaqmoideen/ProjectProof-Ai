"""app/ai/matching — re-exports the deterministic match and recommendation logic.

The actual implementation is in app/services/match_service.py.
This module exists so ai/ is self-contained (docs/06-ai-modules-specification.md).
"""

from app.services.match_service import MatchScoreService  # noqa: F401
