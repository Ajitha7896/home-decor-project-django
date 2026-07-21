from django.contrib import admin
from django.utils.html import format_html
from django.core.mail import send_mail
from django.conf import settings

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


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'price',
        'stock',
        'stock_status',
        'is_available',
        'created_at'
    )

    search_fields = ('name', 'description', 'category')
    list_filter = ('category', 'is_available', 'created_at')
    list_editable = ('price', 'stock', 'is_available')
    ordering = ('stock',)
    list_per_page = 20

    actions = ['mark_available', 'mark_unavailable']

    def stock_status(self, obj):
        if obj.stock == 0:
            return format_html(
                '<span style="color:red; font-weight:bold;">Out of Stock</span>'
            )
        elif obj.stock <= 3:
            return format_html(
                '<span style="color:orange; font-weight:bold;">Low Stock</span>'
            )
        else:
            return format_html(
                '<span style="color:green; font-weight:bold;">In Stock</span>'
            )

    stock_status.short_description = 'Stock Status'

    def mark_available(self, request, queryset):
        queryset.update(is_available=True)

    mark_available.short_description = "Mark selected products as available"

    def mark_unavailable(self, request, queryset):
        queryset.update(is_available=False)

    mark_unavailable.short_description = "Mark selected products as unavailable"


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'short_address')
    search_fields = ('user__username', 'user__email', 'phone', 'address')
    list_per_page = 20

    def short_address(self, obj):
        if obj.address:
            return obj.address[:50]
        return "-"

    short_address.short_description = "Address"


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'discount_amount',
        'is_active',
        'created_at'
    )

    search_fields = ('code',)
    list_filter = ('is_active', 'created_at')
    list_editable = ('discount_amount', 'is_active')
    ordering = ('-created_at',)
    list_per_page = 20

    actions = ['activate_coupons', 'deactivate_coupons']

    def activate_coupons(self, request, queryset):
        queryset.update(is_active=True)

    activate_coupons.short_description = "Activate selected coupons"

    def deactivate_coupons(self, request, queryset):
        queryset.update(is_active=False)

    deactivate_coupons.short_description = "Deactivate selected coupons"


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'user',
        'rating',
        'short_review',
        'created_at'
    )

    search_fields = ('product__name', 'user__username', 'review')
    list_filter = ('rating', 'created_at')
    ordering = ('-created_at',)
    list_per_page = 20

    def short_review(self, obj):
        return obj.review[:60]

    short_review.short_description = "Review"


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'product',
        'product_price',
        'added_at'
    )

    search_fields = ('user__username', 'user__email', 'product__name')
    list_filter = ('added_at',)
    ordering = ('-added_at',)
    list_per_page = 20

    def product_price(self, obj):
        return f"${obj.product.price}"

    product_price.short_description = "Price"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        'product',
        'product_name',
        'price',
        'quantity',
        'subtotal'
    )
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer_name',
        'email',
        'phone',
        'payment_method',
        'status_badge',
        'total_amount',
        'coupon_code',
        'discount_amount',
        'stock_restored',
        'order_date'
    )

    search_fields = (
        'id',
        'customer_name',
        'email',
        'phone',
        'products',
        'user__username',
        'coupon_code'
    )

    list_filter = (
        'payment_method',
        'status',
        'stock_restored',
        'order_date'
    )

    list_editable = ('total_amount',)
    readonly_fields = ('order_date',)
    ordering = ('-order_date',)
    date_hierarchy = 'order_date'
    list_per_page = 20

    inlines = [OrderItemInline]

    actions = [
        'mark_processing',
        'mark_shipped',
        'mark_delivered',
        'mark_cancelled'
    ]

    def status_badge(self, obj):
        if obj.status == "Pending":
            return format_html(
                '<span style="background:#ffc107; color:#000; padding:5px 10px; border-radius:6px; font-weight:bold;">Pending</span>'
            )
        elif obj.status == "Processing":
            return format_html(
                '<span style="background:#0dcaf0; color:#000; padding:5px 10px; border-radius:6px; font-weight:bold;">Processing</span>'
            )
        elif obj.status == "Shipped":
            return format_html(
                '<span style="background:#0d6efd; color:#fff; padding:5px 10px; border-radius:6px; font-weight:bold;">Shipped</span>'
            )
        elif obj.status == "Delivered":
            return format_html(
                '<span style="background:#198754; color:#fff; padding:5px 10px; border-radius:6px; font-weight:bold;">Delivered</span>'
            )
        elif obj.status == "Cancelled":
            return format_html(
                '<span style="background:#dc3545; color:#fff; padding:5px 10px; border-radius:6px; font-weight:bold;">Cancelled</span>'
            )

        return obj.status

    status_badge.short_description = "Status"

    def send_status_email(self, obj, old_status):
        email_subject = f"Home Decor Order Status Update - Order #{obj.id}"

        email_message = f"""
Hi {obj.customer_name},

Your Home Decor order status has been updated.

Order ID: {obj.id}
Previous Status: {old_status}
New Status: {obj.status}

Delivery Fee: ${obj.delivery_fee}
Coupon Code: {obj.coupon_code}
Discount: ${obj.discount_amount}
Total Amount: ${obj.total_amount}
Payment Method: {obj.payment_method}

You can login to your account and check My Orders for more details.

Thank you,
Home Decor
"""

        send_mail(
            email_subject,
            email_message,
            settings.DEFAULT_FROM_EMAIL,
            [obj.email],
            fail_silently=True,
        )

    def restore_stock_if_cancelled(self, obj):
        if obj.status == "Cancelled" and not obj.stock_restored:
            for item in obj.items.all():
                if item.product:
                    item.product.stock = item.product.stock + item.quantity
                    item.product.save()

            obj.stock_restored = True
            obj.save()

    def save_model(self, request, obj, form, change):
        old_status = None

        if change:
            try:
                old_order = Order.objects.get(pk=obj.pk)
                old_status = old_order.status
            except Order.DoesNotExist:
                old_status = None

        super().save_model(request, obj, form, change)

        if change and old_status and old_status != obj.status:
            self.restore_stock_if_cancelled(obj)
            self.send_status_email(obj, old_status)

    def update_status_for_queryset(self, queryset, new_status):
        for order in queryset:
            old_status = order.status

            if old_status != new_status:
                order.status = new_status
                order.save()

                if new_status == "Cancelled" and not order.stock_restored:
                    for item in order.items.all():
                        if item.product:
                            item.product.stock = item.product.stock + item.quantity
                            item.product.save()

                    order.stock_restored = True
                    order.save()

                self.send_status_email(order, old_status)

    def mark_processing(self, request, queryset):
        self.update_status_for_queryset(queryset, "Processing")

    mark_processing.short_description = "Mark selected orders as Processing"

    def mark_shipped(self, request, queryset):
        self.update_status_for_queryset(queryset, "Shipped")

    mark_shipped.short_description = "Mark selected orders as Shipped"

    def mark_delivered(self, request, queryset):
        self.update_status_for_queryset(queryset, "Delivered")

    mark_delivered.short_description = "Mark selected orders as Delivered"

    def mark_cancelled(self, request, queryset):
        self.update_status_for_queryset(queryset, "Cancelled")

    mark_cancelled.short_description = "Mark selected orders as Cancelled"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'order',
        'product_name',
        'price',
        'quantity',
        'subtotal'
    )

    search_fields = ('product_name', 'order__customer_name')
    list_filter = ('order__status',)
    list_per_page = 20


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'email',
        'subject',
        'short_message',
        'submitted_at'
    )

    search_fields = ('name', 'email', 'subject', 'message')
    list_filter = ('submitted_at',)
    ordering = ('-submitted_at',)
    list_per_page = 20

    def short_message(self, obj):
        return obj.message[:70]

    short_message.short_description = "Message"
    