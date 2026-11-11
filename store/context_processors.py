from .models import Cart


def cart_count(request):
    if not request.user.is_authenticated:
        return {"cart_count": 0}

    user_cart = Cart.objects.filter(user=request.user).first()

    if user_cart:
        count = sum(
            item.quantity for item in user_cart.items.all()
        )
    else:
        count = 0

    return {"cart_count": count}