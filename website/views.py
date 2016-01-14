from django.shortcuts import render
from django.http import Http404,HttpResponseBadRequest,\
                    HttpResponseRedirect,HttpResponse
from django.contrib.auth.decorators import login_required

def homepage(request):
	return render(request, 'homepage.html')