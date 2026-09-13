from django.urls import path
from orders import views

urlpatterns = [
    path('cart/', views.cart_detail_view, name='cart_detail'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('success/<int:order_id>/', views.payment_success_view, name='payment_success'),
    path('webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),
    path('history/', views.order_history_view, name='order_history'),
    path('out-of-stock/', views.out_of_stock_view, name='out_of_stock'),
    path('error/', views.checkout_error_view, name='checkout_error'),
    path('failed/', views.payment_failed_view, name='payment_failed'),
]
