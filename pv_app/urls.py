from django.urls import path

from pv_app.api.src.authentication import login_admin, login_user, register_user, user_profile, verify_email
from pv_app.api.src.user_panel import address_management, cart_management, categories_management, coupon_management, notify_me_management, orders, products_management, sub_categories_management

urlpatterns = [
    path('register_user/', register_user, name='register_user'),
    path('login_user/', login_user, name='login_user'),
    path('verify_email/', verify_email, name='verify_email'),
    path('user_profile/', user_profile, name='user_profile'),
    path('categories_management/', categories_management, name='categories_management'),
    path('sub_categories_management/', sub_categories_management, name='sub_categories_management'),
    path('products_management/', products_management, name='products_management'),
    path('cart_management/', cart_management, name='cart_management'),
    path('coupon_management/', coupon_management, name='coupon_management'),
    path('address_management/', address_management, name='address_management'),
    path('orders/', orders, name='orders'),
    path('notify_me/', notify_me_management, name='notify_me_management'),

    #Admin Panel APIs
    path('login_admin/', login_admin, name='login_admin'),
]