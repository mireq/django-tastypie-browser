# -*- coding: utf-8 -*-
from tastypie.resources import Resource
from tastypie.exceptions import ImmediateHttpResponse
from django.http.response import HttpResponse, HttpResponseRedirect
from django.db import transaction
from django.template.response import TemplateResponse


def patch_resource():
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

	@transaction.atomic
	def dispatch(self, request_type, request, **kwargs):
		dummy = request.body
		if request.method == "POST":
			if "_method" in request.POST:
				request.method = request.POST["_method"]
				request.META['HTTP_X_CSRFTOKEN'] = request.POST.get('csrfmiddlewaretoken', '')
				try:
					self.old_dispatch(request_type, request, **kwargs)
				except ImmediateHttpResponse as e:
					ctx = {
						'response': e.response,
						'request': request,
						'request_type': request_type,
					}
					response = TemplateResponse(request, "tastypie_browser/error.html", ctx)
					response.status_code = e.response.status_code
					return response
				return HttpResponseRedirect(request.META['PATH_INFO'])
		return self.old_dispatch(request_type, request, **kwargs)

	setattr(Resource, "serialize", serialize)
	setattr(Resource, "old_dispatch", Resource.dispatch)
	setattr(Resource, "dispatch", dispatch)
