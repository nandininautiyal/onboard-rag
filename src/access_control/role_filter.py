"""
role_filter.py

Defines Techify's role-based access rules for onboarding document
retrieval. Each employee role maps to the set of access_role tags
(from document frontmatter) they're allowed to see.

Every document in the corpus is tagged with one access_role value:
all, engineering, sales, finance, hr, marketing, or manager.
"all" documents are visible to everyone regardless of role.
"""

VALID_DOC_ACCESS_TAGS = {"all", "engineering", "sales", "finance", "hr", "marketing", "manager"}

# Maps a user's employee role to the set of document access_role tags
# they may retrieve, in addition to "all" (which everyone can see).
ROLE_ACCESS_MAP = {
    "engineering": {"all", "engineering"},
    "sales": {"all", "sales"},
    "finance": {"all", "finance"},
    "hr": {"all", "hr"},
    "marketing": {"all", "marketing"},
    "manager": {"all", "manager"},
}


def get_allowed_access_roles(user_role: str | None) -> set[str] | None:
    """
    Returns the set of document access_role tags a user with this role
    may retrieve.

    - Returns None if user_role is None -> no filtering applied
      (used for admin/testing contexts, or when access control is
      not relevant, e.g. running eval scripts against the full corpus).
    - Returns {"all"} if the role is unrecognized, as a safe default
      that doesn't accidentally over-expose restricted content.
    """
    if user_role is None:
        return None

    user_role = user_role.lower().strip()

    if user_role not in ROLE_ACCESS_MAP:
        print(f"WARNING: Unrecognized role '{user_role}' — defaulting to 'all'-only access")
        return {"all"}

    return ROLE_ACCESS_MAP[user_role]