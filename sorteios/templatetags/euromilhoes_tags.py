"""
Template tags personalizados para EuroMilhões Analyzer.
"""
from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()


@register.filter
def format_currency(value):
    """Formata valor como moeda (€)."""
    if value is None:
        return "-"
    return f"€{intcomma(int(value))}"


@register.filter
def ball_format(value):
    """Formata número com dois dígitos."""
    try:
        return f"{int(value):02d}"
    except (ValueError, TypeError):
        return value
