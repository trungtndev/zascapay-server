import json
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from ...models import Product, ProductCategory, Detection
from store.models import Store, StoreInventory


class Command(BaseCommand):
    help = "Import Products + Detection from YOLO names and attach them to all existing stores with random per-store price"

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Đường dẫn tới file yolo_names.json'
        )
        parser.add_argument(
            '--quantity',
            type=int,
            default=0,
            help='Số lượng mặc định cho mỗi sản phẩm trong kho của từng store (mặc định 0)'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Xóa toàn bộ data cũ liên quan (Detection, StoreInventory, Product) trước khi nạp lại'
        )

    def handle(self, *args, **kwargs):
        file_path = kwargs['file']
        default_quantity = kwargs.get('quantity', 0)
        clean = kwargs.get('clean', False)

        if clean:
            self.stdout.write(self.style.WARNING("Đang xóa dữ liệu cũ: Detection, StoreInventory, Product liên quan..."))
            Detection.objects.all().delete()
            StoreInventory.objects.all().delete()
            Product.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Đã xóa dữ liệu cũ."))

        try:
            with open(file_path, "r") as f:
                names = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Không đọc được file {file_path}: {e}"))
            return

        category, _ = ProductCategory.objects.get_or_create(name="Default Category")

        stores = list(Store.objects.all())
        if not stores:
            self.stdout.write(self.style.WARNING("Không có store nào trong hệ thống. Vẫn tạo Product + Detection nhưng không map vào StoreInventory."))

        created_products = 0
        created_detections = 0
        created_inventory_links = 0

        for idx, class_name in names.items():
            sku = f"YOLO-{idx}"

            product, product_created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": class_name,
                    "category": category,
                    "status": Product.Status.ACTIVE,
                }
            )

            if product_created:
                created_products += 1
                self.stdout.write(self.style.SUCCESS(f"Product {class_name} (SKU: {sku}) created"))
            else:
                self.stdout.write(f"Product {class_name} (SKU: {sku}) đã tồn tại")

            detection, detection_created = Detection.objects.get_or_create(
                id=int(idx),
                name=class_name,
                product=product,
                defaults={"accuracy": 0}
            )

            if detection_created:
                created_detections += 1
                self.stdout.write(self.style.SUCCESS(f"Detection {class_name} -> Product {product.name} created"))
            else:
                self.stdout.write(f"Detection cho {class_name} đã tồn tại")

            for store in stores:
                random_price = Decimal(random.uniform(10, 50)).quantize(Decimal("0.01"))
                inv, inv_created = StoreInventory.objects.get_or_create(
                    store=store,
                    product=product,
                    defaults={"quantity": default_quantity, "price": random_price}
                )
                if inv_created:
                    created_inventory_links += 1

        self.stdout.write(self.style.SUCCESS(
            f"Hoàn tất import. Products mới: {created_products}, Detections mới: {created_detections}, "
            f"bản ghi StoreInventory mới: {created_inventory_links}"
        ))
