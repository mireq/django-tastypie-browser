# -*- coding: utf-8 -*-
from django.template.loader import render_to_string
from django.core.serializers import json as djangojson
from django.core.urlresolvers import reverse
from django.utils.html import escape
import re


def patch_serializer():
	from tastypie.serializers import Serializer

	def to_json(self, data, options=None):
		options = options or {}
		to_html = options.pop("to_html", False)
		indent = None
		if to_html:
			indent = 2
		data = self.to_simple(data, options)

		data = djangojson.json.dumps(data, cls=djangojson.DjangoJSONEncoder, sort_keys=True, ensure_ascii=False, indent=indent)
		return data

	def to_html(self, data, options=None):
		if "resource" in options:
			return self.resource_to_html(data, options)
		else:
			return self.toplevel_to_html(data, options)

	def resource_to_html(self, data, options=None):
		options = options or {}
		resource = options['resource']
		request = options['request']
		content = escape(options['response'].content)
		content = re.sub(r'^(\s+&quot;[\w_-]+&quot;: &quot;)(/[a-z0-9/_-]+)(&quot;)', r'\1<a href="\2">\2</a>\3', content, flags=re.MULTILINE)
		api_name = resource._meta.api_name
		resource_name = resource._meta.resource_name

		path = request.path
		list_path = resource.get_resource_uri()

		breadcrumblist = []
		breadcrumblist.append(('API {0}'.format(api_name), reverse("api_{0}_top_level".format(api_name), kwargs={'api_name': api_name})))
		breadcrumblist.append((resource_name, list_path))
		if path != list_path:
			breadcrumblist.append((path.split("/")[-2], request.path))

		ctx = {
			'content': content,
			'request': request,
			'response': options['response'],
			'name': resource_name,
			'allowed_methods': [m.upper() for m in resource._meta.allowed_methods],
			'available_formats': self.formats,
			'breadcrumblist': breadcrumblist,
		}
		templates = (
			"tastypie_browser/api_{0}.html".format(resource_name),
			"tastypie_browser/api.html",
		)
		return render_to_string(templates, ctx)

	def toplevel_to_html(self, data, options=None):
		options = options or {}
		request = options['request']
		content = escape(options['response'].content)
		content = re.sub(r'^(\s+&quot;[\w_-]+&quot;: &quot;)(/[a-z0-9/_-]+)(&quot;)', r'\1<a href="\2">\2</a>\3', content, flags=re.MULTILINE)
		api_name = options['api'].api_name

		breadcrumblist = []
		breadcrumblist.append(('API {0}'.format(api_name), reverse("api_{0}_top_level".format(api_name), kwargs={'api_name': api_name})))

		ctx = {
			'content': content,
			'request': request,
			'response': options['response'],
			'name': api_name,
			'allowed_methods': ['get'],
			'available_formats': self.formats,
			'breadcrumblist': breadcrumblist,
		}
		templates = (
			"tastypie_browser/toplevel.html",
			"tastypie_browser/api.html",
		)
		return render_to_string(templates, ctx)


	def from_html(self, content):
		pass

	setattr(Serializer, "to_json", to_json)
	setattr(Serializer, "to_html", to_html)
	setattr(Serializer, "resource_to_html", resource_to_html)
	setattr(Serializer, "toplevel_to_html", toplevel_to_html)
	setattr(Serializer, "from_html", from_html)
