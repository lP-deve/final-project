from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .models import Review
from .models import Category, Product, Review


@login_required(login_url="store:login")
@require_POST
def delete_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id)

    if review.user == request.user:
        product_id = review.product.id
        review.delete()
        messages.success(request, "თქვენი შეფასება წარმატებით წაიშალა!")
        return redirect("store:product_detail", product_id=product_id)
    else:
        messages.error(request, "თქვენ არ გაქვთ ამ შეფასების წაშლის უფლება.")
        return redirect("store:product_detail", product_id=review.product.id)

def get_cart_count(request):
    cart_data = request.session.get("cart", {})
    count = 0

    for quantity in cart_data.values():
        try:
            count += max(0, int(quantity))
        except (TypeError, ValueError):
            continue

    return count


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
            products = products.filter(
                price__gte=Decimal(min_price)
            )
        except (InvalidOperation, ValueError):
            min_price = ""

    if max_price:
        try:
            products = products.filter(
                price__lte=Decimal(max_price)
            )
        except (InvalidOperation, ValueError):
            max_price = ""

    if min_rating:
        try:
            threshold = float(min_rating)
            products = [
                product
                for product in products
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
        "cart_count": get_cart_count(request),
    })


def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    reviews = product.reviews.all().order_by("-created_at")

    context = {
        "product": product,
        "reviews": reviews,
        "review_count": reviews.count(),
        "average_rating": product.average_rating,
        "cart_count": get_cart_count(request),
    }

    return render(request, "store/product_detail.html", context)
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


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    if product.stock < 1:
        messages.error(request, "This product is out of stock.")
        return redirect("store:product_detail", product_id=product.id)

    cart_data = request.session.get("cart", {})
    key = str(product.id)

    try:
        quantity = int(cart_data.get(key, 0))
    except (TypeError, ValueError):
        quantity = 0

    if quantity >= product.stock:
        messages.error(request, "You cannot add more than the available stock.")
    else:
        cart_data[key] = quantity + 1
        request.session["cart"] = cart_data
        request.session.modified = True
        messages.success(request, "Product added to your cart.")

    next_url = request.POST.get("next", "")

    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect("store:cart")


def cart(request):
    cart_data = request.session.get("cart", {})
    items = []
    total = Decimal("0.00")
    changed = False

    for product_id, raw_quantity in list(cart_data.items()):
        product = Product.objects.filter(pk=product_id).first()

        if product is None or product.stock < 1:
            cart_data.pop(product_id, None)
            changed = True
            continue

        try:
            quantity = int(raw_quantity)
        except (TypeError, ValueError):
            quantity = 1

        quantity = max(1, min(quantity, product.stock))

        if cart_data.get(product_id) != quantity:
            cart_data[product_id] = quantity
            changed = True

        subtotal = product.price * quantity
        total += subtotal

        items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal,
        })

    if changed:
        request.session["cart"] = cart_data
        request.session.modified = True

    return render(request, "store/cart.html", {
        "items": items,
        "total": total,
        "cart_count": sum(item["quantity"] for item in items),
    })


@require_POST
def update_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    cart_data = request.session.get("cart", {})
    key = str(product_id)

    if key not in cart_data:
        return redirect("store:cart")

    try:
        quantity = int(cart_data[key])
    except (TypeError, ValueError):
        quantity = 1

    action = request.POST.get("action")

    if action == "increase":
        if quantity < product.stock:
            cart_data[key] = quantity + 1
        else:
            messages.error(request, "You have reached the available stock limit.")

    elif action == "decrease":
        if quantity > 1:
            cart_data[key] = quantity - 1
        else:
            cart_data.pop(key, None)

    request.session["cart"] = cart_data
    request.session.modified = True

    return redirect("store:cart")


@require_POST
def remove_from_cart(request, product_id):
    cart_data = request.session.get("cart", {})
    cart_data.pop(str(product_id), None)

    request.session["cart"] = cart_data
    request.session.modified = True

    messages.success(request, "Product removed from cart.")
    return redirect("store:cart")


@login_required(login_url="store:login")
def checkout(request):
    cart_data = request.session.get("cart", {})

    if not cart_data:
        messages.error(request, "Your cart is empty.")
        return redirect("store:cart")

    items = []
    total = Decimal("0.00")

    for product_id, raw_quantity in cart_data.items():
        product = Product.objects.filter(pk=product_id).first()

        if product is None or product.stock < 1:
            continue

        try:
            quantity = int(raw_quantity)
        except (TypeError, ValueError):
            continue

        quantity = max(1, min(quantity, product.stock))

        subtotal = product.price * quantity
        total += subtotal

        items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal,
        })

    if not items:
        messages.error(request, "Your cart has no available products.")
        return redirect("store:cart")

    if request.method == "POST":
        request.session["cart"] = {}
        request.session.modified = True

        return render(request, "store/checkout.html", {
            "items": [],
            "total": total,
            "cart_count": 0,
            "order_success": True,
        })

    return render(request, "store/checkout.html", {
        "items": items,
        "total": total,
        "cart_count": get_cart_count(request),
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