from django.db import models
from django.conf import settings
from django.db.models import Avg


class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Living Room', 'Living Room'),
        ('Bedroom', 'Bedroom'),
        ('Dining Room', 'Dining Room'),
        ('Chairs', 'Chairs'),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Living Room')
    price = models.IntegerField()
    image = models.ImageField(upload_to='products/')
    description = models.TextField()
    stock = models.PositiveIntegerField(default=10)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def average_rating(self):
        average = self.reviews.aggregate(avg=Avg('rating'))['avg']

        if average:
            return round(average, 1)

        return 0

    @property
    def review_count(self):
        return self.reviews.count()

    def __str__(self):
        return self.name


class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.user.username


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_amount = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


class ProductReview(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    review = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')

    def __str__(self):
        return f"{self.product.name} - {self.rating} Stars"


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]

    PAYMENT_CHOICES = [
        ('Cash on Delivery', 'Cash on Delivery'),
        ('Credit Card', 'Credit Card'),
        ('PayPal', 'PayPal'),
        ('Bank Transfer', 'Bank Transfer'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    customer_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    products = models.TextField(blank=True)

    delivery_fee = models.IntegerField(default=0)
    coupon_code = models.CharField(max_length=50, blank=True)
    discount_amount = models.IntegerField(default=0)
    total_amount = models.IntegerField()

    payment_method = models.CharField(max_length=50, choices=PAYMENT_CHOICES, default='Cash on Delivery')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    stock_restored = models.BooleanField(default=False)
    order_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=100)
    price = models.IntegerField()
    quantity = models.PositiveIntegerField()
    subtotal = models.IntegerField()

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
        