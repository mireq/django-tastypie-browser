# -*- coding: utf-8 -*-
from django import template

register = template.Library()


@register.simple_tag
def set_url_parameter(url, **kwargs):
	return url
