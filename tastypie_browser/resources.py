# -*- coding: utf-8 -*-
def patch_resource():
	from tastypie.api import Api
	from tastypie.resources import Resource
	from tastypie.utils.mime import determine_format, build_content_type
	from django.http.response import HttpResponse

	old_serialize = Resource.serialize
	setattr(Resource, "old_serialize", old_serialize)

	def serialize(self, request, data, format, options=None):
		if format == 'text/html':
			options = options or {}
			options['request'] = request
			options['to_html'] = True
			options['resource'] = self

			options['response'] = HttpResponse(content=self.old_serialize(request, data, "application/json", options), content_type="application/json")
		return self.old_serialize(request, data, format, options)

	setattr(Resource, "serialize", serialize)

	old_top_level = Api.top_level
	setattr(Api, "old_top_level", old_top_level)

	def top_level(self, request, api_name=None):
		desired_format = determine_format(request, self.serializer)
		if 'text/html' in desired_format:
			available_resources = {}

			if api_name is None:
				api_name = self.api_name

			for name in sorted(self._registry.keys()):
				available_resources[name] = {
					'list_endpoint': self._build_reverse_url("api_dispatch_list", kwargs={
						'api_name': api_name,
						'resource_name': name,
					}),
					'schema': self._build_reverse_url("api_get_schema", kwargs={
						'api_name': api_name,
						'resource_name': name,
					}),
				}

			options = {
				'request': request,
				'to_html': True,
				'api': self,
			}
			options['response'] = HttpResponse(content=self.serializer.serialize(available_resources, "application/json", options), content_type="application/json")
			serialized = self.serializer.serialize(available_resources, desired_format, options)
			return HttpResponse(content=serialized, content_type=build_content_type(desired_format))
		else:
			return self.old_top_level(request, api_name)

	setattr(Api, "top_level", top_level)
