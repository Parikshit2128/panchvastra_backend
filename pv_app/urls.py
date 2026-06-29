from django.urls import path

from pv_app.api.src.authentication import login_user, register_user, verify_email
from pv_app.api.src.user_panel import cart_management, categories_management, coupon_management, products_management

urlpatterns = [
    path('register_user/', register_user, name='register_user'),
    path('login_user/', login_user, name='login_user'),
    path('verify_email/', verify_email, name='verify_email'),
    path('categories_management/', categories_management, name='categories_management'),
    path('products_management/', products_management, name='products_management'),
    path('cart_management/', cart_management, name='cart_management'),
    path('coupon_management/', coupon_management, name='coupon_management'),
]