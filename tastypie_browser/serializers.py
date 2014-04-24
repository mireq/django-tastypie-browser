# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

from django.core.serializers import json as djangojson
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.html import escape
from django.core.urlresolvers import resolve
from django.conf import settings
from urlparse import parse_qs
from django.utils.encoding import force_text
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
		url_info = resolve(request.path_info)

		breadcrumblist = []
		breadcrumblist.append(('API {0}'.format(api_name), reverse("api_{0}_top_level".format(api_name), kwargs={'api_name': api_name})))
		breadcrumblist.append((resource_name, resource.get_resource_uri()))
		if path != resource.get_resource_uri():
			breadcrumblist.append((path.split("/")[-2], path))

		ctx = {
			'content': content,
			'request': request,
			'response': options['response'],
			'name': resource_name,
			'allowed_methods': [m.upper() for m in resource_options.allowed_methods],
			'available_formats': [f for f in self.formats if hasattr(self, 'to_' + f)],
			'breadcrumblist': breadcrumblist,
			'data': data,
			'url_info': url_info,
			'content_types': dict(ct for ct in self.content_types.iteritems() if hasattr(self, 'from_' + ct[0]) and ct[0] in self.formats),
			'default_method': 'PATCH' if url_info.url_name == 'api_dispatch_detail' else 'POST',
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

	def from_urlencode(self, data, options=None):
		options = options or {}
		encoding = options.get("charset", settings.DEFAULT_CHARSET)
		qs = dict((force_text(k, encoding, errors='replace'), force_text(v, encoding, errors='replace') if len(v)>1 else v[0]) for k, v in parse_qs(str(data)).iteritems())
		if "_content_type" in qs:
			ctype = qs['_content_type']
			raw_data = qs['raw_data']
			if ctype.split(";")[0] != 'application/x-www-form-urlencoded':
				return self.deserialize(raw_data, ctype)
		return qs

	Serializer.content_types.update({'urlencode': 'application/x-www-form-urlencoded'})
	setattr(Serializer, "to_json", to_json)
	setattr(Serializer, "to_html", to_html)
	setattr(Serializer, "from_urlencode", from_urlencode)
	setattr(Serializer, "resource_to_html", resource_to_html)
	setattr(Serializer, "toplevel_to_html", toplevel_to_html)
	setattr(Serializer, "link_re", link_re)
	setattr(api, "Api", HtmlApi)
