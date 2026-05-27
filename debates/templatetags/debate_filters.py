from django import template

from debates.markdown_utils import (
    render_debate_markdown_html,
)


register = template.Library()


@register.filter(
    name='render_markdown',
)
def render_markdown(
    value: str,
) -> str:

    return render_debate_markdown_html(value)
