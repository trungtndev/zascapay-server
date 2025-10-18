import json
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from ...models import Product, ProductCategory, Detection

class Command(BaseCommand):
    help = "Import Products + Detection from YOLO names with random price"

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Đường dẫn tới file yolo_names.json'
        )

    def handle(self, *args, **kwargs):
        file_path = kwargs['file']

        # 1️⃣ Load YOLO names từ file JSON
        try:
            with open(file_path, "r") as f:
                names = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Không đọc được file {file_path}: {e}"))
            return

        # 2️⃣ Tạo category mặc định
        category, _ = ProductCategory.objects.get_or_create(name="Default Category")

        # 3️⃣ Thêm Product + Detection
        for idx, class_name in names.items():
            sku = f"YOLO-{idx}"
            price = Decimal(random.uniform(10, 1000)).quantize(Decimal("0.01"))

            # Tạo Product nếu chưa tồn tại
            product, _ = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": class_name,
                    "category": category,
                    "status": Product.Status.ACTIVE,
                    "price": price
                }
            )

            # Tạo Detection FK map Product
            detection, created = Detection.objects.get_or_create(
                name=class_name,
                product=product,
                defaults={"accuracy": 0}  # mặc định 0
            )

            if created:
                self.stdout.write(f"Detection {class_name} -> Product {product.name} (Price: {price}) created")
            else:
                self.stdout.write(f"Product/Detection {class_name} đã tồn tại")
