from django.db.models.signals import post_migrate
from django.contrib.auth import get_user_model
from django.dispatch import receiver


@receiver(post_migrate)
def create_default_admin(sender, **kwargs):
    """
    Tự động tạo admin mặc định khi hệ thống khởi động lần đầu (sau migrate).
    """
    User = get_user_model()
    if not User.objects.filter(is_system_admin=True).exists():
        print("⚙️  Creating default system admin...")
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin",  # bạn nên thay trong môi trường thật!
            first_name="System",
            last_name="Admin",
        )
        admin.is_approved = True
        admin.is_system_admin = True
        admin.save()
        print("✅ Default system admin created: username=admin, password=admin")