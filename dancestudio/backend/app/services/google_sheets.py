from ..config import get_settings


def export_to_sheets(payload: dict) -> str:
    settings = get_settings()
    if not settings.google_sheets_enabled:
        return "Google Sheets integration disabled"
    # Заглушка: в реальной реализации использовался бы Google API client
    return f"Exported {len(payload.get('rows', []))} rows to Google Sheets"
