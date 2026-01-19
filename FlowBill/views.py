from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Prefetch ,F,Sum
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import transaction
from django.core.exceptions import ValidationError
from io import TextIOWrapper
from decimal import Decimal
from .models import *
from .serializers import *
from MySenzApp.models import *
from MySenzApp.crud import *
import csv
import pytz 




IST = pytz.timezone("Asia/Kolkata")




class VendorAPIView(APIView):
    def post(self, request):

        serializer = VendorSerializer(data=request.data)

        if serializer.is_valid():
            vendor = serializer.save()
            return Response({"success":True,"message": "Vendor created", "vendor_id": vendor.vendor_id})
        
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
        category_id = request.query_params.get("category_id")

        if category_id: 
            queryset = Vendor.objects.filter(category__id=category_id, is_active=True) 
            vendor = queryset.values("id","name")

            return Response({"success": True, "data": list(vendor)})
        else: 
            queryset = Vendor.objects.filter(is_active=True) 

        serializer = VendorSerializer(queryset, many=True)

        return Response({"success": True, "data": serializer.data})

    def delete(self, request):
        json_request = JSONParser().parse(request)
        vendor_id = json_request.get("vendor_id")

        vendor = get_object_or_404(Vendor, pk=vendor_id)
        vendor.delete()
        return Response({"success": True, "message": "Vendor deleted"},status=status.HTTP_204_NO_CONTENT)
    


class ProductAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = Product.objects.all()
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
        return Response({"success": True,"count": paginator.count,"num_pages": paginator.num_pages,"current_page": page,"data": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ProductSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()

            return Response({"success": True, "message": "Product created successfully", "data": serializer.data},status=status.HTTP_201_CREATED)
        return Response({"success": False, "error": serializer.errors},status=status.HTTP_400_BAD_REQUEST)

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



class BulkUploadAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        products, errors = [], []

        if isinstance(request.data, list):
            rows = request.data
        else:
            file_csv = request.FILES.get("file")
            if not file_csv:
                return Response({"success": False, "error": "Provide JSON array or CSV file"},status=status.HTTP_400_BAD_REQUEST)
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
            {"success": True,"message": "Bulk upload complete","products_uploaded": len(products),
                "medicines_uploaded": len([p for p in products if p.category.name.lower() == "medicine"])
            },
            status=status.HTTP_201_CREATED
        )



class GRNListAPIView(APIView):
    def get(self, request):
        grn_type = request.query_params.get("grn_type")
        qs = GRN.objects.all().prefetch_related("items")
        if grn_type:
            qs = qs.filter(grn_type=grn_type)

        data = []
        for grn in qs:
            items = []
            for item in grn.items.all():
                items.append({
                    "product_name": item.product_name,
                    "batch_no": item.batch_no,
                    "accepted_qty": item.accepted_qty,
                    "mrp": str(item.mrp),
                    "purchase_price": str(item.purchase_price),
                })
            data.append({
                "grn_number": grn.grn_number,
                "grn_type": grn.grn_type,
                "vendor_name": grn.vendor_name,
                "net_amount": str(grn.net_amount),
                "tax_amount": str(grn.tax_amount),
                "items": items,
            })
        return Response(data, status=status.HTTP_200_OK)



class BulkGRNUploadAPIView(APIView):
    @transaction.atomic
    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "CSV file required"}, status=status.HTTP_400_BAD_REQUEST)

        csv_file = TextIOWrapper(file_obj.file, encoding="utf-8")
        reader = csv.DictReader(csv_file)

        items_data = []
        for row in reader:
            items_data.append({
                "product_name": row["Product Name"],
                "batch_no": row["Batch"],
                "expiry_date": row["Exp"],
                "accepted_qty": int(row["Qty"]),
                "purchase_price": float(row["Rate"]),
                "mrp": float(row["MRP"]),
                "uom": row.get("Pack", ""),
                "discount": float(row.get("Disc", 0)),
                "gst_percent": float(row.get("GST%", 0)),
                "amount": float(row["Amount"]),
            })

        grn_data = {
            "grn_number": request.data.get("grn_number"),
            "grn_type": request.data.get("grn_type", "Central"),
            "status": request.data.get("status", "Full"),
            "invoice_date": request.data.get("invoice_date"),
            "vendor_name": request.data.get("vendor_name"),
            "gst_no": request.data.get("gst_no"),
            "net_amount": request.data.get("net_amount", 0),
            "tax_amount": request.data.get("tax_amount", 0),
            "request_id": request.data.get("request_id"),
        }

        grn = create_grn(grn_data, items_data)
        return Response({"message": "GRN created", "grn_number": grn.grn_number}, status=status.HTTP_201_CREATED)



class GRNView(APIView):
    def get(self, request):
        grn_number = request.query_params.get("grn_number")

        if grn_number:

            try:
                grn = GRN.objects.get(grn_number=grn_number)
                items = grn.items.all()

                data = []
                for item in items:
                    po_item = PurchaseOrderItem.objects.filter( purchase_order=grn.purchase_order, product=item.product ).first()
                    data.append({
                        "id": item.id,
                        "product_name": item.product.name if item.product else None,
                        "brand_name": item.product.brand_name if item.product else None, 
                        "uom": item.product.uom if item.product else None, 
                        "qty": po_item.qty if po_item else None,
                        "batch_no": item.batch_no,
                        "accepted_qty": item.accepted_qty,
                        "received_qty": item.received_qty,
                        "damaged_qty": item.damaged_qty,
                        "excess_qty": item.excess_qty,
                        "rejected_qty": item.rejected_qty,
                        "free_qty": item.free_qty,
                        "amount": str(item.amount),
                        "mrp": str(item.mrp),
                        "purchase_price": str(item.purchase_price),
                        "discount": str(item.discount),
                        "gst_perc": str(item.gst_percent),
                        "margin": str(item.margin),
                        "reason": item.reason,
                        "mfg_date":item.manufacturing_date,
                        "exp_date":item.expiry_date,

                    })
                    pass
                return Response({"success":True,"data": data}, status=status.HTTP_200_OK)

            except GRN.DoesNotExist:
                return Response({"success":False,"error": "GRN not found"}, status=status.HTTP_404_NOT_FOUND)

        else:
            grns = GRN.objects.all()
            data = []
            for grn in grns:
                data.append({
                    "grn_number": grn.grn_number,
                    "category": getattr(grn.items.first().product.category, "name", None),
                    "vendor": getattr(grn.purchase_order.vendor, "name", None),
                    "purchase_number": grn.purchase_order.po_number,
                    "created_at":timezone.localtime(grn.created_at, IST).strftime("%Y-%m-%d %H:%M:%S"),
                    "invoice_date": grn.invoice_date,
                    "net_amount": str(grn.net_amount),
                    "tax_amount": str(grn.tax_amount),
                })
            return Response({"success":True, "data": data} , status=status.HTTP_200_OK)


class DispatchAPIView(APIView):
    
    def get(self, request):

        store_id = request.query_params.get("store_id")
        qs = Dispatch.objects.select_related("store", "indent").prefetch_related("items__product_batch", "items__indent_item")
        
        if store_id:
            qs = qs.filter(store_id=store_id)
        data = [
            {
                "id": d.id, 
                "store": d.store.name, 
                "indent": d.indent.indent_number, 
                "status": d.status, 
                "items": [ { "product": di.product_batch.product.name, 
                            "batch_no": di.product_batch.batch_no, 
                            "quantity": di.quantity, } for di in d.items.all() ] 
            } for d in qs
        ]
        qs = Dispatch.objects.select_related("store", "indent").prefetch_related("items__product_batch", "items__indent_item")
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
    
    @transaction.atomic
    def post(self, request):
        indent_id = request.data.get("indent_id")

        try:
            indent = Indent.objects.get(indent_number=indent_id)
        except Indent.DoesNotExist:
            return Response(
                {"success": False, "error": f"Indent {indent_id} does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )

        for item in indent.items.all():
            required_qty = item.quantity
            total_available = (
                ProductBatch.objects.filter(product=item.product, stock__gt=0)
                .aggregate(total_stock=Sum("stock"))["total_stock"]
                or 0
            )
            if required_qty > total_available:
                return Response(
                    {
                        "success": False,
                        "message": f"Not enough stock for product {item.product.name}. "
                                f"Required {required_qty}, available {total_available}"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

    
        dispatch = Dispatch.objects.create(store=indent.store, indent=indent, status="Dispatched")

        #  Deduct stock and create DispatchItems
        for item in indent.items.all():
            required_qty = item.quantity
            batches = ProductBatch.objects.filter(product=item.product, stock__gt=0).order_by("expiry_date")

            for batch in batches:
                if required_qty <= 0:
                    break
                available = batch.stock
                take_qty = min(available, required_qty)

                batch.stock -= take_qty
                batch.save(update_fields=["stock"])

                DispatchItem.objects.create(
                    dispatch=dispatch,
                    product_batch=batch,
                    indent_item=item,
                    quantity=take_qty
                )

                required_qty -= take_qty

        return Response(
            {"success": True, "message": "Dispatch created", "dispatch_id": dispatch.id},
            status=status.HTTP_201_CREATED
        )

    
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


        # email message 
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
        send_po_email(subject, message, vendor.email)

    

    return JsonResponse({"success": True, "message": "Purchase Order created successfully"}, status=201)



@csrf_exempt
@api_view(["POST"])
def get_products(request):
    category_id = request.data.get("category_id")
    subcategory_id = request.data.get("subcategory_id")

    if not category_id and not subcategory_id:
        return JsonResponse({"success": False, "message": "Either category_id or subcategory_id is required"}, status=400)

    products = Product.objects.all().values( *[field.name for field in Product._meta.fields], "sub_category__name" )

    if category_id:
        try:
            category_id = int(category_id)
            products = products.filter(category_id=category_id)
        except (ValueError, TypeError):
            return JsonResponse({"success": False, "message": "category_id must be an integer"}, status=400)

    if subcategory_id:
        try:
            subcategory_id = int(subcategory_id)
            products = products.filter(sub_category_id=subcategory_id)
        except (ValueError, TypeError):
            return JsonResponse({"success": False, "message": "subcategory_id must be an integer"}, status=400)

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
                "id":po.id,
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
                "id":po.id,
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
        qty = int(item.get("qty", 0))

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
        .prefetch_related("items__product__category")
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


@csrf_exempt
@api_view(["GET"])
def store_inventory(request, store_id):
    qs = ProductBatch.objects.filter(store_id=store_id)\
        .values("product__name")\
        .annotate(total_qty=Sum("stock"))
    return Response(qs)


@csrf_exempt
@api_view(["GET"])
def central_inventory(request):
    central_store = Store.objects.get(is_central=True)
    qs = ProductBatch.objects.filter(store=central_store)\
        .values("product__name")\
        .annotate(total_qty=Sum("stock"))
    return Response(qs)


@csrf_exempt 
@api_view(["GET"]) 
def get_intent_list(request): 
    statuses = IndentStatus.objects.values_list("status", flat=True)
    return Response({"success": True, "statuses": list(statuses)}, status=status.HTTP_200_OK)




@csrf_exempt
@api_view(["POST"])
@transaction.atomic
def create_grn(request):
    try:
        data = request.data  
        purchase_order_id = data.get("id")
        items = data.get("items", [])

        po = PurchaseOrder.objects.filter(id=purchase_order_id).first()

      
        grn = GRN.objects.create(
            purchase_order_id=purchase_order_id,
            status=data.get("status"),
            invoice_date=data.get("invoice_date"),
            net_amount=data.get("net_amount", 0),
            tax_amount=data.get("tax_amount", 0),
        )

        # Create GRN Items
        for item in items:
            GRNItem.objects.create(
                grn=grn,
                product_id=item.get("id"),
                batch_no=item.get("batch_no"),
                manufacturing_date=item.get("mfg_date"),
                expiry_date=item.get("exp_date"), 
                accepted_qty=item.get("accepted_qty", 0),
                received_qty=item.get("received_qty", 0),
                damaged_qty=item.get("damaged_qty", 0),
                rejected_qty=item.get("rejected_qty", 0),
                excess_qty = item.get("excess_qty",0),
                free_qty = item.get("free_qty",0),
                reason=item.get("reason"),
                mrp=item.get("mrp"),
                purchase_price=item.get("purchase_price"),
                discount=item.get("discount", 0),
                gst_percent=item.get("gst_perc", 0),
            )
            all_received = all(i.accepted_qty == i.received_qty for i in grn.items.all())
            if all_received:
                po.status = "Completed"
                po.save(update_fields=["status"])

        return Response({"success": True,"message": "GRN created successfully"}, status=status.HTTP_201_CREATED)

    except Exception as e:
        transaction.set_rollback(True)
        return Response({
            "success": False,
            "message": f"Error creating GRN: {str(e)}"
        }, status=status.HTTP_400_BAD_REQUEST)




@csrf_exempt
@api_view(["GET"])
def product_stock_list(request):

    products = Product.objects.filter(batches__stock__gt=0).distinct()
    data = []

    for product in products:
        total_stock = product.batches.aggregate(
            total_stock=Sum("stock")
        )["total_stock"] or 0

        if total_stock <= 0:
            continue

        latest_batch = product.batches.order_by("-created_at").first()

        data.append({
            "id": product.product_id,
            "name": product.name,
            "brand": product.brand_name,
            "uom": product.uom,
            "stock": total_stock,
            "margin": latest_batch.margin_price if latest_batch else 0,
            "mrp": latest_batch.mrp if latest_batch else 0,
        })

    return JsonResponse(data, safe=False)