from datetime import datetime

def format_date(value, format):
    """Format a date."""
    if value is None:
        return ""
    else:
        old_format = '%Y-%m-%d'
        new_format = '%d %B %Y'
        if format == 'full':
            return datetime.strptime(value, old_format).strftime(new_format)

def format_time(value, format):
    """Format a time."""
    if value is None:
        return ""
    else:
        old_format = '%H:%M:%S'
        new_format = '%I %p'
        if format == '12':
            return datetime.strptime(
                value, old_format
            ).strftime(new_format).lstrip("0").replace(" 0", " ")
