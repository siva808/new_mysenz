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
    
    existing = GRN.objects.filter(request_id=request_id).first()
    if existing:
        return existing

    po = PurchaseOrder.objects.select_for_update().prefetch_related("items").get(id=po_id)
    if po.status == "cancelled":
        raise GRNError("PO is cancelled")

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

