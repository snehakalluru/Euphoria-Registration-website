import re


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def normalize_team_name(value: str) -> str:
    return normalize_spaces(value).casefold()


def normalize_email(value: str) -> str:
    return value.strip().casefold()


def normalize_phone(value: str) -> str:
    return re.sub(r"[^0-9+]", "", value.strip())


def normalize_identifier(value: str) -> str:
    return normalize_spaces(value).upper()