from rest_framework import serializers
from django.db import transaction
from .models import *

class VendorSerializer(serializers.ModelSerializer): 
    category_name = serializers.CharField(source="category.name", read_only=True)
    
    class Meta: 
        model = Vendor 
        fields = "__all__" 
        read_only_fields = ["vendor_id","category_name"]


class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["product_id"]


class IndentItemSerializer(serializers.ModelSerializer): 
    
    product_name = serializers.CharField(source="product.name", read_only=True) 
    class Meta: 
        model = IndentItem 
        fields = ["id", "product", "product_name", "quantity"]


class GRNItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GRNItem
        fields = [
            "product", "batch_no", "expiry_date",
            "accepted_qty", "received_qty", "damaged_qty", "expired_qty", "rejected_qty",
            "purchase_price", "mrp","discount", "gst_percent", "amount"
        ]


class GRNSerializer(serializers.ModelSerializer):
    items = GRNItemSerializer(many=True)

    class Meta:
        model = GRN
        fields = [
            "grn_number", "grn_type", "purchase_order", "store", "status",
            "invoice_date", "vendor_name", "gst_no", "net_amount", "tax_amount",
            "request_id", "items"
        ]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        grn = GRN.objects.create(**validated_data)
        for item_data in items_data:
            GRNItem.objects.create(grn=grn, **item_data)
        return grn


class IndentSerializer(serializers.ModelSerializer):
    items = IndentItemSerializer(many=True)
    suggested_vendors = serializers.ListField(child=serializers.DictField(), required=False)
    class Meta:
        model = Indent
        fields = ["id", "indent_number", "store", "created_at", "status", "items", "suggested_vendors"]
        read_only_fields = ["indent_number", "created_at"]

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        indent = Indent.objects.create(**validated_data)

        for item in items_data:
            IndentItem.objects.create(indent=indent, **item)

        vendor_map = {}
        for ii in indent.items.select_related("product__category").all():
            cat_name = ii.product.category.name if ii.product and ii.product.category else None
            if not cat_name:
                continue
            for v in Vendor.objects.filter(is_active=True, categories__contains=[cat_name]).only("id", "name"):
                vendor_map[v.id] = {"id": v.id, "name": v.name}

        indent.suggested_vendors = list(vendor_map.values())
        indent.save(update_fields=["suggested_vendors"])
        return indent

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        for field in ("store", "status"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item in items_data:
                IndentItem.objects.create(indent=instance, **item)

            # Recompute vendor suggestions
            vendor_map = {}
            for ii in instance.items.select_related("product__category").all():
                cat_name = ii.product.category.name if ii.product and ii.product.category else None
                if not cat_name:
                    continue
                for v in Vendor.objects.filter(is_active=True, categories__contains=[cat_name]).only("id", "name"):
                    vendor_map[v.id] = {"id": v.id, "name": v.name}
            instance.suggested_vendors = list(vendor_map.values())
            instance.save(update_fields=["suggested_vendors"])

        return instance



