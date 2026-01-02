from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Prefetch ,F,Sum
from django.utils import timezone
from django.utils import timezone 
from django.core.paginator import Paginator
from datetime import date
from .models import *
from .serializers import *
from MySenzApp.models import *
from MySenzApp.crud import DocumentManager
import csv
from django.core.mail import send_mail 
from django.conf import settings


import pytz 
IST = pytz.timezone("Asia/Kolkata")


# vendor crud operation using to serializer

class VendorAPIView(APIView):
    permission_classes = [IsAdminUser] 

    def post(self, request):
        serializer = VendorSerializer(data=request.data)
        if serializer.is_valid():
            vendor = serializer.save()
            return Response(
                {"success":True,"message": "Vendor created", "vendor_id": vendor.vendor_id},)
        return Response({"success": False, "error": serializer.errors})

    
    def put(self, request): 
        vendor_id = request.data.get("vendor_id") 
        vendor = get_object_or_404(Vendor, vendor_id=vendor_id) 
        serializer = VendorSerializer(vendor, data=request.data, partial=True) 
        if serializer.is_valid(): 
            serializer.save() 
            return Response( {"success": True, "message": "Vendor updated", "data": serializer.data}) 
        return Response({"success": False, "error": serializer.errors})
    
    def get(self, request):
        vendors = Vendor.objects.all()
        serializer = VendorSerializer(vendors, many=True)

        return Response(
            {"success": True, "data": serializer.data})

    def delete(self, request):
        json_request = JSONParser().parse(request)
        vendor_id = json_request.get("vendor_id")

        vendor = get_object_or_404(Vendor, pk=vendor_id)
        vendor.delete()
        return Response(
            {"success": True, "message": "Vendor deleted"},
            status=status.HTTP_204_NO_CONTENT
        )
    

#product crud operations 

class ProductAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = Product.objects.all()

        # Extract filters from query params
        category_id = request.query_params.get("category_id")
        brand_name = request.query_params.get("brand_name")
        molecule = request.query_params.get("molecule")
        uom = request.query_params.get("uom")
        color = request.query_params.get("color")
        is_active = request.query_params.get("is_active")

        # Apply filters if present
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if brand_name:
            queryset = queryset.filter(brand_name__icontains=brand_name)
        if molecule:
            queryset = queryset.filter(molecule__icontains=molecule)
        if uom:
            queryset = queryset.filter(uom__iexact=uom)
        if color:
            queryset = queryset.filter(color__iexact=color)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.strip().lower() in ["true", "1"])

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))
        paginator = Paginator(queryset, page_size)
        products_page = paginator.get_page(page)

        serializer = ProductSerializer(products_page, many=True)
        return Response({
            "success": True,
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "current_page": page,
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "message": "Product created successfully", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"success": False, "error": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def put(self, request):
        product_id = request.data.get("product_id")
        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            return Response({"success": False, "error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "message": "Product updated", "data": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        product_id = request.data.get("product_id")
        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            return Response({"success": False, "error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "message": "Product updated", "data": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        product_id = request.data.get("product_id")
        try:
            product = Product.objects.get(product_id=product_id)
            product.delete()
            return Response({"success": True, "message": "Product deleted"}, status=status.HTTP_204_NO_CONTENT)
        except Product.DoesNotExist:
            return Response({"success": False, "error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)


#bulk upload product function 

class BulkUploadAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        products, errors = [], []

        # Accept either JSON array or CSV file
        if isinstance(request.data, list):
            rows = request.data
        else:
            file_csv = request.FILES.get("file")
            if not file_csv:
                return Response(
                    {"success": False, "error": "Provide JSON array or CSV file"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            rows = csv.DictReader(file_csv.read().decode("utf-8").splitlines())

        for idx, row in enumerate(rows, start=1):
            category_name = row.get("category", "").strip().lower()

            category_obj = Category.objects.filter(name__iexact=category_name).first()
            if not category_obj:
                errors.append({
                    "row": idx,
                    "errors": {"category": [f"Category '{category_name}' does not exist"]}
                })
                continue

            # Always use ProductSerializer
            serializer = ProductSerializer(data={k: v for k, v in row.items() if k != "category"})

            if serializer.is_valid():
                obj = Product(**serializer.validated_data)
                obj.category = category_obj

                # Extra validation for medicine category
                if category_name == "medicine":
                    missing = []
                    for field in ["brand_name", "molecule", "uom"]:
                        if not getattr(obj, field, None):
                            missing.append(field)
                    if missing:
                        errors.append({
                            "row": idx,
                            "errors": {f: [f"{f} is required for medicine products"] for f in missing}
                        })
                        continue

                products.append(obj)
            else:
                errors.append({"row": idx, "errors": serializer.errors})

        if errors:
            return Response(
                {"success": False, "message": "Validation failed", "errors": errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save all valid products in one transaction
        with transaction.atomic():
            for product in products:
                product.save()

        return Response(
            {
                "success": True,
                "message": "Bulk upload complete",
                "products_uploaded": len(products),
                "medicines_uploaded": len([p for p in products if p.category.name.lower() == "medicine"])
            },
            status=status.HTTP_201_CREATED
        )



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_vendor(request):
    category_name = request.data.get("category_name")

    if not category_name:
        return Response(
            {"success": False, "error": "category_name is required"})

    # category_name is already a string, so use it directly
    vendors = Vendor.objects.filter(categories__contains=[category_name],is_active=True).values("id", "name")

    return Response(
        {"success": True, "data": list(vendors)},
        status=status.HTTP_200_OK
    )







@csrf_exempt
@api_view(["POST"])
def create_purchase_order(request):
    json_request = JSONParser().parse(request)
    vendor_id = json_request.get("vendor")
    items_data = json_request.get("items", [])

    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except Vendor.DoesNotExist:
        return JsonResponse({"error": f"Vendor with id {vendor_id} does not exist"}, status=400)

    # Create PurchaseOrder
    po = PurchaseOrder.objects.create(vendor=vendor)

    created_items = []
    for item in items_data:
        prod_code = item.get("product_id")
        qty = int(item.get("qty", 0))
        uom = item.get("uom")

        if not prod_code:
            return JsonResponse({"success": False, "message": "Each item must include a valid 'product_id'"}, status=400)

        try:
            prod_obj = Product.objects.get(product_id=prod_code)
        except Product.DoesNotExist:
            return JsonResponse({"success": False, "message": f"Product with product_id {prod_code} does not exist"}, status=400)

        po_item = PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=prod_obj,
            qty=qty,
            uom=uom
        )

        created_items.append({
            "id": po_item.id,
            "product_id": prod_code,
            "qty": qty,
            "uom": uom
        })
        subject = f"New Purchase Order {po.po_number}"
        message = f"""
        Dear {vendor.name},

        A new Purchase Order has been created for you.

        PO Number: {po.po_number}
        Vendor: {vendor.name}
        Items:
        """

        for item in created_items:
            try:
                prod_obj = Product.objects.get(product_id=item["product_id"])
                product_name = prod_obj.name or ""
                molecule = prod_obj.molecule or ""
                brand_name = prod_obj.brand_name or ""
            except Product.DoesNotExist:
                product_name = molecule = brand_name = ""

            message += (
                f"- Product ID: {item['product_id']}, "
                f"Name: {product_name}, "
                f"Brand: {brand_name}, "
                f"Molecule: {molecule}, "
                f"Qty: {item['qty']} {item['uom']}\n"
            )

        message += "\nRegards,\nElixwel Inventory System"

        # Make sure EMAIL_BACKEND and EMAIL_HOST settings are configured in settings.py
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [vendor.email],
            fail_silently=False,
        )

    

    return JsonResponse({"success": True, "message": "Purchase Order created successfully"}, status=201)

@csrf_exempt
@api_view(["POST"])
def get_products(request):
    category_id = request.data.get("category_id")
    if not category_id:
        return JsonResponse({"success": False, "message": "category_id is required"}, status=400)

    try:
        category_id = int(category_id)
    except ValueError:
        return JsonResponse({"success": False, "message": "category_id must be an integer"}, status=400)

    products = Product.objects.filter(category_id=category_id).values()
    return JsonResponse({"success": True, "data": list(products)}, status=200)



@csrf_exempt
@api_view(["POST"])
def get_po_details(request):
    json_request = JSONParser().parse(request)
    po_number = json_request.get("po_number")
    status_filter = json_request.get("status")

    def item_category(item):
        if item.product and item.product.category:
            return item.product.category.name
        return "Uncategorized"

    def po_category_summary(items_qs):
        cats = {item_category(i) for i in items_qs}
        if len(cats) == 0:
            return {"category_name": None, "categories": []}
        if len(cats) == 1:
            only = next(iter(cats))
            return {"category_name": only, "categories": [only]}
        return {"category_name": "Mixed", "categories": sorted(cats)}

    if status_filter:
        pos = (PurchaseOrder.objects
               .select_related("vendor")
               .prefetch_related(
                   Prefetch("items", queryset=PurchaseOrderItem.objects.select_related("product__category"))
               )
               .filter(status=status_filter))

        data = []
        for po in pos:
            summary = po_category_summary(po.items.all())
            data.append({
                "po_number": po.po_number,
                "vendor": getattr(po.vendor, "name", po.vendor_id),
                "created_at": timezone.localtime(po.created_at, IST).strftime("%Y-%m-%d %H:%M:%S"),
                "status": po.status,
                "category_name": summary["category_name"]
            })

        return JsonResponse({"success": True, "count": pos.count(), "purchase_orders": data}, status=200)

    if not po_number:
        pos = (PurchaseOrder.objects
               .select_related("vendor")
               .prefetch_related(
                   Prefetch("items", queryset=PurchaseOrderItem.objects.select_related("product__category"))
               )
               .order_by("-id"))

        data = []
        for po in pos:
            summary = po_category_summary(po.items.all())
            data.append({
                "po_number": po.po_number,
                "vendor": getattr(po.vendor, "name", po.vendor_id),
                "created_at": timezone.localtime(po.created_at, IST).strftime("%Y-%m-%d %H:%M:%S"),
                "status": po.status,
                "category_name": summary["category_name"],
            })
        return JsonResponse({"success": True, "purchase_orders": data}, status=200)

    # One PO with item-level details
    try:
        po = (PurchaseOrder.objects
              .select_related("vendor")
              .prefetch_related(
                  Prefetch("items", queryset=PurchaseOrderItem.objects.select_related("product__category"))
              )
              .get(po_number=po_number))
    except PurchaseOrder.DoesNotExist:
        return JsonResponse({"success": False, "message": f"Purchase Order with number {po_number} does not exist"}, status=404)

    items = []
    for item in po.items.all():
        obj = item.product
        if not obj:
            continue

        item_data = {
            "id": obj.id,
            "product_id": obj.product_id,
            "name": obj.name,
            "description": obj.description,
            "quantity": obj.quantity,
            "brand_name": obj.brand_name,
            "molecule": obj.molecule,
            "uom": obj.uom,
            "shape": obj.shape,
            "material": obj.material,
            "color": obj.color,
            "size": obj.size,
            "stock": obj.stock,
            "is_active": obj.is_active,
            "category": obj.category_id,
            "qty": item.qty,
            "uom_po": item.uom,
            "unit_price": str(item.unit_price) if item.unit_price else None,
            "subtotal": str(item.subtotal),
        }
        items.append(item_data)

    summary = po_category_summary(po.items.all())
    po_data = {
        "po_number": po.po_number,
        "vendor": getattr(po.vendor, "name", po.vendor_id),
        "created_at": timezone.localtime(po.created_at, IST).strftime("%Y-%m-%d %H:%M:%S"),
        "status": po.status,
        "category_name": summary["category_name"],
        "items": items,
    }

    return JsonResponse({"success": True, "purchase_order": po_data}, status=200)


@csrf_exempt
@api_view(["POST"])
def po_update_status(request):
    json_request = JSONParser().parse(request)
    po_number = json_request.get("po_number")
    new_status = json_request.get("status")

    if not po_number or not new_status:
        return JsonResponse({"success": False, "message": "po_number and status are required"}, status=400)

    try:
        po = PurchaseOrder.objects.get(po_number=po_number)
    except PurchaseOrder.DoesNotExist:
        return JsonResponse({"success": False, "message": f"Purchase Order with number {po_number} does not exist"}, status=404)

    po.status = new_status
    po.save()
    return JsonResponse({"success": True, "message": f"Purchase Order {po_number} status updated to {new_status}"}, status=200)



@csrf_exempt
@api_view(["POST"])
def create_indent(request):
    json_request = JSONParser().parse(request)

    store_id = json_request.get("store_id")
    items_data = json_request.get("items", [])
    suggested_vendors = json_request.get("suggested_vendors", [])
    status = json_request.get("status")

    if not store_id or not items_data:
        return JsonResponse({"success": False, "message": "store_id and items are required"}, status=400)

    # Validate UUID
    try:
        store_uuid = uuid.UUID(store_id)
    except ValueError:
        return JsonResponse({"success": False, "message": "Invalid store_id format (must be UUID)"}, status=400)

    # Fetch store
    try:
        store = Store.objects.get(id=store_uuid)
    except Store.DoesNotExist:
        return JsonResponse({"success": False, "message": f"Store with id {store_id} does not exist"}, status=404)

    validated_items = []
    for item in items_data:
        prod_code = item.get("product_id")
        qty = int(item.get("quantity", 0))

        if not prod_code or qty <= 0:
            return JsonResponse({"success": False, "message": "Each item must include product_id and valid quantity"}, status=400)

        try:
            prod_obj = Product.objects.get(product_id=prod_code)
        except Product.DoesNotExist:
            return JsonResponse({"success": False, "message": f"Product with product_id {prod_code} does not exist"}, status=400)

        validated_items.append((prod_obj, qty))

    with transaction.atomic():
        indent = Indent.objects.create(store=store, status=status, suggested_vendors=suggested_vendors)

        created_items = []
        for prod_obj, qty in validated_items:
            indent_item = IndentItem.objects.create(indent=indent, product=prod_obj, quantity=qty)
            created_items.append({
                "id": indent_item.id,
                "product_id": prod_obj.product_id,
                "name": prod_obj.name,
                "quantity": indent_item.quantity,
                "category_id": prod_obj.category_id,
            })

    return JsonResponse({
        "success": True,
        "message": "Indent created successfully",
        "indent_number": indent.indent_number,
        "items": created_items
    }, status=201)


@csrf_exempt 
@api_view(["GET"]) 
def get_intent_list(request): 
    statuses = IndentStatus.objects.values_list("status", flat=True)
    return Response({"success": True, "statuses": list(statuses)}, status=status.HTTP_200_OK)
    

@csrf_exempt
@api_view(["POST"])
def stoke_management(request):
    json_request = JSONParser().parse(request)
    product_id = json_request.get("product_id")

    try:
        product = Product.objects.get(product_id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({"success": False, "message": f"Product with product_id {product_id} does not exist"}, status=404)

    # Example: update stock (you can adjust logic)
    new_stock = int(json_request.get("stock", product.stock))
    product.stock = new_stock
    product.save(update_fields=["stock"])

    return JsonResponse({"success": True, "message": f"Product stock updated to {new_stock}"}, status=200)



@csrf_exempt
@api_view(["POST"])
def get_indent_details(request):
    json_request = JSONParser().parse(request)
    indent_number = json_request.get("indent_number")
    status_filter = json_request.get("status")
    store_id = json_request.get("store_id")

    # Base queryset
    indents_qs = (
        Indent.objects
        .select_related("store")
        .prefetch_related("items__product__category", "items__medicine__category")
    )

    # Apply filters
    if status_filter:
        indents_qs = indents_qs.filter(status=status_filter)
    if store_id:
        indents_qs = indents_qs.filter(store_id=store_id)

    # specific indent_number
    if indent_number:
        try:
            indent = indents_qs.get(indent_number=indent_number)
        except Indent.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": f"Indent with number {indent_number} does not exist"},
                status=404,
            )

        # Resolve vendor names
        vendor_names = []
        if indent.suggested_vendors:
            vendors = Vendor.objects.in_bulk(indent.suggested_vendors)
            vendor_names = [{"id": v.id, "name": v.name} for v in vendors.values()]

        items = []
        category_id, category_name = None, None
        for item in indent.items.all():
            obj = item.product or item.medicine
            if not obj:
                continue
            if hasattr(obj, "category") and obj.category:
                category_id = obj.category_id
                category_name = obj.category.name
            items.append({
                "id": obj.id,
                "name": getattr(obj, "name", None),
                "qty": item.quantity,
                "uom": getattr(obj, "uom", None),
                "brand_name": getattr(obj, "brand_name", None),
                "molecule": getattr(obj, "molecule", None),
                "type": "product" if item.product else "medicine",
                "category_name": category_name,
            })

        indent_data = {
            "indent_number": indent.indent_number,
            "store_id": indent.store_id,
            "created_at": timezone.localtime(indent.created_at, IST).strftime("%Y-%m-%d %H:%M:%S"),
            "status": indent.status,
            "suggested_vendors": vendor_names,
            "category_id": category_id,
            "category_name": category_name,
            "items": items,
        }
        return JsonResponse({"success": True, "indent": indent_data}, status=200)

    # list indents (with filters applied)
    indents_qs = indents_qs.order_by("-id")
    data = []
    for indent in indents_qs:
        vendor_names = []
        first_item = indent.items.first()
        category_id, category_name = None, None

        if indent.suggested_vendors:
            vendors = Vendor.objects.in_bulk(indent.suggested_vendors)
            vendor_names = [{"id": v.id, "name": v.name} for v in vendors.values()]

        if first_item:
            obj = first_item.product or first_item.medicine
            if obj and obj.category:
                category_id = obj.category_id
                category_name = obj.category.name


        data.append({
            "indent_number": indent.indent_number,
            "store_id": indent.store_id,
            "store_name": indent.store.store_name if indent.store else None,
            "created_at": timezone.localtime(indent.created_at, IST).strftime("%Y-%m-%d %H:%M:%S"), 
            "updated_at": timezone.localtime(indent.updated_at, IST).strftime("%Y-%m-%d %H:%M:%S"),
            "status": indent.status,
            "category_id": category_id,
            "category_name": category_name,
            "suggested_vendors": vendor_names,
        })

    return JsonResponse({"success": True, "count": indents_qs.count(), "indents": data}, status=200)



@csrf_exempt
@api_view(["POST"])
def update_indent(request):
    json_request = JSONParser().parse(request)

    indent_number = json_request.get("indent_id")
    status = json_request.get("status")
    items_data = json_request.get("items", [])
    suggested_vendors = json_request.get("suggested_vendors", [])

    try:
        indent = Indent.objects.get(indent_number=indent_number)
    except Indent.DoesNotExist:
        return JsonResponse({"success": False, "message": f"Indent {indent_number} does not exist"})

    if status:
        indent.status = status
    if suggested_vendors:
        indent.suggested_vendors = suggested_vendors
    indent.save()

    created_or_updated_items = []

    with transaction.atomic():
        for item in items_data:
            prod_code = item.get("product_id")
            qty = int(item.get("qty", 0))

            if not prod_code or qty <= 0:
                return JsonResponse({"success": False, "message": "Each item must include product_id and valid quantity"})

            try:
                prod_obj = Product.objects.get(product_id=prod_code)
            except Product.DoesNotExist:
                return JsonResponse({"success": False, "message": f"Product with product_id {prod_code} does not exist"})

            indent_item, created = IndentItem.objects.update_or_create(
                indent=indent,
                product=prod_obj,
                defaults={"quantity": qty}
            )
            action = "created" if created else "updated"

            created_or_updated_items.append({
                "id": indent_item.id,
                "product_id": prod_code,
                "name": prod_obj.name,
                "quantity": indent_item.quantity,
                "category_id": prod_obj.category_id,
                "action": action
            })

    return JsonResponse({
        "success": True,
        "message": f"Indent {indent_number} updated successfully",
        "items": created_or_updated_items
    }, status=200)


@csrf_exempt
@api_view(["GET"])
def UOMdropdown(request):
    data = list(UOM.objects.values_list("name", flat=True))
    return Response({"success": True, "data": data})




@transaction.atomic
def create_grn_from_po(po_id: int, rows: list, request_id: str, actor: str = "system") -> GRN:
    
    existing = GRN.objects.filter(request_id=request_id).first()
    if existing:
        return existing

    po = PurchaseOrder.objects.select_for_update().prefetch_related("items").get(id=po_id)
    if po.status == "cancelled":
        raise GRNError("PO is cancelled")

    # Create GRN record
    grn_number = next_id(prefix=f"GRN-WH-{po.id}-")
    grn = GRN.objects.create(
        grn_number=grn_number,
        grn_type="warehouse",
        purchase_order=po,
        status="Partial",
        request_id=request_id
    )

    # Map PO items for validation
    poi_map = {poi.id: poi for poi in po.items.all()}

    grn_items = []
    # We'll update product/medicine stock inline (select_for_update on rows)
    for r in rows:
        poi_id = int(r.get("purchase_order_item_id") or 0)
        if poi_id not in poi_map:
            raise GRNError(f"PO item {poi_id} not found on PO {po_id}")

        poi = poi_map[poi_id]

        # Determine whether this row is product or medicine and validate
        product_id = r.get("product_id")
        medicine_id = r.get("medicine_id")
        if poi.product_id and not product_id:
            raise GRNError(f"PO item {poi_id} expects product_id")
        if poi.medicine_id and not medicine_id:
            raise GRNError(f"PO item {poi_id} expects medicine_id")

        accepted_qty = int(r.get("accepted_qty") or 0)
        rejected_qty = int(r.get("rejected_qty") or 0)
        batch_no = (r.get("batch_no") or "").strip()
        expiry_date = r.get("expiry_date") or None
        uom = r.get("uom") or poi.uom
        reason = r.get("reason") or ""

        # Expiry policy: if expiry_date provided and expired, treat accepted as 0 and move to rejected
        if expiry_date and _is_expired(expiry_date):
            if accepted_qty > 0:
                rejected_qty += accepted_qty
                accepted_qty = 0

        gi = GRNItem(
            grn=grn,
            product_id=product_id if product_id else None,
            medicine_id=medicine_id if medicine_id else None,
            batch_no=batch_no,
            expiry_date=expiry_date,
            accepted_qty=accepted_qty,
            rejected_qty=rejected_qty,
            uom=uom,
            reason=reason
        )
        grn_items.append(gi)

        # Update stock on Product or Medicine
        if accepted_qty > 0:
            if product_id:
                Product.objects.filter(id=product_id).update(stock=F('stock') + accepted_qty)
            elif medicine_id:
                Medicine.objects.filter(id=medicine_id).update(stock=F('stock') + accepted_qty)

    # Bulk create GRN items
    GRNItem.objects.bulk_create(grn_items)

    # Update PO status if fully received
    if _po_fully_received(po):
        po.status = "received"
        po.save(update_fields=["status"])
        grn.status = "Full"
    else:
        grn.status = "Partial"

    grn.confirmed_at = timezone.now()
    grn.save(update_fields=["status", "confirmed_at"])
    return grn



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_warehouse_grn(request):
    data = request.data
    po_id = data.get("po_id")
    request_id = data.get("request_id")
    rows = data.get("rows", [])

    if not po_id or not request_id or not isinstance(rows, list):
        return Response({"detail": "po_id, request_id and rows[] are required"}, status=status.HTTP_400_BAD_REQUEST)

    # Basic row validation
    parsed = []
    for i, r in enumerate(rows, start=1):
        poi = _parse_int(r.get("purchase_order_item_id"))
        product_id = r.get("product_id")
        medicine_id = r.get("medicine_id")
        uom = r.get("uom") or ""
        accepted_qty = _parse_int(r.get("accepted_qty"))
        rejected_qty = _parse_int(r.get("rejected_qty"))
        batch_no = (r.get("batch_no") or "").strip()
        expiry_date = _parse_date(r.get("expiry_date"))
        reason = r.get("reason") or ""

        if not poi:
            return Response({"detail": f"Row {i}: purchase_order_item_id required"}, status=400)
        if not (product_id or medicine_id):
            return Response({"detail": f"Row {i}: product_id or medicine_id required"}, status=400)

        parsed.append({
            "purchase_order_item_id": poi,
            "product_id": product_id,
            "medicine_id": medicine_id,
            "uom": uom,
            "accepted_qty": accepted_qty,
            "rejected_qty": rejected_qty,
            "batch_no": batch_no,
            "expiry_date": expiry_date,
            "reason": reason
        })

    try:
        grn = create_grn_from_po(po_id=int(po_id), rows=parsed, request_id=str(request_id), actor=request.user.username)
    except GRNError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"grn_number": grn.grn_number, "grn_id": grn.id, "status": grn.status}, status=status.HTTP_201_CREATED)
