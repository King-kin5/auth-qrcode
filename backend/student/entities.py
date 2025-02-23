
from enum import Enum


class Tier(Enum):
    STUDENT = "student"
    ADMIN = "admin"  # Added admin tier

class Status(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    SUSPENDED = "suspended"  # Added suspended status
    DELETED = "deleted"  