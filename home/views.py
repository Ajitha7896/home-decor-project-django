from django.shortcuts import render, redirect
from django.http import Http404
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator

from .models import (
    Product,
    CustomerProfile,
    Coupon,
    ProductReview,
    Wishlist,
    Order,
    OrderItem,
    ContactMessage
)


DELIVERY_FEE = 50


def get_product_by_id(product_id):
    try:
        return Product.objects.get(id=product_id, is_available=True)
    except Product.DoesNotExist:
        return None


def user_can_access_order(request, order):
    if request.user.is_staff or request.user.is_superuser:
        return True

    if order.user == request.user:
        return True

    if order.email == request.user.email:
        return True

    return False


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('register')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        CustomerProfile.objects.create(user=user)

        messages.success(request, "Registration successful. Please login.")
        return redirect('login')

    return render(request, 'home/register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    next_url = request.GET.get('next', '')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        next_url = request.POST.get("next", "")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            messages.success(request, "Login successful.")

            CustomerProfile.objects.get_or_create(user=user)

            if next_url:
                return redirect(next_url)

            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('login')

    return render(request, 'home/login.html', {
        "next": next_url
    })


def logout_view(request):
    auth_logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('home')


@login_required
def profile(request):
    profile, created = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")

        if User.objects.filter(email=email).exclude(id=request.user.id).exists():
            messages.error(request, "This email is already used by another account.")
            return redirect('profile')

        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.email = email
        request.user.save()

        profile.phone = phone
        profile.address = address
        profile.save()

        messages.success(request, "Profile updated successfully.")
        return redirect('profile')

    return render(request, 'home/profile.html', {
        "profile": profile
    })


@login_required
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('change_password')

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('change_password')

        if len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return redirect('change_password')

        request.user.set_password(new_password)
        request.user.save()

        update_session_auth_hash(request, request.user)

        messages.success(request, "Password changed successfully.")
        return redirect('profile')

    return render(request, 'home/change_password.html')


def home(request):
    featured_products = Product.objects.filter(is_available=True)[:4]

    return render(request, 'home/index.html', {
        "featured_products": featured_products
    })


def about(request):
    return render(request, 'home/about.html')


def products(request):
    search_query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    sort_by = request.GET.get('sort', '')

    product_list = Product.objects.filter(is_available=True)

    if search_query:
        product_list = product_list.filter(name__icontains=search_query)

    if category:
        product_list = product_list.filter(category=category)

    if sort_by == 'price_low':
        product_list = product_list.order_by('price')
    elif sort_by == 'price_high':
        product_list = product_list.order_by('-price')
    elif sort_by == 'name':
        product_list = product_list.order_by('name')
    else:
        product_list = product_list.order_by('-created_at')

    paginator = Paginator(product_list, 8)
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)

    categories = ['Living Room', 'Bedroom', 'Dining Room', 'Chairs']

    return render(request, 'home/products.html', {
        "products": products_page,
        "search_query": search_query,
        "selected_category": category,
        "categories": categories,
        "sort_by": sort_by
    })


def product_detail(request, product_id):
    product = get_product_by_id(product_id)

    if product is None:
        raise Http404("Product not found")

    reviews = product.reviews.all().order_by('-created_at')
    user_review = None

    if request.user.is_authenticated:
        user_review = ProductReview.objects.filter(
            product=product,
            user=request.user
        ).first()

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.path)

        if user_review:
            messages.error(request, "You have already reviewed this product.")
            return redirect('product_detail', product_id=product.id)

        rating = request.POST.get("rating")
        review_text = request.POST.get("review")

        ProductReview.objects.create(
            product=product,
            user=request.user,
            rating=rating,
            review=review_text
        )

        messages.success(request, "Thank you for your review.")
        return redirect('product_detail', product_id=product.id)

    return render(request, 'home/product_detail.html', {
        "product": product,
        "reviews": reviews,
        "user_review": user_review
    })


def add_to_cart(request, product_id):
    product = get_product_by_id(product_id)

    if product is None:
        raise Http404("Product not found")

    if product.stock <= 0:
        return redirect('product_detail', product_id=product_id)

    cart = request.session.get('cart', {})

    if isinstance(cart, list):
        cart = {}

    product_id_str = str(product_id)
    current_quantity = cart.get(product_id_str, 0)

    if current_quantity < product.stock:
        cart[product_id_str] = current_quantity + 1

    request.session['cart'] = cart

    return redirect('cart')


def cart(request):
    cart = request.session.get('cart', {})

    if isinstance(cart, list):
        cart = {}

    cart_items = []
    total_amount = 0
    updated_cart = {}

    for product_id_str, quantity in cart.items():
        product = get_product_by_id(int(product_id_str))

        if product and product.stock > 0:
            if quantity > product.stock:
                quantity = product.stock

            subtotal = product.price * quantity
            total_amount += subtotal

            cart_items.append({
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal
            })

            updated_cart[product_id_str] = quantity

    request.session['cart'] = updated_cart

    return render(request, 'home/cart.html', {
        "cart_items": cart_items,
        "total_amount": total_amount
    })


def increase_quantity(request, product_id):
    product = get_product_by_id(product_id)

    if product is None:
        return redirect('cart')

    cart = request.session.get('cart', {})

    if isinstance(cart, list):
        cart = {}

    product_id_str = str(product_id)

    if product_id_str in cart:
        if cart[product_id_str] < product.stock:
            cart[product_id_str] += 1

    request.session['cart'] = cart

    return redirect('cart')


def decrease_quantity(request, product_id):
    cart = request.session.get('cart', {})

    if isinstance(cart, list):
        cart = {}

    product_id_str = str(product_id)

    if product_id_str in cart:
        cart[product_id_str] -= 1

        if cart[product_id_str] <= 0:
            del cart[product_id_str]

    request.session['cart'] = cart

    return redirect('cart')


def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})

    if isinstance(cart, list):
        cart = {}

    product_id_str = str(product_id)

    if product_id_str in cart:
        del cart[product_id_str]

    request.session['cart'] = cart

    return redirect('cart')


def clear_cart(request):
    request.session['cart'] = {}
    request.session['coupon_code'] = ''
    return redirect('cart')


@login_required
def checkout(request):
    profile, created = CustomerProfile.objects.get_or_create(user=request.user)

    cart = request.session.get('cart', {})

    if isinstance(cart, list):
        cart = {}

    cart_items = []
    subtotal_amount = 0
    product_names = []
    updated_cart = {}

    for product_id_str, quantity in cart.items():
        product = get_product_by_id(int(product_id_str))

        if product and product.stock > 0:
            if quantity > product.stock:
                quantity = product.stock

            subtotal = product.price * quantity
            subtotal_amount += subtotal

            cart_items.append({
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal
            })

            product_names.append(f"{product.name} x {quantity}")
            updated_cart[product_id_str] = quantity

    request.session['cart'] = updated_cart

    delivery_fee = DELIVERY_FEE if cart_items else 0

    active_coupons = Coupon.objects.filter(is_active=True).order_by('code')

    coupon_code = request.session.get('coupon_code', '')
    discount_amount = 0
    applied_coupon = None

    if coupon_code:
        try:
            applied_coupon = Coupon.objects.get(
                code__iexact=coupon_code,
                is_active=True
            )

            discount_amount = applied_coupon.discount_amount

            if discount_amount > subtotal_amount:
                discount_amount = subtotal_amount

            coupon_code = applied_coupon.code

        except Coupon.DoesNotExist:
            coupon_code = ''
            discount_amount = 0
            applied_coupon = None
            request.session['coupon_code'] = ''

    total_amount = subtotal_amount + delivery_fee - discount_amount

    full_name = request.user.get_full_name()

    if not full_name:
        full_name = request.user.username

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "apply_coupon":
            entered_coupon = request.POST.get("coupon_code", "").strip()

            if not entered_coupon:
                request.session['coupon_code'] = ''
                messages.error(request, "Please select a coupon.")
                return redirect('checkout')

            try:
                coupon = Coupon.objects.get(
                    code__iexact=entered_coupon,
                    is_active=True
                )

                request.session['coupon_code'] = coupon.code
                messages.success(request, "Coupon applied successfully.")

            except Coupon.DoesNotExist:
                request.session['coupon_code'] = ''
                messages.error(request, "Invalid or inactive coupon code.")

            return redirect('checkout')

        if action == "remove_coupon":
            request.session['coupon_code'] = ''
            messages.success(request, "Coupon removed.")
            return redirect('checkout')

        if action == "place_order":
            if not cart_items:
                return redirect('cart')

            customer_name = request.POST.get("name")
            email = request.user.email
            phone = request.POST.get("phone")
            address = request.POST.get("address")
            payment_method = request.POST.get("payment_method")

            profile.phone = phone
            profile.address = address
            profile.save()

            order = Order.objects.create(
                user=request.user,
                customer_name=customer_name,
                email=email,
                phone=phone,
                address=address,
                products=", ".join(product_names),
                delivery_fee=delivery_fee,
                coupon_code=coupon_code,
                discount_amount=discount_amount,
                total_amount=total_amount,
                payment_method=payment_method
            )

            for item in cart_items:
                product = item["product"]
                quantity = item["quantity"]
                item_subtotal = item["subtotal"]

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    price=product.price,
                    quantity=quantity,
                    subtotal=item_subtotal
                )

                product.stock = product.stock - quantity
                product.save()

            request.session['cart'] = {}
            request.session['coupon_code'] = ''

            email_subject = f"Home Decor Order Confirmation - Order #{order.id}"

            email_message = f"""
Hi {order.customer_name},

Thank you for shopping with Home Decor.

Your order has been placed successfully.

Order ID: {order.id}
Subtotal: ${subtotal_amount}
Delivery Fee: ${order.delivery_fee}
Coupon Code: {order.coupon_code}
Discount: ${order.discount_amount}
Total Amount: ${order.total_amount}
Payment Method: {order.payment_method}
Status: {order.status}

Ordered Products:
{order.products}

You can track your order using your Order ID and Email.

Thank you,
Home Decor
"""

            send_mail(
                email_subject,
                email_message,
                settings.DEFAULT_FROM_EMAIL,
                [order.email],
                fail_silently=False,
            )

            return render(request, 'home/order_success.html', {
                "order": order,
                "subtotal_amount": subtotal_amount
            })

    return render(request, 'home/checkout.html', {
        "cart_items": cart_items,
        "subtotal_amount": subtotal_amount,
        "delivery_fee": delivery_fee,
        "coupon_code": coupon_code,
        "discount_amount": discount_amount,
        "total_amount": total_amount,
        "profile": profile,
        "full_name": full_name,
        "active_coupons": active_coupons
    })


@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related('product').order_by('-added_at')

    return render(request, 'home/wishlist.html', {
        "wishlist_items": wishlist_items
    })


@login_required
def add_to_wishlist(request, product_id):
    product = get_product_by_id(product_id)

    if product is None:
        raise Http404("Product not found")

    Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )

    messages.success(request, "Product added to wishlist.")

    next_url = request.GET.get('next')

    if next_url:
        return redirect(next_url)

    return redirect('wishlist')


@login_required
def remove_from_wishlist(request, product_id):
    Wishlist.objects.filter(
        user=request.user,
        product_id=product_id
    ).delete()

    messages.success(request, "Product removed from wishlist.")

    return redirect('wishlist')


def track_order(request):
    order = None
    error = None

    if request.method == "POST":
        order_id = request.POST.get("order_id")
        email = request.POST.get("email")

        try:
            order = Order.objects.get(id=order_id, email=email)
        except Order.DoesNotExist:
            error = "No order found with this Order ID and Email."

    return render(request, 'home/track_order.html', {
        "order": order,
        "error": error
    })


@login_required
def my_orders(request):
    orders = Order.objects.filter(
        Q(user=request.user) | Q(email=request.user.email)
    ).distinct().order_by('-order_date')

    return render(request, 'home/my_orders.html', {
        "orders": orders
    })


@login_required
def invoice(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        raise Http404("Invoice not found")

    if not user_can_access_order(request, order):
        raise Http404("Invoice not found")

    return render(request, 'home/invoice.html', {
        "order": order
    })


@login_required
def cancel_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        raise Http404("Order not found")

    if not user_can_access_order(request, order):
        raise Http404("Order not found")

    if order.status == "Pending" or order.status == "Processing":

        if not order.stock_restored:
            for item in order.items.all():
                if item.product:
                    item.product.stock = item.product.stock + item.quantity
                    item.product.save()

            order.stock_restored = True

        order.status = "Cancelled"
        order.save()

        return render(request, 'home/order_cancelled.html', {
            "order": order
        })

    return render(request, 'home/order_cancel_failed.html', {
        "order": order
    })


def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        return render(request, 'home/contact_success.html')

    return render(request, 'home/contact.html')
    