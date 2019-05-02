from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def readfilefield(field):
    """ Template filter for rendering data from a file field """
    with field.open('r') as f:
        return f.read()
