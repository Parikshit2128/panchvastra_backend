from django.urls import path

from pv_app.api.src.user_panel import cart_management, categories_management, coupon_management, products_management

urlpatterns = [
    path('categories_management/', categories_management, name='categories_management'),
    path('products_management/', products_management, name='products_management'),
    path('cart_management/', cart_management, name='cart_management'),
    path('coupon_management/', coupon_management, name='coupon_management'),
]