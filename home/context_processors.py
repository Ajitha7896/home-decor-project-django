def cart_count(request):
    cart = request.session.get('cart', {})

    if isinstance(cart, list):
        count = len(cart)
    elif isinstance(cart, dict):
        count = sum(cart.values())
    else:
        count = 0

    return {
        'cart_count': count
    }
    