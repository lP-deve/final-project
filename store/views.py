
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Category, Product, Review, Cart, CartItem



@login_required(login_url="store:login")
@require_POST
def delete_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id)

    if review.user == request.user:
        product_id = review.product.id
        review.delete()
        messages.success(request, "თქვენი შეფასება წარმატებით წაიშალა!")
        return redirect("store:product_detail", product_id=product_id)

    messages.error(request, "თქვენ არ გაქვთ ამ შეფასების წაშლის უფლება.")
    return redirect("store:product_detail", product_id=review.product.id)




def home(request):
    products = Product.objects.select_related("category").all()
    categories = Category.objects.all().order_by("name")

    brands = (
        Product.objects.order_by("brand")
        .values_list("brand", flat=True)
        .distinct()
    )

    search = request.GET.get("q", "").strip()
    selected_category = request.GET.get("category", "").strip()
    selected_brand = request.GET.get("brand", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    min_rating = request.GET.get("rating", "").strip()

    if search:
        products = products.filter(
            Q(name__icontains=search)
            | Q(brand__icontains=search)
            | Q(description__icontains=search)
        )

    if selected_category:
        products = products.filter(category__slug=selected_category)

    if selected_brand:
        products = products.filter(brand=selected_brand)

    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except (InvalidOperation, ValueError):
            min_price = ""

    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except (InvalidOperation, ValueError):
            max_price = ""

    if min_rating:
        try:
            threshold = float(min_rating)
            products = [
                product for product in products
                if float(product.average_rating or 0) >= threshold
            ]
        except (ValueError, TypeError):
            min_rating = ""

    return render(request, "store/home.html", {
        "products": products,
        "categories": categories,
        "brands": brands,
        "search": search,
        "selected_category": selected_category,
        "selected_brand": selected_brand,
        "min_price": min_price,
        "max_price": max_price,
        "min_rating": min_rating,
    })




def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    reviews = product.reviews.all().order_by("-created_at")

    context = {
        "product": product,
        "reviews": reviews,
        "review_count": reviews.count(),
        "average_rating": product.average_rating,
    }

    return render(request, "store/product_detail.html", context)


# -------------------------
# ADD REVIEW
# -------------------------

@login_required(login_url="store:login")
@require_POST
def add_review(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    try:
        rating = int(request.POST.get("rating", 0))
    except (TypeError, ValueError):
        rating = 0

    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    comment = request.POST.get("comment", "").strip()

    if not 1 <= rating <= 5:
        messages.error(request, "Please choose a rating from 1 to 5.")

    elif not first_name or not last_name:
        messages.error(request, "Please enter your first and last name.")

    else:
        Review.objects.create(
            product=product,
            user=request.user,
            first_name=first_name,
            last_name=last_name,
            rating=rating,
            comment=comment,
        )

        messages.success(request, "Your review was submitted successfully!")

    return redirect("store:product_detail", product_id=product.id)


# -------------------------
# ADD TO CART
# -------------------------

@login_required(login_url="store:login")
@require_POST
def add_to_cart(request, product_id):

    with transaction.atomic():

        product = get_object_or_404(
            Product.objects.select_for_update(),
            pk=product_id
        )

        if product.stock < 1:
            messages.error(request, "Product is out of stock.")
            return redirect(
                "store:product_detail",
                product_id=product.id
            )

        cart, created = Cart.objects.get_or_create(
            user=request.user
        )

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": 0}
        )

        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            cart_item.save(update_fields=["quantity"])

            messages.success(request, "Product added to cart.")

        else:
            messages.error(request, "Not enough stock.")

    return redirect("store:cart")


# -------------------------
# CART PAGE
# -------------------------

@login_required(login_url="store:login")
def cart(request):

    user_cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    items = user_cart.items.select_related("product").all()

    total = sum(
        (item.subtotal for item in items),
        Decimal("0.00")
    )

    return render(request, "store/cart.html", {
        "items": items,
        "total": total,
    })



@login_required(login_url="store:login")
@require_POST
def update_cart(request, product_id):
    user_cart = get_object_or_404(Cart, user=request.user)

    cart_item = get_object_or_404(
        CartItem,
        cart=user_cart,
        product_id=product_id
    )

    action = request.POST.get("action")

    if action == "increase":

        if cart_item.quantity < cart_item.product.stock:
            cart_item.quantity += 1
            cart_item.save(update_fields=["quantity"])
            messages.success(request, "Quantity increased.")
        else:
            messages.error(request, "Not enough stock available.")

    elif action == "decrease":

        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save(update_fields=["quantity"])

    return redirect("store:cart")



@login_required(login_url="store:login")
@require_POST
def remove_from_cart(request, product_id):

    user_cart = get_object_or_404(
        Cart,
        user=request.user
    )

    cart_item = get_object_or_404(
        CartItem,
        cart=user_cart,
        product_id=product_id
    )

    cart_item.delete()

    messages.success(request, "Product removed from cart.")

    return redirect("store:cart")



@login_required(login_url="store:login")
def checkout(request):

    user_cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    items = list(
        user_cart.items.select_related("product").all()
    )

    if not items:
        messages.error(request, "Your cart is empty.")
        return redirect("store:cart")

    total = sum(
        (item.subtotal for item in items),
        Decimal("0.00")
    )

    if request.method == "POST":

        with transaction.atomic():

         
            for item in items:

                product = Product.objects.select_for_update().get(
                    pk=item.product_id
                )

                if product.stock < item.quantity:
                    messages.error(
                        request,
                        f"Not enough stock for {product.name}."
                    )
                    return redirect("store:cart")

      
            for item in items:

                product = Product.objects.select_for_update().get(
                    pk=item.product_id
                )

                product.stock -= item.quantity
                product.save(update_fields=["stock"])

            
            user_cart.items.all().delete()

        messages.success(request, "Your order was submitted successfully!")

        return render(request, "store/checkout.html", {
            "items": [],
            "total": total,
            "order_success": True,
        })

    return render(request, "store/checkout.html", {
        "items": items,
        "total": total,
    })




def register(request):

    if request.user.is_authenticated:
        return redirect("store:home")

    if request.method == "POST":

        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)

            return redirect("store:home")

    else:
        form = UserCreationForm()

    return render(
        request,
        "registration/register.html",
        {"form": form},
    )
