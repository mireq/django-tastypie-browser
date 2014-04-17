# -*- coding: utf-8 -*-
import re

from django.core.serializers import json as djangojson
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.html import escape
from tastypie import api
from tastypie.serializers import Serializer


class ApiSerializer(Serializer):
	def to_html(self, data, options=None):
		options = options or {}
		options['api'] = getattr(self, "api")
		return super(ApiSerializer, self).to_html(data, options)


class HtmlApi(api.Api):
	def __init__(self, api_name="v1", serializer_class=ApiSerializer):
		super(HtmlApi, self).__init__(api_name=api_name, serializer_class=serializer_class)
		setattr(self.serializer, 'api', self)

	def top_level(self, request, api_name=None):
		setattr(self, "_request", request)
		response = super(HtmlApi, self).top_level(request, api_name)
		if hasattr(self, "_request"):
			delattr(self, "_request")
		return response


def patch_serializer():
	link_re = re.compile(r'^(\s+&quot;[\w_-]+&quot;: &quot;)(/[a-z0-9/_-]+)(&quot;)', flags=re.MULTILINE)

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
		if "api" in options:
			return self.toplevel_to_html(data, options)
		else:
			return self.resource_to_html(data, options)

	def resource_to_html(self, data, options=None):
		options = options or {}
		resource = options['resource']
		request = options['request']
		content = escape(options['response'].content)
		content = link_re.sub(r'\1<a href="\2">\2</a>\3', content)
		resource_options = getattr(resource, "_meta")
		api_name = resource_options.api_name
		resource_name = resource_options.resource_name

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
			'allowed_methods': [m.upper() for m in resource_options.allowed_methods],
			'available_formats': self.formats,
			'breadcrumblist': breadcrumblist,
			'data': data
		}
		templates = (
			"tastypie_browser/api_{0}.html".format(resource_name),
			"tastypie_browser/api.html",
		)
		return render_to_string(templates, ctx)

	def toplevel_to_html(self, data, options=None):
		options = options or {}
		api_instance = options['api']
		api_name = api_instance.api_name
		serializer = api_instance.serializer

		breadcrumblist = []
		breadcrumblist.append(('API {0}'.format(api_name), reverse("api_{0}_top_level".format(api_name), kwargs={'api_name': api_name})))

		content = escape(serializer.serialize(data, 'application/json', {'to_html': True}))
		content = self.link_re.sub(r'\1<a href="\2">\2</a>\3', content)
		ctx = {
			'name': api_name,
			'breadcrumblist': breadcrumblist,
			'data': data,
			'content': content,
			'request': getattr(api_instance, "_request", None)
		}
		templates = (
			"tastypie_browser/toplevel.html",
			"tastypie_browser/api.html",
		)
		return render_to_string(templates, ctx)

	setattr(Serializer, "to_json", to_json)
	setattr(Serializer, "to_html", to_html)
	setattr(Serializer, "resource_to_html", resource_to_html)
	setattr(Serializer, "toplevel_to_html", toplevel_to_html)
	setattr(Serializer, "link_re", link_re)
	setattr(api, "Api", HtmlApi)
