from django.urls import path
from django.shortcuts import render

def transparency_page(request):
    return render(request, 'legal/transparency.html')

urlpatterns = [
    path('', transparency_page, name='transparency'),
]
