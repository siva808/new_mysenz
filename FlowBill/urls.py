from django.urls import path
from .views import *
from .store import *

urlpatterns = [
   path('vendor/', VendorAPIView.as_view()),
   path('product/', ProductAPIView.as_view()),
   path('bulk-upload/', BulkUploadAPIView.as_view()),
   path('indent_status_list/', get_indent_details,name="indent_status_list"),# the status filter in to intent list
   path("indent_list/", get_intent_list, name="indent-list"),#the status list api 
   #path("get_vendor/",get_vendor, name="get_vendor"),
   path("create_indent/",create_indent,name="create_indent"),
   path("create_po/",create_purchase_order,name="create_purchase_order"),
   path("get_products/",get_products,name="get_products"),
   path("get_po_details/",get_po_details,name="get_po_details"),
   path("update_po_status/",po_update_status,name="update_po_status"),
   path("update_indent/",update_indent,name="update_indent"),
   path("UOMdropdown/",UOMdropdown,name="UOMdropdown"),
   path("create-grn/", create_grn),
   path("get_grn/",GRNView.as_view()),
   path("get_product_stock/", product_stock_list),
   path("dispatch_order/", DispatchAPIView.as_view()),
   path("recipe-view/", RecipeAPIView.as_view()),

]