from django.test import TestCase

# Create your tests here.
# apps/grn/utils.py
import uuid

def next_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"



# apps/grn/services.py
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from datetime import date

from MySenzApp.models import PurchaseOrder, PurchaseOrderItem, Product, Medicine
from .models import GRN, GRNItem
from .utils import next_id

class GRNError(Exception):
    pass

def _is_expired(expiry_date):
    if not expiry_date:
        return False
    return expiry_date < date.today()

def _po_fully_received(po: PurchaseOrder) -> bool:
    """
    Return True if sum of accepted_qty across GRNs for each PO item >= expected qty.
    """
    accepted = (
        GRNItem.objects.filter(grn__purchase_order=po)
        .values("product_id", "medicine_id", "grn__purchase_order")
        .annotate(total=Sum("accepted_qty"))
    )
    # Build map by PO item (product or medicine)
    acc_map = {}
    for r in accepted:
        # prefer product_id if present else medicine_id
        key = ("product", r.get("product_id")) if r.get("product_id") else ("medicine", r.get("medicine_id"))
        acc_map[key] = float(r["total"] or 0)

    for poi in po.items.all():
        if poi.product_id:
            key = ("product", poi.product_id)
        else:
            key = ("medicine", poi.medicine_id)
        expected = float(poi.qty)
        got = acc_map.get(key, 0.0)
        if got < expected:
            return False
    return True








@transaction.atomic
def create_grn_from_po(po_id: int, rows: list, request_id: str, actor: str = "system") -> GRN:
    """
    Create a warehouse GRN from a PO.

    rows: [
      {
        "purchase_order_item_id": 123,
        "product_id": 5,            # OR "medicine_id": 7
        "uom": "Nos",
        "accepted_qty": 18,
        "rejected_qty": 2,
        "batch_no": "B123",
        "expiry_date": "2026-06-30",
        "reason": "short"
      }, ...
    ]
    """
    # Idempotency: return existing GRN if request_id already processed
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

@transaction.atomic
def create_branch_grn_from_dispatch(dispatch_id: int, rows: list, request_id: str, actor: str = "system") -> GRN:
    """
    Create a branch/store GRN from a dispatch.

    rows: [
      {
        "item_id": 5,
        "product_id": 5,            # OR "medicine_id": 7
        "uom": "Nos",
        "batch_no": "B123",
        "expiry_date": "2026-06-30",
        "received_qty": 18,
        "missing_qty": 2,
        "damaged_qty": 0,
        "expired_qty": 0
      }, ...
    ]
    """
    # Idempotency
    existing = GRN.objects.filter(request_id=request_id).first()
    if existing:
        return existing

    # We don't have Dispatch model in your posted file; if you have one, validate dispatch here.
    # For now, we accept dispatch_id as informational and create GRN tied to the PO referenced in dispatch if available.
    # If you have a Dispatch model, replace the following with select_for_update on Dispatch and validation.
    # For simplicity, we will create GRN with purchase_order = first PO of the system (or None) if not available.
    # Better: pass purchase_order id in request or fetch from Dispatch.

    # Create GRN record (branch)
    grn_number = next_id(prefix=f"GRN-BR-{dispatch_id}-")
    # If you want to link to a PurchaseOrder, you can set purchase_order to None or to a related PO.
    grn = GRN.objects.create(
        grn_number=grn_number,
        grn_type="branch",
        purchase_order=None,
        status="Partial",
        dispatch_id=dispatch_id,
        request_id=request_id
    )

    grn_items = []
    for r in rows:
        product_id = r.get("product_id")
        medicine_id = r.get("medicine_id")
        item_id = r.get("item_id")  # optional duplicate of product_id/medicine_id
        uom = r.get("uom") or ""
        batch_no = (r.get("batch_no") or "").strip()
        expiry_date = r.get("expiry_date") or None
        received_qty = int(r.get("received_qty") or 0)
        missing_qty = int(r.get("missing_qty") or 0)
        damaged_qty = int(r.get("damaged_qty") or 0)
        expired_qty = int(r.get("expired_qty") or 0)

        # Expiry handling
        if expiry_date and _is_expired(expiry_date):
            if received_qty > 0:
                missing_qty += received_qty
                received_qty = 0

        gi = GRNItem(
            grn=grn,
            product_id=product_id if product_id else None,
            medicine_id=medicine_id if medicine_id else None,
            batch_no=batch_no,
            expiry_date=expiry_date,
            accepted_qty=received_qty,
            rejected_qty=(missing_qty + damaged_qty + expired_qty),
            uom=uom,
            reason="branch_inward"
        )
        grn_items.append(gi)

        # Update branch stock (we assume Product.stock and Medicine.stock represent global stock; if you track per-store stock separately, update that model instead)
        if received_qty > 0:
            if product_id:
                Product.objects.filter(id=product_id).update(stock=F('stock') + received_qty)
            elif medicine_id:
                Medicine.objects.filter(id=medicine_id).update(stock=F('stock') + received_qty)

    GRNItem.objects.bulk_create(grn_items)

    grn.confirmed_at = timezone.now()
    grn.status = "Full" if all(item.accepted_qty > 0 for item in grn.items.all()) else "Partial"
    grn.save(update_fields=["status", "confirmed_at"])
    return grn







# apps/grn/api/views.py
import csv, io
from datetime import datetime
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from apps.grn.services import create_grn_from_po, create_branch_grn_from_dispatch, GRNError

def _parse_int(v, default=0):
    try:
        return int(str(v).strip())
    except Exception:
        return default

def _parse_date(v):
    if not v:
        return None
    try:
        return datetime.strptime(v.strip(), "%Y-%m-%d").date()
    except Exception:
        return None

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_warehouse_grn(request):
    """
    JSON payload:
    {
      "po_id": 1,
      "request_id": "REQ-123",
      "rows": [ { purchase_order_item_id, product_id|medicine_id, uom, accepted_qty, rejected_qty, batch_no, expiry_date, reason }, ... ]
    }
    """
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

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_branch_grn(request):
    """
    JSON payload:
    {
      "dispatch_id": 10,
      "request_id": "REQ-456",
      "rows": [ { product_id|medicine_id, item_id(optional), uom, batch_no, expiry_date, received_qty, missing_qty, damaged_qty, expired_qty }, ... ]
    }
    """
    data = request.data
    dispatch_id = data.get("dispatch_id")
    request_id = data.get("request_id")
    rows = data.get("rows", [])

    if not dispatch_id or not request_id or not isinstance(rows, list):
        return Response({"detail": "dispatch_id, request_id and rows[] are required"}, status=status.HTTP_400_BAD_REQUEST)

    parsed = []
    for i, r in enumerate(rows, start=1):
        product_id = r.get("product_id")
        medicine_id = r.get("medicine_id")
        item_id = r.get("item_id")
        uom = r.get("uom") or ""
        batch_no = (r.get("batch_no") or "").strip()
        expiry_date = _parse_date(r.get("expiry_date"))
        received_qty = _parse_int(r.get("received_qty"))
        missing_qty = _parse_int(r.get("missing_qty"))
        damaged_qty = _parse_int(r.get("damaged_qty"))
        expired_qty = _parse_int(r.get("expired_qty"))

        if not (product_id or medicine_id):
            return Response({"detail": f"Row {i}: product_id or medicine_id required"}, status=400)
        if not batch_no:
            return Response({"detail": f"Row {i}: batch_no required"}, status=400)

        parsed.append({
            "product_id": product_id,
            "medicine_id": medicine_id,
            "item_id": item_id,
            "uom": uom,
            "batch_no": batch_no,
            "expiry_date": expiry_date,
            "received_qty": received_qty,
            "missing_qty": missing_qty,
            "damaged_qty": damaged_qty,
            "expired_qty": expired_qty
        })

    try:
        grn = create_branch_grn_from_dispatch(dispatch_id=int(dispatch_id), rows=parsed, request_id=str(request_id), actor=request.user.username)
    except GRNError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"grn_number": grn.grn_number, "grn_id": grn.id, "status": grn.status}, status=status.HTTP_201_CREATED)

# CSV upload endpoints

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_warehouse_grn_csv(request):
    """
    Multipart form-data:
      - po_id
      - request_id
      - file (CSV)
    CSV header must include:
      purchase_order_item_id,product_id,medicine_id,uom,accepted_qty,rejected_qty,batch_no,expiry_date,reason
    """
    po_id = request.data.get("po_id")
    request_id = request.data.get("request_id")
    upload = request.FILES.get("file")
    if not po_id or not request_id or not upload:
        return Response({"detail": "po_id, request_id and file are required"}, status=400)

    try:
        content = upload.read().decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(content))
    except Exception:
        return Response({"detail": "Invalid CSV"}, status=400)

    required = {"purchase_order_item_id", "uom", "accepted_qty", "rejected_qty", "batch_no", "expiry_date", "reason"}
    if not required.issubset(set(reader.fieldnames or [])):
        return Response({"detail": f"CSV missing required columns: {', '.join(sorted(required))}"}, status=400)

    rows = []
    errors = []
    line = 1
    for raw in reader:
        line += 1
        try:
            poi = _parse_int(raw.get("purchase_order_item_id"))
            product_id = raw.get("product_id") or None
            medicine_id = raw.get("medicine_id") or None
            uom = raw.get("uom") or ""
            accepted_qty = _parse_int(raw.get("accepted_qty"))
            rejected_qty = _parse_int(raw.get("rejected_qty"))
            batch_no = (raw.get("batch_no") or "").strip()
            expiry_date = raw.get("expiry_date") or None
            reason = raw.get("reason") or ""

            if not poi:
                errors.append(f"Line {line}: purchase_order_item_id required")
                continue
            if not (product_id or medicine_id):
                errors.append(f"Line {line}: product_id or medicine_id required")
                continue

            rows.append({
                "purchase_order_item_id": poi,
                "product_id": int(product_id) if product_id else None,
                "medicine_id": int(medicine_id) if medicine_id else None,
                "uom": uom,
                "accepted_qty": accepted_qty,
                "rejected_qty": rejected_qty,
                "batch_no": batch_no,
                "expiry_date": expiry_date,
                "reason": reason
            })
        except Exception as ex:
            errors.append(f"Line {line}: parse error {ex}")

    if errors:
        return Response({"detail": "CSV validation failed", "errors": errors}, status=400)
    if not rows:
        return Response({"detail": "No valid rows"}, status=400)

    try:
        grn = create_grn_from_po(po_id=int(po_id), rows=rows, request_id=str(request_id), actor=request.user.username)
    except GRNError as e:
        return Response({"detail": str(e)}, status=400)

    return Response({"grn_number": grn.grn_number, "grn_id": grn.id, "status": grn.status}, status=201)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_branch_grn_csv(request):
    """
    Multipart form-data:
      - dispatch_id
      - request_id
      - file (CSV)
    CSV header must include:
      product_id,medicine_id,uom,batch_no,expiry_date,received_qty,missing_qty,damaged_qty,expired_qty
    """
    dispatch_id = request.data.get("dispatch_id")
    request_id = request.data.get("request_id")
    upload = request.FILES.get("file")
    if not dispatch_id or not request_id or not upload:
        return Response({"detail": "dispatch_id, request_id and file are required"}, status=400)

    try:
        content = upload.read().decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(content))
    except Exception:
        return Response({"detail": "Invalid CSV"}, status=400)

    required = {"batch_no", "received_qty"}
    if not required.issubset(set(reader.fieldnames or [])):
        return Response({"detail": f"CSV missing required columns: {', '.join(sorted(required))}"}, status=400)

    rows = []
    errors = []
    line = 1
    for raw in reader:
        line += 1
        try:
            product_id = raw.get("product_id") or None
            medicine_id = raw.get("medicine_id") or None
            uom = raw.get("uom") or ""
            batch_no = (raw.get("batch_no") or "").strip()
            expiry_date = raw.get("expiry_date") or None
            received_qty = _parse_int(raw.get("received_qty"))
            missing_qty = _parse_int(raw.get("missing_qty"))
            damaged_qty = _parse_int(raw.get("damaged_qty"))
            expired_qty = _parse_int(raw.get("expired_qty"))

            if not (product_id or medicine_id):
                errors.append(f"Line {line}: product_id or medicine_id required")
                continue
            if not batch_no:
                errors.append(f"Line {line}: batch_no required")
                continue

            rows.append({
                "product_id": int(product_id) if product_id else None,
                "medicine_id": int(medicine_id) if medicine_id else None,
                "uom": uom,
                "batch_no": batch_no,
                "expiry_date": expiry_date,
                "received_qty": received_qty,
                "missing_qty": missing_qty,
                "damaged_qty": damaged_qty,
                "expired_qty": expired_qty
            })
        except Exception as ex:
            errors.append(f"Line {line}: parse error {ex}")

    if errors:
        return Response({"detail": "CSV validation failed", "errors": errors}, status=400)
    if not rows:
        return Response({"detail": "No valid rows"}, status=400)

    try:
        grn = create_branch_grn_from_dispatch(dispatch_id=int(dispatch_id), rows=rows, request_id=str(request_id), actor=request.user.username)
    except GRNError as e:
        return Response({"detail": str(e)}, status=400)

    return Response({"grn_number": grn.grn_number, "grn_id": grn.id, "status": grn.status}, status=201)





# apps/grn/api/urls.py
from django.urls import path
from .views import (
    create_warehouse_grn, create_branch_grn,
    upload_warehouse_grn_csv, upload_branch_grn_csv
)

urlpatterns = [
    path("grn/warehouse/create", create_warehouse_grn, name="grn-warehouse-create"),
    path("grn/branch/create", create_branch_grn, name="grn-branch-create"),
    path("grn/warehouse/upload-csv", upload_warehouse_grn_csv, name="grn-warehouse-upload-csv"),
    path("grn/branch/upload-csv", upload_branch_grn_csv, name="grn-branch-upload-csv"),
]



