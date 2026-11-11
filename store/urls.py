from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = "store"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/<int:product_id>/", views.product_detail, name="product_detail"),
    path("products/<int:product_id>/review/", views.add_review, name="add_review"),
    path("cart/", views.cart, name="cart"),

path(
    "cart/add/<int:product_id>/",
    views.add_to_cart,
    name="add_to_cart"
),

path(
    "cart/update/<int:product_id>/",
    views.update_cart,
    name="update_cart"
),

path(
    "cart/remove/<int:product_id>/",
    views.remove_from_cart,
    name="remove_from_cart"
),
    path("checkout/", views.checkout, name="checkout"),
    path("register/", views.register, name="register"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    
    path("review/<int:review_id>/delete/", views.delete_review, name="delete_review"),
]
