"""Privacy stage — enforce `internal_until_public_use_review` at publish time.

Every migrated record starts with `contact.public = False`: phone, email, and
address are held internal until a record is cleared for public use. The publish
step calls `Contact.public_string()`, which returns "" unless `public` is True,
so nothing internal leaks by default.

This module holds the *promotion* rules — the narrow, defensible cases where a
contact may be shown publicly — kept separate from the model so the policy is
easy to find and change. A contact is public only when it already appears in a
public-facing source (a farm's own website is the clearest case).
"""
from __future__ import annotations

from model import Farm


def clear_public_contact(farm: Farm) -> bool:
    """Mark a farm's contact public when it is defensibly already public.

    Rule: if the farm publishes its own website, its listed phone is public by
    the farm's own choice. Everything else stays internal pending review. This is
    intentionally conservative — widening it is a policy decision, not a default.
    Returns whether the contact was cleared.
    """
    if farm.contact.public:
        return True
    if farm.website and farm.contact.phone:
        farm.contact.public = True
        return True
    return False


def apply_privacy(farms: list[Farm]) -> dict[str, int]:
    cleared = sum(1 for f in farms if clear_public_contact(f))
    return {"contacts_public": cleared, "contacts_held_internal": len(farms) - cleared}
