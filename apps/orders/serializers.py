from rest_framework import serializers
from .models import Orders, OrderItems, Payments, Shipments, ProductReturns
from apps.users.serializers import AddressSerializer


class OrderSerializer(serializers.ModelSerializer):
    shipping_address_detail = AddressSerializer(source='shipping_address', read_only=True)
    
    class Meta:
        model = Orders
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    
    class Meta:
        model = OrderItems
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payments
        fields = '__all__'


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipments
        fields = '__all__'


class ProductReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReturns
        fields = '__all__'
