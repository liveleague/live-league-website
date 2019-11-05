from datetime import datetime

def format_date(value, format):
    """Format a date."""
    if value is None:
        return ''
    else:
        old_format = '%Y-%m-%d'
        if format == 'full':
            return datetime.strptime(value, old_format).strftime('%d %B %Y')
        if format == 'small':
            return datetime.strptime(value, old_format).strftime('%b %d')

def format_time(value, format):
    """Format a time."""
    if value is None:
        return ''
    else:
        old_format = '%H:%M:%S'
        if format == '12':
            new_format = '%I:%M %p'
            return datetime.strptime(
                value, old_format
            ).strftime(new_format).lstrip("0").replace(" 0", " ")

def format_datetime(value, format):
    """Format a datetime."""
    if value is None:
        return ''
    else:
        old_format = '%Y-%m-%dT'