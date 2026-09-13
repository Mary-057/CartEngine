import hmac
import hashlib
import json
import logging
import uuid
import requests
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from products.models import Product
from .models import Order, OrderItem, Cart, CartItem
from django.contrib import messages
from .tasks import process_paystack_webhook_async  # Import your background task

logger = logging.getLogger(__name__)

def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('product_list')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

@login_required
def cart_detail_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        action = request.POST.get('action')
        
        if item_id:
            cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
            
            if action == 'delete':
                cart_item.delete()
            else:
                new_quantity = request.POST.get('quantity')
                if new_quantity:
                    try:
                        qty = int(new_quantity)
                        if qty > 0:
                            cart_item.quantity = qty
                            cart_item.save()
                        else:
                            cart_item.delete()
                    except ValueError:
                        pass
        return redirect('cart_detail')

    cart_items = cart.items.select_related('product').all()
    cart_total = sum(item.product.price * item.quantity for item in cart_items)
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'cart_total': cart_total,
    }
    return render(request, 'orders/cart_detail.html', context)

@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, f"{product.name} added!")
        
    return redirect(request.META.get('HTTP_REFERER', 'product_list'))

@login_required
@require_POST
def checkout_view(request):
    user_cart = get_object_or_404(Cart, user=request.user)
    cart_items = user_cart.items.select_related('product').all()

    if not cart_items.exists():
        return redirect('cart_detail')

    paystack_ref = str(uuid.uuid4())
    total_amount = 0

    try:
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user, 
                status='PENDING',
                paystack_reference=paystack_ref
            )

            for item in cart_items:
                product = Product.objects.select_for_update().get(id=item.product.id)

                if product.stock < item.quantity:
                    transaction.set_rollback(True)
                    return redirect('out_of_stock')

                product.stock -= item.quantity
                product.save()

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price_at_purchase=product.price
                )

                total_amount += product.price * item.quantity

    except Exception as e:
        print("DATABASE ERROR OCCURRED:", str(e))
        logger.error(f"Checkout database error for user {request.user.id}: {str(e)}")
        return redirect('checkout_error')

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
    data = {
        "email": request.user.email or "customer@example.com",
        "amount": int(total_amount * 100),
        "reference": paystack_ref,
        "callback_url": request.build_absolute_uri(f"/orders/success/{order.id}/")
    }

    try:
        response = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=headers, timeout=30)
        res_data = response.json()
    except requests.exceptions.RequestException as e:
        print("NETWORK CONNECTION FAILED:", str(e))
        logger.error(f"Paystack network connection failed: {str(e)}")
        order.status = 'FAILED'
        order.save()
        return redirect('checkout_error')

    if res_data.get("status"):
        auth_url = res_data["data"]["authorization_url"]
        return redirect(auth_url)
    else:
        print("PAYSTACK REJECTED THIS BECAUSE:", res_data)
        order.status = 'FAILED'
        order.save()
        return redirect('checkout_error')

@login_required
def payment_success_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    receipt_items = order.items.select_related('product').all()
    
    total_amount = sum(item.price_at_purchase * item.quantity for item in receipt_items)
    
    if order.status == 'SUCCESS':
        return render(request, 'orders/success.html', {'order': order, 'receipt_items': receipt_items, 'total_amount': total_amount})

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }
    verify_url = f"https://api.paystack.co/transaction/verify/{order.paystack_reference}"
    
    try:
        response = requests.get(verify_url, headers=headers, timeout=30)
        res_data = response.json()
    except requests.exceptions.RequestException as e:
        print("VERIFICATION NETWORK FAILED:", str(e))
        logger.error(f"Paystack verification network failed: {str(e)}")
        return redirect('checkout_error')

    if res_data.get("status") and res_data["data"].get("status") == "success":
        order.status = 'SUCCESS'
        order.save()
        
        Cart.objects.filter(user=request.user).delete()
        
        return render(request, 'orders/success.html', {'order': order, 'receipt_items': receipt_items, 'total_amount': total_amount})
    else:
        print("PAYSTACK REJECTED VERIFICATION BECAUSE:", res_data)
        order.status = 'FAILED'
        order.save()
        return redirect('payment_failed')

@csrf_exempt
@require_POST
def paystack_webhook(request):
    paystack_signature = request.headers.get('X-Paystack-Signature')
    body = request.body
    
    computed_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        body,
        hashlib.sha512
    ).hexdigest()
    
    if not hmac.compare_digest(computed_signature, paystack_signature or ''):
        logger.warning("Invalid Paystack webhook signature detected!")
        return HttpResponse(status=400)
        
    event_data = json.loads(body)
    event = event_data.get('event')
    
    if event == 'charge.success':
        data = event_data.get('data', {})
        reference = data.get('reference')
        
        # Hand the execution off to Redis/Celery background worker instantly
        process_paystack_webhook_async.delay(reference)
            
    return HttpResponse(status=200)

@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-id')
    return render(request, 'orders/order_history.html', {'orders': orders})

def out_of_stock_view(request):
    return render(request, 'orders/out_of_stock.html')

def checkout_error_view(request):
    return render(request, 'orders/checkout_error.html')

def payment_failed_view(request):
    return render(request, 'orders/payment_failed.html')