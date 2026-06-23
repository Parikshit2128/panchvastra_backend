from django.urls import path

from pv_app.api.src.user_panel import categories_management, products_management

urlpatterns = [
    path('categories_management/', categories_management, name='categories_management'),
    path('products_management/', products_management, name='products_management'),
]