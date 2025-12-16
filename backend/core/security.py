from uuid import UUID

# Hardcoded single user ID for local-first app
SINGLE_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

def get_current_user_id() -> str:
    """Stub for getting current user ID in single-user mode."""
    return str(SINGLE_USER_ID)
