from django.contrib import admin
from .models import Category, Product, Review
from .models import Cart, CartItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "brand",
        "category",
        "price",
        "stock",
        "rating",
    )

    list_filter = ("category", "brand", "rating")
    search_fields = ("name", "brand", "description")
admin.site.register(Review)

admin.site.register(Cart)
admin.site.register(CartItem)