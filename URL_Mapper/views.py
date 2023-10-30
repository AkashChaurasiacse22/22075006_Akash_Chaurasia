from django.shortcuts import render, redirect
from django.core.exceptions import ObjectDoesNotExist
from .models import URL
import shortuuid
from .forms import URL_Form
from .utils import generate_short_url
# Create your views here.

def shorten_url(request):
    if request.method == "POST":
        form=URL_Form(request.POST)
        if form.is_valid():
            Long_url=form.cleaned_data['Long_url']
            try:
                My_object=URL.objects.get(Long_url=Long_url)
            except URL.DoesNotExist:
                My_object=None
            if My_object:
                url_instance=URL.objects.get(Long_url=Long_url)
            else:
                url_instance=URL.objects.create(Long_url=Long_url)
                url_instance.Short_url=generate_short_url(Long_url)
                url_instance.save()
            return render(request, 'URL_Mapper/results.html', {'Short_url': url_instance.Short_url})
    else:
        form=URL_Form()
    return render(request,'URL_Mapper/Shorten.html', {'form':form})

def redirect_url(request, Short_url):
    try:
        url_instance=URL.objects.get(Short_url=Short_url)
        return redirect(url_instance.Long_url)
    except URL.DoesNotExist:
        return render(request, 'URL_Mapper/Not_Found.html')

def Show_List(request):
    My_Objects=URL.objects.all()
    if not My_Objects:
        return render(request, 'URL_Mapper/No_List.html')
    else:
        return render(request, 'URL_Mapper/List.html', {"My_Object": My_Objects})
