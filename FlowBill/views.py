from collections import defaultdict
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

from django.db.models import Sum, F
from rest_framework.pagination import PageNumberPagination
class LargeResultSetPagination(PageNumberPagination):
    page_size = 200  
    page_size_query_param = "page_size"
    max_page_size = 1000  



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

        try:
            category_id = int(category_id) if category_id is not None else None
        except ValueError:
            return Response({"success": False, "message": "Invalid category_id"}, status=400)

        if category_id == 0:
            vendors = Vendor.objects.all().values("id", "name")
            return Response({"success": True, "data": list(vendors)}, status=200)

        elif category_id: 
            queryset = Vendor.objects.filter(category__id=category_id) 
            vendor = queryset.values("id", "name")
            return Response({"success": True, "data": list(vendor)}, status=200)

        else: 
            queryset = Vendor.objects.all()
            serializer = VendorSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data}, status=200)


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
        status_filter = request.query_params.get("status")  # new filter

        qs = Dispatch.objects.select_related("store", "indent").prefetch_related(
            "items__product_batch", "items__indent_item"
        )

        if store_id:
            qs = qs.filter(store_id=store_id)

        if status_filter:
            qs = qs.filter(status=status_filter)

        data = [
            {
                "id": d.id,
                "store": d.store.store_name,
                "dispatch_id": d.dispatch_id,
                "created_at": timezone.localtime(d.created_at, IST).strftime("%Y-%m-%d %H:%M:%S"),
                "indent": d.indent.indent_number,
                "indent_id": d.indent.id,
                "status": d.status,
                "items": [
                    {
                        "product": di.product_batch.product.name,
                        "product_id": di.product_batch.product.id,
                        "brand_name": di.product_batch.product.brand_name,
                        "uom": di.product_batch.product.uom,
                        "gst": di.product_batch.gst_percent,
                        "exp_date": di.product_batch.expiry_date,
                        "batch_no": di.product_batch.batch_no,
                        "margin": di.product_batch.margin_price,
                        "mrp": di.product_batch.mrp,
                        "quantity": di.quantity,
                    }
                    for di in d.items.all()
                ],
            }
            for d in qs
        ]

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
        indent.status = "Dispatched"
        indent.save(update_fields=["status"])

        return Response(
            {"success": True, "message": "Dispatch created", "dispatch_id": dispatch.id},
            status=status.HTTP_201_CREATED
        )



class RecipeAPIView(APIView):

    def post(self,request):
        serializer = RecipeSerializer(data=request.data)

        if serializer.is_valid():
            recipe = serializer.save()
            return Response({"success":True,"message":"Recipe created","recipe_id":recipe.recipe_id},status=status.HTTP_201_CREATED)
        return Response({"success":False,"error":serializer.errors},status=status.HTTP_400_BAD_REQUEST)
    
    def get(self,request):
        recipe_id = request.query_params.get("id")

        category = request.query_params.get("category_id")
        if category:
            queryset = Recipe.objects.filter(service__category__id=category)
            data = []
            for recipe in queryset:
                data.append({
                    "id": recipe.id,
                    "recipe_id": recipe.recipe_id,
                    "service": recipe.service.name,
                    "created_at": timezone.localtime(recipe.created_at, IST).strftime("%Y-%m-%d %H:%M:%S"),
                })
            return Response({"success":True,"data":data},status=status.HTTP_200_OK)
        
        if recipe_id:
            recipe = Recipe.objects.select_related("service").prefetch_related("items__product").get(id=recipe_id)

            grouped = defaultdict(list) 
            
            for item in recipe.items.all().order_by("-version"): 
                grouped[f"v{item.version}"].append({ "id": item.id,"product":item.product.id, "product_name": item.product.name, "uom": item.product.uom, "quantity": item.quantity, "created_at": timezone.localtime(item.created_at, IST).strftime("%Y-%m-%d %H:%M:%S"), })
            data = { "id": recipe.id, 
                    "recipe_id": recipe.recipe_id, 
                    "service": recipe.service.name,"category_id": recipe.service.category.id if recipe.service and recipe.service.category else None, 
                    "created_at": timezone.localtime(recipe.created_at).strftime("%Y-%m-%d %H:%M:%S"), 
                    "items": grouped,  }
            return Response({"success": True, "data": data}, status=status.HTTP_200_OK) 
        else:
            recipes = Recipe.objects.all()
            data = []
            for recipe in recipes:
                data.append({
                    "id": recipe.id,
                    "recipe_id": recipe.recipe_id,
                    "service": recipe.service.name,
                    
                    "created_at": timezone.localtime(recipe.created_at, IST).strftime("%Y-%m-%d %H:%M:%S"),
                })
            return Response({"success":True,"data":data},status=status.HTTP_200_OK)   



class GRNReturnAPIView(APIView):
    @transaction.atomic
    def post(self, request):
        vendor_id = request.data.get("vendor_id")
        items_data = request.data.get("items", [])
        vendor_type = request.data.get("vendor_type", "")
        reason = request.data.get("reason", "")
        insert_type = request.data.get("insert_type", "")

        # Vendor lookup
        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            return Response({"success": False, "error": "Vendor not found"})

        grn_return = GRNReturn.objects.create(
            vendor=vendor,
            vendor_type=vendor_type,
            status="initiated",
            reason=reason)
       
        total_credit_amount = 0
        return_details = []

        for item in items_data:
            grn_item_id = item.get("batch_no")
            return_qty = int(item.get("return_qty", 0))

            try:
                grn_item = ProductBatch.objects.select_for_update().get(batch_no=grn_item_id)
            except ProductBatch.DoesNotExist:
                return Response({"success": False, "error": f"ProductBatch {grn_item_id} not found"})

            
            available_qty = grn_item.stock

            if return_qty <= 0: 
                return_qty = available_qty

            if return_qty > available_qty: 
                return Response( {"success": False, "error": f"Return qty exceeds available qty for batch {grn_item.batch_no}"}, status=status.HTTP_400_BAD_REQUEST )


            # Update ProductBatch
            grn_item.stock = F("stock") - return_qty
            grn_item.save(update_fields=["stock"])

            # Credit calculation
            item_credit = return_qty * grn_item.purchase_price
            total_credit_amount += item_credit

            
            

            item_credit = return_qty * grn_item.purchase_price
            
            GRNReturnItem.objects.create(
                grn_return=grn_return,
                product_item=grn_item,
                return_quantity=return_qty,
                batch_no=grn_item.batch_no,
                amount = item_credit
            )

            return_details.append({
                "product": grn_item.product.name,
                "batch_no": grn_item.batch_no,
                "return_qty": return_qty,
                "credit_amount": item_credit
            })

       
        credit_note = CreditNote.objects.create(
            vendor=vendor,
            grn=grn_return,
            total_amount=total_credit_amount,
            active=True,
            insert_type=insert_type
)

        return Response({"success": True,"grn_return_number": grn_return.grn_return_number,"credit_amount": str(credit_note.total_amount),"return_details": return_details
        }, status=status.HTTP_200_OK)






    def get(self, request):
        grn_number = request.query_params.get("grn_number")

        if not grn_number:
            return Response({"success": False, "error": "grn_number parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            grn = GRN.objects.get(grn_number=grn_number)
        except GRN.DoesNotExist:
            return Response({"success": False, "error": f"GRN {grn_number} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        data = []
        for item in grn.items.all():
            data.append({
                "batch_no": item.batch_no,
                "accepted_qty": item.accepted_qty,
                "returned_qty": item.returned_qty,
            })

        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)




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
                "vendor_id": po.vendor_id,
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
        prod_code = item.get("id")
        qty = int(item.get("qty", 0))

        if not prod_code or qty <= 0:
            return JsonResponse({"success": False, "message": "Each item must include product_id and valid quantity"}, status=400)

        try:
            prod_obj = Product.objects.get(id=prod_code)
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
            prod_code = item.get("id")
            qty = int(item.get("qty", 0))

            if not prod_code or qty <= 0:
                return JsonResponse({"success": False, "message": "Each item must include product_id and valid quantity"})

            try:
                prod_obj = Product.objects.get(id=prod_code)
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
            purchase_order_id=po.id,
            status=data.get("status"),
            vendor_id=data.get("vendor_id"),
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
    products = Product.objects.filter(product_batches__stock__gt=0).distinct() 
    data = [] 

    for product in products:
        total_stock = ProductBatch.objects.filter(product=product).aggregate( total_stock=Sum("stock") )["total_stock"] or 0


        latest_batch = ProductBatch.objects.filter(product=product).order_by("-created_at").first()

        data.append({
            "product_id": product.product_id,
            "name": product.name,
            "brand_name": product.brand_name,
            "uom": product.uom,
            "stock": total_stock,
            "margin": latest_batch.margin_price if latest_batch else 0,
            "mrp": latest_batch.mrp if latest_batch else 0,
        })

    return JsonResponse({"success": True, "data": data}, safe=False)




@api_view(["POST"])
def create_recipe_version(request):
    from django.db.models import Max
    recipe_id = request.data.get("recipe_id")
    items_data = request.data.get("items", [])

    if not recipe_id:
        return Response(
            {"success": False, "message": "recipe_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        recipe = Recipe.objects.get(recipe_id=recipe_id)
    except Recipe.DoesNotExist:
        return Response(
            {"success": False, "message": f"Recipe with id {recipe_id} does not exist"},
            status=status.HTTP_404_NOT_FOUND
        )

    
    last_version = (Recipeiterm.objects.filter(recipe=recipe).aggregate(Max("version"))["version__max"] or 1)
    new_version = last_version + 1

    with transaction.atomic():
        
        for item in items_data:
            Recipeiterm.objects.create(
                recipe=recipe,
                product_id=item["product_id"],  
                quantity=item["quantity"],
                version=new_version,
            )

    return Response(
        {
            "success": True,
            "message": f"Recipe version v{new_version} created successfully",
            "recipe_id": recipe.recipe_id,
            "version": new_version
        },
        status=status.HTTP_201_CREATED
    )



@api_view(["GET"])
def get_vendor_stock(request):
    try:
        vendor_id = request.query_params.get("vendor_id")
        category_id = request.query_params.get("category_id")

        if not vendor_id and not category_id:
            return Response({
                "success": False,
                "message": "Either vendor_id or category_id is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        stock_data = []

       
        if vendor_id:
            grns = GRN.objects.filter(vendor_id=vendor_id).prefetch_related("items__product")
            for grn in grns:
                for item in grn.items.all():
                    stock_data.append({
                        "grn_number": grn.grn_number,
                        "product_id": item.product_id,
                        "HSNcode":item.product.hsn_Code,
                        "product_name": item.product.name if item.product else None,
                        "batch_no": item.batch_no,
                        "exp_date": item.expiry_date,
                        "accepted_qty": item.accepted_qty,
                        "stock": ProductBatch.objects.filter(
                            product=item.product,
                            batch_no=item.batch_no
                        ).values_list("stock", flat=True).first(),
                        "mrp": str(item.mrp),
                        "purchase_price": str(item.purchase_price),
                        "margin": str(item.margin),
                    })

       
        if category_id:
            batches = ProductBatch.objects.filter(product__category_id=category_id).select_related("product")
            for batch in batches:
                stock_data.append({
                    "product_id": batch.product.id,
                    "product_name": batch.product.name,
                    "HSNcode":batch.product.hsn_Code,
                    "batch_no": batch.batch_no,
                    "exp_date": batch.expiry_date,
                    "stock": batch.stock,
                    "mrp": str(batch.mrp),
                    "purchase_price": str(batch.purchase_price),
                    "margin": str(batch.margin_price),
                })

        return Response({
            "success": True,
            "count": len(stock_data),
            "data": stock_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "success": False,
            "message": f"Error fetching vendor stock: {str(e)}"
        }, status=status.HTTP_400_BAD_REQUEST)



@api_view(["GET"])
def get_credit_notes(request):
    note_type = request.query_params.get("note_type")

    if note_type == "credit":
        vendor_totals = (
            CreditNote.objects.filter(active=True)
            .values("vendor_id", "vendor__name")
            .annotate(total=Sum("total_amount"))
            .order_by("vendor__name")
        )
        data = [
            {
                "vendor_id": vt["vendor_id"],
                "vendor_name": vt["vendor__name"],
                "total_credit_amount": str(vt["total"]),
            }
            for vt in vendor_totals
        ]
        return Response({"success": True, "count": len(data), "data": data})

    elif note_type == "history":
        notes = (
            CreditNote.objects
            .select_related("vendor")
            .values(
                "vendor_id",
                "vendor__name",
                "insert_type",
                "active",
                "total_amount",
                "created_at"
            )
        )
        data = [
            {
                "vendor_id": n["vendor_id"],
                "vendor_name": n["vendor__name"],
                "insert_type": n["insert_type"],
                "is_active": n["active"],
                "total_credit_amount": str(n["total_amount"]),
                "created_at": timezone.localtime(n["created_at"], IST).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for n in notes
        ]
        return Response({"success": True, "count": len(data), "data": data})

    return Response({"success": False, "message": "Invalid note_type"}, status=400)




class CategoryFilterView(APIView):
    def post(self,request):
        category_ids = request.data.get("categorys",[])
        filter_type = request.data.get("fiter_type")

        if filter_type == "products":
             products = Product.objects.filter(category_id__in=category_ids).only("id","name").values("id", "name").iterator()
             results = list(products)
        elif filter_type == "services":
            services = Service.objects.filter(category_id__in=category_ids).only("id", "name", "price").values("id", "name", "price").iterator()
            results = list(services) 

        else:
            products = Product.objects.filter(category_id__in=category_ids).only("id","name").values("id", "name").iterator()
            services = Service.objects.filter(category_id__in=category_ids).only("id", "name").values("id", "name").iterator()
            results = { "products": list(products), "services": list(services) }

        return Response({"success":True,"data":results})
    


class PackageCreateAPIView(APIView):

    @transaction.atomic
    def post(self, request):
        data = request.data

        try:
            
            package = Packages.objects.create(
                package_name=data.get("package_name"),
                package_type=data.get("package_type"),
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
                discount=data.get("discount", 0)
            )

            items = data.get("Products", [])
            package_items = []
            total_price = 0

            for item in items:
                item_type = item.get("type", "").strip().lower()
                item_id = item.get("item")
                qty = int(item.get("qty", 1))

                package_item = PackagesItem(
                    packages=package,
                    item_type=item_type,
                    qty=qty,
                )

                if item_type == "product":
                    product = ProductBatch.objects.get(id=item_id)
                    package_item.product_id = item_id
                    total_price += (product.mrp or 0) * qty

                elif item_type == "service":
                    service = Service.objects.get(id=item_id)
                    package_item.service_id = item_id
                    total_price += (service.price or 0) * qty

                else:
                    raise ValueError(f"Invalid item type: {item_type}")

                package_items.append(package_item)

            
            PackagesItem.objects.bulk_create(package_items)

            discount_percentage = package.discount or 0
            final_price = total_price - (total_price * discount_percentage / 100)
            package.price = final_price
            package.save()

            return Response({
                "success": True,
                "package_id": package.id,
                "items_count": len(package_items),
                "total_price": str(total_price),
                "final_price": str(final_price),
                "discount": f"{discount_percentage}%"
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


    def get(self, request):

        packages = Packages.objects.prefetch_related(
            Prefetch(
                "packagesitem_set",
                queryset=PackagesItem.objects.select_related("product", "service")
            )
        )

        response = []

        for pkg in packages:
            response.append({
                "package_id": pkg.id,
                "package_name": pkg.package_name,
                "package_type": pkg.package_type,
                "start_date": pkg.start_date,
                "end_date": pkg.end_date,
                "created_at": timezone.localtime(pkg.created_at).strftime("%Y-%m-%d %H:%M:%S"),
                "discount": f"{pkg.discount}%",
                "final_price": str(pkg.price),
                "Products": [
                    {
                        "type": item.item_type.lower(),
                        "id": item.product.id if item.product else item.service.id,
                        "name": item.product.name if item.product else item.service.name,
                        "qty": item.qty,
                    }
                    for item in pkg.packagesitem_set.all()
                ]
            })

        return Response({"success": True,"data": response},status=status.HTTP_200_OK)




class StoreGrnAPIView(APIView):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            store = Store.objects.get(id=data.get("store"))
            indent = Indent.objects.get(id=data.get("indent_id"))

            grn = StoreGrn.objects.create(
                store=store,
                indent=indent,
            )

            net_amount = Decimal(0)
            items = data.get("items", [])
            for item in items:
                product = Product.objects.get(id=item.get("product_id"))

                accepted_qty = Decimal(item.get("accepted_qty", 0))
                mrp = Decimal(item.get("mrp", 0))

                amount = accepted_qty * mrp
                net_amount += amount

                StoreGrnItem.objects.create(
                    store_grn=grn,
                    product=product,
                    batch_no=item.get("batch_no"),
                    expiry_date=item.get("exp_date"),
                    received_qty=item.get("received_qty", 0),
                    rejected_qty=item.get("rejected_qty", 0),
                    damaged_qty=item.get("damaged_qty", 0),
                    excess_qty=item.get("excess_qty", 0),
                    free_qty=item.get("free_qty", 0),
                    amount=amount,
                    reason=item.get("reason", ""),
                    accepted_qty=accepted_qty,
                    mrp=mrp,
                    purchase_price=item.get("purchase_price", 0),
                    gst_percent=item.get("gst_percent", 0),
                    margin_price=item.get("margin", 0),
                )

            grn.net_amount = net_amount
            grn.save(update_fields=["net_amount"])

            indent.status = "completed"
            indent.save(update_fields=["status"])

            Dispatch.objects.filter(indent=indent).update(status="completed")

            return Response({"success": True, "message": "GRN created and status updated"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, **kwargs):
        store_id = request.query_params.get("store_id")
        status_filter = request.query_params.get("status")  # fixed typo

        if not store_id:
            return Response(
                {"error": "store_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Base queryset
        grns = (
            StoreGrn.objects.filter(store_id=store_id)
            .select_related("indent")
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=StoreGrnItem.objects.select_related("product").only(
                        "id", "batch_no", "accepted_qty", "mrp",
                        "purchase_price", "amount", "product__name",
                    ),
                )
            )
            .only("id", "grn_number", "status", "net_amount", "indent_id")
            .order_by("-created_at")
        )

        # Apply status filter if provided
        if status_filter:
            grns = grns.filter(status=status_filter)

        data = [
            {
                "grn_number": grn.grn_number,
                "indent": grn.indent_id,
                "status": grn.status,
                "created_at":timezone.localtime(grn.created_at, IST).strftime("%Y-%m-%d %H:%M:%S"),
                "net_amount": str(grn.net_amount),
                "items": [
                    {
                        "product": item.product.name if item.product else None,
                        "batch_no": item.batch_no,
                        "accepted_qty": item.accepted_qty,
                        "mrp": str(item.mrp),
                        "purchase_price": str(item.purchase_price),
                        "amount": str(item.amount),
                    }
                    for item in grn.items.all()
                ],
            }
            for grn in grns
        ]

        return Response({"success":True,"data": data}, status=status.HTTP_200_OK)




class StoreStockAPIView(APIView):

    def get(self, request, *args, **kwargs):
        store_id = request.query_params.get("store_id")

        if not store_id:
            return Response({"success":True,"error": "store_id is required"})

        products = (Product.objects.filter(stocks__store_id=store_id, stocks__stock__gt=0).distinct())

        data = []
        for product in products:

            total_stock = (product.stocks.filter(store_id=store_id)
                .aggregate(total=Sum("stock"))
                ["total"] or 0)

            if total_stock <= 0:
                continue

            latest_stock = (product.stocks.filter(store_id=store_id)
                .order_by("-created_at")
                .select_related("storegrn__indent")
                .first()
            )

            data.append({
                "product_id": product.id,
                "product_name": product.name,
                "brand_name": product.brand_name,
                "uom": product.uom,
                "stock": total_stock,
                "mrp": str(latest_stock.mrp) if latest_stock else "0",
                "margin_price": str(latest_stock.margin_price) if latest_stock else "0",
                "grn_number": latest_stock.storegrn.grn_number if latest_stock else None,
                "indent_number": (
                    latest_stock.storegrn.indent.indent_number
                    if latest_stock and latest_stock.storegrn.indent
                    else None
                ),
            })

        return Response(
            {
                "success": True,
                "total_products": len(data),
                "data": data,
            },
            status=status.HTTP_200_OK
        )



class StoreStockList(APIView):
    def get(request):
        store_id = request.query_params.get("store_id")

        if not store_id:
            return JsonResponse({"success":True,"message": "store is is required "})
        
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))  
        offset = (page - 1) * page_size
        limit = offset + page_size

        products_qs = Product.objects.filter(stocks__store_id=store_id, stocks__stock__gt=0).distinct()

        total_products = products_qs.count()
        products = products_qs[offset:limit]

        data=[]

        for product in products:
            total_stock =(
                Stock.objects.filter(store_id=store_id,product=product)
                .aggregate(total_stock=Sum("stock"))["total_stock"]
                or 0
            )
            latest_batch = (
            Stock.objects.filter(store_id=store_id, product=product)
            .order_by("-created_at")
            .first())

            data.append({
            "product_id": product.product_id,
            "name": product.name,
            "brand_name": product.brand_name,
            "uom": product.uom,
            "total_stock": total_stock,
            "mrp": latest_batch.mrp if latest_batch else 0,
            "margin": latest_batch.margin_price if latest_batch else 0,})

        return JsonResponse({"success":True,"message":"successfulyy get stock "})
    


@api_view(["GET"])
def store_category_stock_list(request):
    try:
        store_id = request.query_params.get("store_id")
        category_id = request.query_params.get("category_id")

        if not store_id or not category_id:
            return Response(
                {"success": False, "message": "Both store_id and category_id are required"},
                status=400
            )

        stock_data = []

        products = Product.objects.filter(stocks__store_id=store_id,stocks__product__category_id=category_id,stocks__stock__gt=0).distinct()

        for product in products:
            # Total stock across all batches
            total_stock = (
                Stock.objects.filter(store_id=store_id, product=product, stock__gt=0)
                .aggregate(total=Sum("stock"))["total"] or 0
            )

            if total_stock <= 0:
                continue

            # Pick the batch that expires soonest (FEFO)
            soonest_batch = (
                Stock.objects.filter(store_id=store_id, product=product, stock__gt=0)
                .order_by("expiry_date")  
                .select_related("storegrn__indent")
                .first()
            )

            if not soonest_batch:
                continue

            stock_data.append({
                "product_id": product.product_id,
                "product_name": product.name,
                "brand_name": product.brand_name,
                "HSNcode": product.hsn_Code,
                "uom": product.uom,
                "stock": total_stock,
                "mrp": str(soonest_batch.mrp),
                "margin_price": str(soonest_batch.margin_price),
                "grn_number": soonest_batch.storegrn.grn_number if soonest_batch.storegrn else None,
                "exp_date": soonest_batch.expiry_date,
                "batch_no": soonest_batch.batch_no,
                "stock_id": soonest_batch.id,
                "indent_number": (
                    soonest_batch.storegrn.indent.indent_number
                    if soonest_batch.storegrn and soonest_batch.storegrn.indent
                    else None
                ),
            })

        return Response(
            {"success": True, "count": len(stock_data), "data": stock_data},
            status=200
        )

    except Exception as e:
        return Response(
            {"success": False, "message": f"Error fetching store/category stock: {str(e)}"},
            status=400
        )




class StoreGrnReturnView(APIView):

    @transaction.atomic
    def post(self, request):
        store_id = request.data.get("store_id")
        reason = request.data.get("reason")
        return_type = request.data.get("return_type")
        items = request.data.get("products", [])

        if not store_id or not return_type or not items:
            return Response({"success": False, "message": "store_id, return_type and items are required"},
                            status=status.HTTP_400_BAD_REQUEST)

        storegrn_return = StoreGrnReturn.objects.create(
            store_id=store_id,
            reason=reason,
            return_type=return_type,
            status="initiated"
        )

        for item in items:
            stock_id = item.get("stock_id")
            batch_no = item.get("batch_no")
            return_qty = int(item.get("return_qty", 0))
            amount = item.get("amount", 0)

            stock = Stock.objects.get(id=stock_id, batch_no=batch_no, store_id=store_id)
            if return_qty > stock.stock:
                return Response({
                    "success": False,
                    "message": f"Return qty {return_qty} exceeds available stock {stock.stock} for batch {batch_no}"
                }, status=status.HTTP_400_BAD_REQUEST)

            stock.stock -= return_qty
            stock.save(update_fields=["stock"])

            amount = return_qty * stock.mrp

            StoreGrnReturnItem.objects.create(
                storegrn_return=storegrn_return,
                stock=stock,
                batch_no=batch_no,
                return_qty=return_qty,
                amount=amount
            )

        return Response({"success": True,"message": "Store GRN return created successfully","storegrn_return_number": storegrn_return.storegrn_return_number}, status=status.HTTP_201_CREATED)
    


    def get(self, request):

        store_id = request.query_params.get("store_id")
        status_filter = request.query_params.get("status")

        if not store_id:
            return Response({"success": False, "message": "store_id is required"},status=status.HTTP_400_BAD_REQUEST)

        queryset = StoreGrnReturn.objects.filter(store_id=store_id)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        
        queryset = queryset.select_related("store").prefetch_related("items__stock__product")

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 1000))

        start = (page - 1) * page_size
        end = start + page_size

        results = queryset[start:end]

        data = []
        for obj in results:
            items_data = []
            for item in obj.items.all():
                product = item.stock.product  
                items_data.append({
                    "id": item.id,
                    "stock_id": item.stock.id,
                    "batch_no": item.batch_no,
                    "return_qty": item.return_qty,
                    "amount": str(item.amount),
                    "product_id": product.product_id,
                    "product_name": product.name,
                    "hsn_code": product.hsn_Code,
                })

            data.append({
                "id": obj.id,
                "storegrn_return_number": obj.storegrn_return_number,
                "status": obj.status,
                "reason": obj.reason,
                "return_type": obj.return_type,
                "created_at": timezone.localtime(obj.created_at, IST).strftime("%Y-%m-%d %H:%M:%S"),
                "store_id": obj.store_id,
                "products": items_data,
            })

        return Response({"success": True,"count": queryset.count(),"page": page,"page_size": page_size,"data": data}, status=status.HTTP_200_OK)




class StoreCategoryStockView(APIView):
    pagination_class = LargeResultSetPagination

    def get(self, request, *args, **kwargs):
        store_id = request.query_params.get("store_id")
        category_id = request.query_params.get("category_id")
        type = request.query_params.get("type")

        if not store_id or not category_id:
            return Response(
                {"success": False, "message": "store_id and category_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = []

        if type == "Product":
            products = (
                Product.objects.filter(
                    stocks__store_id=store_id,
                    stocks__stock__gt=0,
                    category_id=category_id
                )
                .distinct()
                .select_related("sub_category")
                .prefetch_related("stocks")
                .order_by("id")
            )

            for product in products:
                total_stock = (
                    product.stocks.filter(store_id=store_id)
                    .aggregate(total=Sum("stock"))["total"] or 0
                )
                if total_stock <= 0:
                    continue

                latest_stock = (
                    product.stocks.filter(store_id=store_id, stock__gt=0)
                    .order_by("expiry_date")  # FEFO
                    .select_related("storegrn__indent")
                    .first()
                )
                if not latest_stock:
                    continue

                mrp = latest_stock.mrp or 0
                margin = latest_stock.margin_price or 0
                discount_percentage = product.sub_category.discount or 0

                max_discount_value = (margin * discount_percentage) / 100
                max_value = mrp - max_discount_value
                discount_percentage_calculated = (
                    (max_discount_value / mrp) * 100 if mrp > 0 else 0
                )

                data.append({
                    "id": product.id,
                    "product_id":product.product_id,
                    "product_name": product.name,
                    "brand_name": product.brand_name,
                    "uom": product.uom,
                    "HSNcode": product.hsn_Code,
                    "molecule": product.molecule,
                    "stock": total_stock,
                    "mrp": float(mrp),
                    "margin_price": float(margin),
                    "discount_percentage": float(discount_percentage),
                    "max_discount_value": float(max_discount_value),
                    "max_value": float(max_value),
                    "discount_percentage_calculated": float(discount_percentage_calculated),
                    "grn_number": latest_stock.storegrn.grn_number if latest_stock.storegrn else None,
                    "exp_date":latest_stock.expiry_date,
                    "batch_no":latest_stock.batch_no,
                    "indent_number": (
                        latest_stock.storegrn.indent.indent_number
                        if latest_stock.storegrn and latest_stock.storegrn.indent
                        else None
                    ),
                })

        elif type == "Service":
            services = (
                Service.objects.filter(
                    category_id=category_id,
                    is_active=True
                )
                .select_related("subcategory")
                .order_by("id")
            )

            for service in services:
                data.append({
                    "service_id": service.id,
                    "service_name": service.name,
                    "description": service.description,
                    "price": service.price,
                    "subcategory": service.subcategory.name if service.subcategory else None,
                    "show_in_ecom": service.show_in_ecom,
                    "home_care_enabled": service.home_care_enabled,
                    "instore_enabled": service.instore_enabled,
                })

        else:
            return Response(
                {"success": False, "message": "Invalid type. Must be 'product' or 'service'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "success": True,
                "total_items": len(data),
                "data": data,
            },
            status=status.HTTP_200_OK
        )




class CustomerByMobileView(APIView):

    def get(self, request):
        mobile = request.query_params.get("mobile")

        customer = (Customer.objects.filter(contact=mobile).only("id", "name","contact").first())

        if not customer:
            return Response(
                {"success":False,"error": "Customer not found"})

        return Response(
            {"success":True,"id": customer.id, "name": customer.name,"mobile":customer.contact},status=status.HTTP_200_OK)




class InvoiceAPIView(APIView):

    def get(self, request):
        store_id = request.query_params.get("store_id")
        mobile_number = request.query_params.get("mobile_number")

        if not store_id:
            return JsonResponse(
                {"success": False, "message": "store_id is required"},
                status=400
            )

        # Base queryset: all invoices for the store
        invoices_qs = Invoice.objects.filter(store_id=store_id)

    
        if mobile_number:
            customer = Customer.objects.filter(contact=mobile_number).first() 
            if not customer:
                return JsonResponse(
                    {"success": False, "message": "Customer not found"},
                    status=404
                )
            invoices_qs = invoices_qs.filter(customer=customer)

        invoices = invoices_qs.prefetch_related("items").order_by("-created_at")

        data = []
        for inv in invoices:
            data.append({
                "invoice_no": inv.invoice_no,
                "status": inv.status,
                "total": float(inv.total),
                "created_at": inv.created_at,
                "items": [
                    {
                        "item_type": i.item_type,
                        "quantity": i.quantity,
                        "mrp": float(i.mrp),
                        "discount": float(i.discount),
                        "selling_price": float(i.selling_price),
                        "subtotal": float(i.Sub_total),
                        "stock_id": i.stock_id,
                        "service_id": i.service_id,
                        "package_id": i.package_id,
                    }
                    for i in inv.items.all()
                ],
            })

        return JsonResponse({"success": True, "data": data}, status=200)

    def post(self, request):
        store_id = request.data.get("store_id")
        mobile_number = request.data.get("mobile_number")
        payment_method = request.data.get("payment_method")
        items = request.data.get("products", [])

        if not store_id or not mobile_number or not items:
            return JsonResponse({"success": False, "message": "store_id, mobile_number and items are required"},status=400)

        customer = Customer.objects.filter(contact=mobile_number).first()

        if not customer:
            return JsonResponse(
                {"success": False, "message": "Customer not found"},status=404)

        with transaction.atomic():

            invoice = Invoice.objects.create(
                store_id=store_id,
                customer=customer,
                status="DRAFT",
                payment_method=payment_method,
                total=Decimal("0.00"),
            )

            invoice_items = []
            total_amount = Decimal("0.00")

            for item in items:
                item_type = item.get("item_type")
                qty = int(item.get("qty", 1))

                if qty <= 0:
                    return JsonResponse({"success": False, "message": "Quantity must be greater than 0"},status=400)

                mrp = Decimal(item.get("mrp", 0))
                discount = Decimal(item.get("discount", 0))
                selling_price = Decimal(item.get("selling_price", 0))
                subtotal = Decimal(item.get("subtotal", 0))

                if item_type == "Product":
                    batch_no = item.get("batch_no")
                    product_id = item.get("product_id")
                    stock = Stock.objects.select_for_update().filter( batch_no=batch_no, store_id=store_id ).first() 
                    if stock.stock < qty:
                        return JsonResponse(
                            {"success": False,"message": "Insufficient stock","batch_no": stock.batch_no,"available": stock.stock},status=400)

                    stock.stock -= qty
                    stock.save(update_fields=["stock"])

                    invoice_items.append(
                        InvoiceItem(
                            invoice=invoice,
                            item_type=item_type,
                            stock=stock,
                            quantity=qty,
                            mrp=mrp,
                            discount=discount,
                            selling_price=selling_price,
                            Sub_total=subtotal,
                        )
                    )

                elif item_type == "Service":

                    invoice_items.append(
                        InvoiceItem(
                            invoice=invoice,
                            item_type=item_type,
                            service_id=item.get("id"),
                            quantity=qty,
                            mrp=mrp,
                            discount=discount,
                            selling_price=selling_price,
                            Sub_total=subtotal,
                        )
                    )

                elif item_type == "Package":
                    invoice_items.append(
                        InvoiceItem(
                            invoice=invoice,
                            item_type=item_type,
                            package_id=item.get("package_id"),
                            quantity=qty,
                            mrp=mrp,
                            discount=discount,
                            selling_price=selling_price,
                            Sub_total=subtotal,
                        )
                    )

                else:
                    return JsonResponse(
                        {"success": False, "message": "Invalid item_type"},status=400)

                total_amount += subtotal

            InvoiceItem.objects.bulk_create(invoice_items)

            invoice.total = total_amount
            invoice.status = "FINAL"
            invoice.save(update_fields=["total", "status"])

        return JsonResponse(
            {
                "success": True,
                "invoice_id": invoice.id,
                "invoice_no": invoice.invoice_no,
                "total": float(invoice.total),
            },
            status=201,
        )
