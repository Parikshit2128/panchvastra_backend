from django.urls import path

from pv_app.api.src.custom import custom_options, custom_requests
from pv_app.api.src.support import submit_support_query, support_queries_management
from pv_app.api.src.authentication import google_login, login_admin, login_user, register_user, user_profile, verify_email
from pv_app.api.src.user_panel import address_management, order_address, order_invoice, order_notes, auth_carousel, cart_management, categories_management, coupon_management, notify_me_management, orders, products_management, sub_categories_management

urlpatterns = [
    path('register_user/', register_user, name='register_user'),
    path('login_user/', login_user, name='login_user'),
    path('google_login/', google_login, name='google_login'),
    path('verify_email/', verify_email, name='verify_email'),
    path('user_profile/', user_profile, name='user_profile'),
    path('auth_carousel/', auth_carousel, name='auth_carousel'),
    path('categories_management/', categories_management, name='categories_management'),
    path('sub_categories_management/', sub_categories_management, name='sub_categories_management'),
    path('products_management/', products_management, name='products_management'),
    path('cart_management/', cart_management, name='cart_management'),
    path('coupon_management/', coupon_management, name='coupon_management'),
    path('address_management/', address_management, name='address_management'),
    path('orders/', orders, name='orders'),
    path('orders/invoice/', order_invoice, name='order_invoice'),
    path('orders/notes/', order_notes, name='order_notes'),
    path('orders/address/', order_address, name='order_address'),
    path('notify_me/', notify_me_management, name='notify_me_management'),
    path('support_query/', submit_support_query, name='submit_support_query'),
    path('support_queries/', support_queries_management, name='support_queries_management'),
    path('custom_options/', custom_options, name='custom_options'),
    path('custom_requests/', custom_requests, name='custom_requests'),

    #Admin Panel APIs
    path('login_admin/', login_admin, name='login_admin'),
]