from django.shortcuts import render
from apps.common.models import Sales
from django.core import serializers


# Create your views here.

def index(request):
    filter_data = {}
    if from_date := request.GET.get('from'):
        filter_data['PurchaseDate__gte'] = from_date
    
    if to_date := request.GET.get('to'):
        filter_data['PurchaseDate__lte'] = to_date

    sales = serializers.serialize('json', Sales.objects.filter(**filter_data))
    context = {
        'segment'  : 'apex_charts',
        'parent'   : 'apps',
        'sales': sales
    }
    return render(request, 'apps/charts.html', context)
