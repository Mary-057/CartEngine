from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from orders.views import signup_view, add_to_cart
from products.views import product_list_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/signup/', signup_view, name='signup'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    path('', product_list_view, name='product_list'),
    path('add-to-cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    
    path('orders/', include('orders.urls')),
]