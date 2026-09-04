def swiss_de(text: str) -> str:
    """Schweizer Hochdeutsch kennt kein 'ß' -- immer 'ss'."""
    return text.replace("ß", "ss") if text else text
