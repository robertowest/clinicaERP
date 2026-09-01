from django import template

register = template.Library()

@register.simple_tag
def debug_breakpoint():
    breakpoint()
    return ''
