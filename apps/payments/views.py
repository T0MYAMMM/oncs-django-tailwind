from django.shortcuts import render
from apps.common.models import Sales
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import stripe


# Create your views here.
@login_required(login_url='/users/signin/')
def pricing_list(request):
    STRIPE_IS_ACTIVE = getattr(settings, 'STRIPE_IS_ACTIVE')

    context = {
        'segment': 'pricing',
        'parent': 'apps',
        'sales': Sales.objects.all(),
        'STRIPE_IS_ACTIVE': STRIPE_IS_ACTIVE
    }
    return render(request, 'apps/payments/pricing.html', context)


@login_required(login_url='/users/signin/')
def success(request):
    return render(request, "apps/payments/payment-success.html")

@login_required(login_url='/users/signin/')
def cancelled(request):
    return render(request, "apps/payments/payment-cancelled.html")

@login_required(login_url='/users/signin/')
def create_checkout_session(request, id):
    sales = Sales.objects.get(id=id)
    domain_url = getattr(settings, 'DOMAIN_URL')
    stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY')

    try:
        checkout_session = stripe.checkout.Session.create(
            success_url=domain_url + "payments/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=domain_url + "payments/cancelled",
            payment_method_types=["card"],
            mode="payment",
            line_items=[
                {
                    "name": sales.ItemName,
                    "quantity": 1,
                    "currency": 'usd',
                    "amount": int(float(sales.SalePriceUSD) * 100),
                },
            ],
        )

        return JsonResponse({"sessionId": checkout_session["id"]})
    
    except Exception as e:
        return JsonResponse(error=str(e)), 403
    

def get_publishable_key(request):
    stripe_config = {"publicKey": getattr(settings, 'STRIPE_PUBLISHABLE_KEY')}
    return JsonResponse(stripe_config)