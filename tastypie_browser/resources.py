# -*- coding: utf-8 -*-
def patch_resource():
	from tastypie.resources import Resource
	from django.http.response import HttpResponse

	old_serialize = Resource.serialize
	setattr(Resource, "old_serialize", old_serialize)

	def serialize(self, request, data, format, options=None): # pylint: disable=W0622
		if format == 'text/html':
			options = options or {}
			options['request'] = request
			options['to_html'] = True
			options['resource'] = self

			options['response'] = HttpResponse(content=self.old_serialize(request, data, "application/json", options), content_type="application/json")
		return self.old_serialize(request, data, format, options)

	setattr(Resource, "serialize", serialize)
