# Zascapay – Hybrid View–API Architecture (Product Module)

This project uses a Hybrid View–API approach:
- Django View renders the HTML skeleton (layout and empty states).
- After the page loads, JavaScript calls REST APIs to fetch data and updates the DOM without a full page reload.

## Data Flow
1) User opens `/product/`.
2) Django view `product.views.product_list` renders `templates/product.html` (no product data embedded).
3) In-browser JS runs and calls the REST API:
   - `GET /product/api/categories/` to populate filters/forms.
   - `GET /product/api/products/metrics/` to populate KPI cards.
   - `GET /product/api/products/?…` to load the paginated table.
4) User actions (create/update/delete) trigger `fetch()` requests (POST/PATCH/DELETE). The page updates dynamically.

CSRF is handled via a cookie set by the view (`ensure_csrf_cookie`) and sent in `X-CSRFToken` header on write requests.

## Key Files
- `product/models.py` – `ProductCategory`, `Product` (with soft delete via `is_deleted`).
- `product/services.py` – Service layer with filtering, CRUD helpers, and metrics.
- `product/serializers.py` – DRF serializers with validation.
- `product/views.py` –
  - `product_list` renders the HTML shell and sets the CSRF cookie.
  - `ProductViewSet` and `ProductCategoryViewSet` delegate business logic to `services.py`.
- `product/urls.py` – Page route and DRF router under `/product/api/`.
- `templates/product.html` – HTML + vanilla JS that calls the REST API.

## REST Endpoints
Base: `/product/api/`

- Categories
  - `GET /categories/?search=&page=&page_size=`
  - `POST /categories/`
  - `GET /categories/{id}/`
  - `PATCH /categories/{id}/`
  - `DELETE /categories/{id}/`

- Products
  - `GET /products/?search=&status=&category=&page=&page_size=&ordering=`
  - `POST /products/`
  - `GET /products/{id}/`
  - `PATCH /products/{id}/`
  - `DELETE /products/{id}/` (soft delete)
  - `POST /products/{id}/restore/` (restore soft-deleted item)
  - `GET /products/metrics/` (KPI totals/averages)

Allowed `ordering`: `name`, `-name`, `sku`, `-sku`, `accuracy_rate`, `-accuracy_rate`, `detection_count`, `-detection_count`, `last_detected_at`, `-last_detected_at`, `last_updated_at`, `-last_updated_at`.

## Quick Start
Install deps (from repo root) and run Django dev server. The DB is configured for MySQL with a password taken from `DB_PASSWORD` env variable.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DB_PASSWORD='YOUR_MYSQL_PASSWORD'
python3 zascapay/manage.py migrate
python3 zascapay/manage.py runserver
```

Open the product UI:
- http://127.0.0.1:8000/product/

Optional: create seed data via API (example cURL):
```bash
# Create a category
curl -s -X POST http://127.0.0.1:8000/product/api/categories/ \
  -H 'Content-Type: application/json' \
  -d '{"name":"Đồ Uống","description":"Nước giải khát"}'

# Create a product (assumes the category id is 1)
curl -s -X POST http://127.0.0.1:8000/product/api/products/ \
  -H 'Content-Type: application/json' \
  -d '{
    "name":"Coca Cola 500ml",
    "sku":"CC-500-001",
    "category":1,
    "status":"active",
    "accuracy_rate":98.5,
    "detection_count":2847,
    "description":"Lon Đỏ Cổ Điển"
  }'
```

## Troubleshooting
- CSRF: The product page view sets the CSRF cookie so AJAX POST/PATCH/DELETE will work. If you test with cURL, you don’t need CSRF (sessionless), but browser JS requires it.
- Database: The default DB is remote MySQL. If you prefer SQLite for local dev, update `DATABASES` in `zascapay/zascapay/settings.py` accordingly.

## Architecture Benefits
- Fast, dynamic UX: Reload only the content that changes.
- Clean separation: Django templates for layout; services for business logic; DRF for transport.
- Easy to extend: Add endpoints or UI widgets without coupling templates to server data.
