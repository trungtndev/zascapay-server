(function() {
  const API_BASE = '/api';
  const ENDPOINTS = {
    products: `${API_BASE}/products/`,
    productDetail: (id) => `${API_BASE}/products/${id}/`,
    restore: (id) => `${API_BASE}/products/${id}/restore/`,
    metrics: `${API_BASE}/products/metrics/`,
    export: `${API_BASE}/products/export/`,
    categories: `${API_BASE}/categories/`,
    categoryDetail: (id) => `${API_BASE}/categories/${id}/`,
  };
  const fmt = new Intl.NumberFormat('vi-VN');
  const $ = (sel) => document.querySelector(sel);

  const tbody = $('#productTbody');
  const searchInput = $('#searchInput');
  const statusFilter = $('#statusFilter');
  const categoryFilter = $('#categoryFilter');
  const prevBtn = $('#prevBtn');
  const nextBtn = $('#nextBtn');
  const pageInfo = $('#pageInfo');
  const kpiTotal = $('#kpiTotal');
  const kpiActive = $('#kpiActive');
  const kpiAvgAcc = $('#kpiAvgAcc');
  const kpiReview = $('#kpiReview');
  const openCreateBtn = $('#openCreateBtn');
  const productModal = $('#productModal');
  const closeModalBtn = $('#closeModalBtn');
  const saveProductBtn = $('#saveProductBtn');
  const exportBtn = $('#exportBtn');

  // View modal elements (new)
  const viewModal = $('#viewProductModal');
  const vpCloseBtn = $('#vpCloseBtn');
  const vpEditBtn = $('#vpEditBtn');
  const vpProductName = $('#vpProductName');
  const vpProductSubtitle = $('#vpProductSubtitle');
  const vpMainImage = $('#vpMainImage');
  const vpMainImageWrapper = $('#vpMainImageWrapper');
  const vpImages = $('#vpImages');
  const vpStatus = $('#vpStatus');
  const vpAccuracy = $('#vpAccuracy');
  const vpDetectionCount = $('#vpDetectionCount');
  const vpLastDetected = $('#vpLastDetected');
  const vpCategory = $('#vpCategory');
  const vpPrice = $('#vpPrice');
  const vpBarcode = $('#vpBarcode');
  const vpCreatedAt = $('#vpCreatedAt');

  // Fields in add modal form
  const fId = $('#productId');
  const fName = $('#fName');
  const fSku = $('#fSku');
  const fPrice = $('#fPrice');
  const fCategory = $('#fCategory');
  const fStatus = $('#fStatus');
  const fAccuracy = $('#fAccuracy');
  const fDetectCount = $('#fDetectCount');
  const fDesc = $('#fDesc');
  const formError = $('#formError');

  // Edit modal elements
  const editModal = $('#editProductModal');
  const closeEditModalBtn = $('#closeEditModalBtn');
  const cancelEditBtn = $('#cancelEditBtn');
  const saveEditBtn = $('#saveEditBtn');
  const editName = $('#editName');
  const editSku = $('#editSku');
  const editCategory = $('#editCategory');
  const editPrice = $('#editPrice');
  const editDesc = $('#editDesc');

  // Edit modal file upload refs
  const chooseEditFilesBtn = $('#chooseEditFilesBtn');
  const editFiles = $('#editFiles');
  const editDropZone = $('#editDropZone');
  const editFilePreviewContainer = $('#editFilePreviewContainer');
  const editFormError = $('#editFormError');

  // File / dropzone elements (may be null if not present)
  const chooseFilesBtn = $('#chooseFilesBtn');
  const fFiles = $('#fFiles');
  const dropZone = $('#dropZone');
  const filePreviewContainer = $('#filePreviewContainer');

  const state = { page: 1, page_size: 10, search: '', status: '', category: '', uploadFiles: [], editUploadFiles: [] };

  function getCSRFToken() {
    const name = 'csrftoken=';
    const parts = document.cookie.split(';');
    for (let p of parts) {
      p = p.trim();
      if (p.startsWith(name)) return decodeURIComponent(p.slice(name.length));
    }
    return '';
  }

  async function fetchJSON(url, options={}) {
    const opts = { headers: { 'Accept': 'application/json' }, ...options };
    const method = (opts.method || 'GET').toUpperCase();
    // always send cookies for same-origin requests so session auth works for GET
    opts.credentials = opts.credentials || 'same-origin';
    if (method !== 'GET') {
      opts.headers = { ...opts.headers, 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() };
    }
    const res = await fetch(url, opts);
    if (res.status === 401 || res.status === 403) {
      window.location.href = `/login/`;
      return Promise.reject(new Error('Unauthorized'));
    }
    if (!res.ok) {
      let tx = '';
      try { tx = await res.text(); } catch (_) { tx = res.statusText; }
      throw new Error(tx || res.statusText);
    }
    const ct = res.headers.get('content-type') || '';
    return ct.includes('application/json') ? res.json() : null;
  }

  function statusBadge(s) {
    if (s === 'active') return '<span class="inline-flex items-center rounded-full bg-blue-100 text-blue-700 px-2.5 py-1 text-xs font-medium">Hoạt Động</span>';
    if (s === 'training') return '<span class="inline-flex items-center rounded-full bg-indigo-700 text-white px-2.5 py-1 text-xs font-medium">Đang Huấn Luyện</span>';
    if (s === 'review') return '<span class="inline-flex items-center rounded-full bg-orange-600 text-white px-2.5 py-1 text-xs font-medium">Cần Xem Xét</span>';
    if (s === 'inactive') return '<span class="inline-flex items-center rounded-full bg-slate-200 text-slate-700 px-2.5 py-1 text-xs font-medium">Ngừng</span>';
    return s;
  }

  function timeAgo(iso) {
    if (!iso) return '-';
    const t = new Date(iso);
    const delta = Math.max(1, Math.floor((Date.now() - t.getTime()) / 1000));
    const m = Math.floor(delta/60), h = Math.floor(m/60), d = Math.floor(h/24);
    if (d > 0) return `${d} ngày trước`;
    if (h > 0) return `${h} giờ trước`;
    if (m > 0) return `${m} phút trước`;
    return 'vừa xong';
  }

  function escapeHtml(str){
    return String(str).replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[s]));
  }

  function rowHTML(p) {
    const acc = (p.accuracy_rate != null) ? `${Number(p.accuracy_rate).toFixed(1)}%` : '-';
    const det = fmt.format(p.detection_count || 0);
    const cat = p.category_name || '';
    const img = '<div class="h-10 w-10 rounded-lg bg-slate-200 grid place-content-center text-[10px] text-slate-500">IMG</div>';
    return `
      <tr class="border-t border-slate-100">
        <td class="px-4 py-4 align-top"><input type="checkbox"/></td>
        <td class="px-4 py-4">
          <div class="flex items-center gap-3">
            ${img}
            <div>
              <div class="font-medium">${escapeHtml(p.name)}</div>
              <div class="text-xs text-slate-500">${escapeHtml(p.description || '')}</div>
            </div>
          </div>
        </td>
        <td class="px-4 py-4">${escapeHtml(cat)}</td>
        <td class="px-4 py-4">${escapeHtml(p.sku)}</td>
        <td class="px-4 py-4">${statusBadge(p.status)}</td>
        <td class="px-4 py-4">${acc}</td>
        <td class="px-4 py-4">${det}</td>
        <td class="px-4 py-4">${timeAgo(p.last_updated_at)}</td>
        <td class="px-4 py-4">
          <div class="flex items-center gap-3 text-slate-500">
            <button class="hover:text-gem-dark" title="Xem" data-action="view" data-id="${p.id}">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 5c7 0 10 7 10 7s-3 7-10 7S2 12 2 12s3-7 10-7Zm0 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"/></svg>
            </button>
            <button class="hover:text-orange-600" title="Sửa" data-action="edit" data-id="${p.id}">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25Zm14.71-9.04a1.003 1.003 0 0 0 0-1.42l-2.5-2.5a1.003 1.003 0 0 0-1.42 0l-1.83 1.83 3.75 3.75 1.99-1.66Z"/></svg>
            </button>
            <button class="hover:text-red-600" title="Xóa" data-action="delete" data-id="${p.id}">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12ZM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4Z"/></svg>
            </button>
          </div>
        </td>
      </tr>`;
  }

  async function loadMetrics() {
    try {
      const data = await fetchJSON(ENDPOINTS.metrics);
      kpiTotal.textContent = fmt.format(data.total_products || 0);
      kpiActive.textContent = fmt.format(data.active_products || 0);
      kpiAvgAcc.textContent = (data.avg_accuracy_rate != null ? Number(data.avg_accuracy_rate).toFixed(1) + '%' : '--');
      kpiReview.textContent = fmt.format(data.review_count || 0);
    } catch (e) { console.warn('metrics', e); }
  }

  async function loadCategories() {
    try {
      const data = await fetchJSON(`${ENDPOINTS.categories}?page_size=100`);
      const items = data.results || data;
      if (categoryFilter) categoryFilter.innerHTML = '<option value="">Tất Cả Danh Mục</option>' + items.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
      if (fCategory) fCategory.innerHTML = items.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
      if (editCategory) editCategory.innerHTML = '<option value="">Chọn danh mục</option>' + items.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
    } catch (e) { console.warn('categories', e); }
  }

  function buildQuery() {
    const q = new URLSearchParams();
    if (state.search) q.set('search', state.search);
    if (state.status) q.set('status', state.status);
    if (state.category) q.set('category', state.category);
    q.set('page', state.page);
    q.set('page_size', state.page_size);
    q.set('ordering', '-last_updated_at');
    return q.toString();
  }

  async function loadProducts() {
    const url = `${ENDPOINTS.products}?${buildQuery()}`;
    if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="px-4 py-6 text-center text-slate-500">Đang tải...</td></tr>`;
    try {
      const data = await fetchJSON(url);
      const items = data.results || [];
      if (!items.length) {
        tbody.innerHTML = `<tr><td colspan="9" class="px-4 py-6 text-center text-slate-500">Không có dữ liệu</td></tr>`;
      } else {
        tbody.innerHTML = items.map(rowHTML).join('');
      }
      const count = data.count ?? items.length;
      const start = (state.page - 1) * state.page_size + 1;
      const end = Math.min(state.page * state.page_size, count);
      pageInfo.textContent = `Hiển thị ${start} đến ${end} của ${fmt.format(count)} sản phẩm`;
      prevBtn.disabled = !data.previous;
      nextBtn.disabled = !data.next;
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="9" class="px-4 py-6 text-center text-orange-600">Lỗi tải dữ liệu: ${escapeHtml(e.message)}</td></tr>`;
      pageInfo.textContent = '';
    }
  }

  // File handling utilities
  function renderPreviews() {
    if (!filePreviewContainer) return;
    filePreviewContainer.innerHTML = '';
    state.uploadFiles.forEach((file, idx) => {
      const url = URL.createObjectURL(file);
      const wrapper = document.createElement('div');
      wrapper.className = 'relative bg-[#c7daf7] rounded-xl p-2 flex items-center justify-center min-w-[120px] min-h-[80px]';
      const img = document.createElement('img');
      img.src = url;
      img.className = 'object-cover w-full h-full rounded-md';
      img.style.maxWidth = '160px';
      img.style.maxHeight = '120px';
      const del = document.createElement('button');
      del.type = 'button';
      del.innerText = '×';
      del.className = 'absolute -top-2 -right-2 bg-white rounded-full w-6 h-6 flex items-center justify-center';
      del.addEventListener('click', function(){
        URL.revokeObjectURL(url);
        state.uploadFiles.splice(idx, 1);
        renderPreviews();
      });
      wrapper.appendChild(img);
      wrapper.appendChild(del);
      filePreviewContainer.appendChild(wrapper);
    });
  }

  // Render previews for edit modal
  function renderEditPreviews() {
    if (!editFilePreviewContainer) return;
    editFilePreviewContainer.innerHTML = '';
    state.editUploadFiles.forEach((file, idx) => {
      const url = URL.createObjectURL(file);
      const wrapper = document.createElement('div');
      wrapper.className = 'relative bg-[#c7daf7] rounded-xl p-2 flex items-center justify-center min-w-[120px] min-h-[80px]';
      const img = document.createElement('img');
      img.src = url;
      img.className = 'object-cover w-full h-full rounded-md';
      img.style.maxWidth = '160px';
      img.style.maxHeight = '120px';
      const del = document.createElement('button');
      del.type = 'button';
      del.innerText = '×';
      del.className = 'absolute -top-2 -right-2 bg-white rounded-full w-6 h-6 flex items-center justify-center';
      del.addEventListener('click', function(){
        URL.revokeObjectURL(url);
        state.editUploadFiles.splice(idx, 1);
        renderEditPreviews();
      });
      wrapper.appendChild(img);
      wrapper.appendChild(del);
      editFilePreviewContainer.appendChild(wrapper);
    });
  }

  function addFiles(files) {
    const arr = Array.from(files || []);
    arr.forEach(f => {
      if (!f.type.startsWith('image/')) return;
      // avoid duplicate by name+size
      const exists = state.uploadFiles.some(x => x.name === f.name && x.size === f.size);
      if (!exists) state.uploadFiles.push(f);
    });
    renderPreviews();
  }

  // Add files for edit modal
  function addEditFiles(files) {
    const arr = Array.from(files || []);
    arr.forEach(f => {
      if (!f.type.startsWith('image/')) return;
      const exists = state.editUploadFiles.some(x => x.name === f.name && x.size === f.size);
      if (!exists) state.editUploadFiles.push(f);
    });
    renderEditPreviews();
  }

  // Modal open/close and populate for add modal
  function openModal(mode, product) {
    if (!productModal) return;
    productModal.classList.remove('hidden');
    productModal.classList.add('flex');
    if (formError) { formError.classList.add('hidden'); formError.textContent = ''; }
    const titleEl = document.getElementById('modalTitle') || document.getElementById('productModalTitle');
    if (titleEl) titleEl.textContent = mode === 'create' ? 'Thêm Sản Phẩm Mới' : 'Cập Nhật Sản Phẩm';
    state.uploadFiles = [];
    renderPreviews();
    if (mode === 'create') {
      if (fId) fId.value = '';
      if (fName) fName.value = '';
      if (fSku) fSku.value = '';
      if (fCategory) fCategory.value = categoryFilter ? categoryFilter.value || '' : '';
      if (fStatus) fStatus.value = 'active';
      if (fAccuracy) fAccuracy.value = '';
      if (fDetectCount) fDetectCount.value = '';
      if (fDesc) fDesc.value = '';
    } else if (product) {
      if (fId) fId.value = product.id;
      if (fName) fName.value = product.name || '';
      if (fSku) fSku.value = product.sku || '';
      if (fCategory) fCategory.value = product.category || '';
      if (fStatus) fStatus.value = product.status || 'active';
      if (fAccuracy) fAccuracy.value = product.accuracy_rate ?? '';
      if (fDetectCount) fDetectCount.value = product.detection_count ?? '';
      if (fDesc) fDesc.value = product.description || '';
    }
  }

  function closeModal() {
    if (!productModal) return;
    productModal.classList.add('hidden');
    productModal.classList.remove('flex');
    state.uploadFiles = [];
    renderPreviews();
  }

  // Edit modal handlers
  function openEditModal(product) {
    if (!editModal) return;
    editModal.classList.remove('hidden');
    editModal.classList.add('flex');
    // populate
    if (product) {
      if (editName) editName.value = product.name || '';
      if (editSku) editSku.value = product.sku || '';
      if (editCategory) editCategory.value = product.category || '';
      if (editPrice) editPrice.value = product.price ?? '';
      if (editDesc) editDesc.value = product.description || '';
      // store product id on modal for save
      editModal.dataset.productId = product.id;
    }
    // reset edit upload files preview
    state.editUploadFiles = [];
    renderEditPreviews();
    // clear any prior error message
    if (editFormError) { editFormError.textContent = ''; editFormError.classList.add('hidden'); }
  }

  function closeEditModal() {
    if (!editModal) return;
    editModal.classList.add('hidden');
    editModal.classList.remove('flex');
    delete editModal.dataset.productId;
    // cleanup edit upload files
    state.editUploadFiles.forEach(f => { try { URL.revokeObjectURL(f); } catch(_){} });
    state.editUploadFiles = [];
    renderEditPreviews();
    // clear any prior error message
    if (editFormError) { editFormError.textContent = ''; editFormError.classList.add('hidden'); }
  }

  async function saveEditProduct() {
    if (!editModal) return;
    const id = editModal.dataset.productId;
    if (!id) {
      if (editFormError) { editFormError.textContent = 'Không có sản phẩm để lưu'; editFormError.classList.remove('hidden'); }
      return;
    }
    // validation
    if (!editName || !editName.value.trim()) {
      if (editFormError) { editFormError.textContent = 'Vui lòng nhập tên sản phẩm'; editFormError.classList.remove('hidden'); }
      return;
    }
    if (!editSku || !editSku.value.trim()) {
      if (editFormError) { editFormError.textContent = 'Vui lòng nhập mã SKU'; editFormError.classList.remove('hidden'); }
      return;
    }

    const payload = {
      name: editName.value.trim(),
      sku: editSku.value.trim(),
      category: editCategory && editCategory.value ? Number(editCategory.value) : null,
      price: editPrice && editPrice.value ? Number(editPrice.value) : null,
      description: editDesc ? editDesc.value.trim() : ''
    };

    saveEditBtn.disabled = true;
    const orig = saveEditBtn.textContent;
    saveEditBtn.textContent = 'Đang lưu...';
    try {
      // If there are edit files use multipart
      if (state.editUploadFiles && state.editUploadFiles.length > 0) {
        const formData = new FormData();
        formData.append('name', payload.name);
        formData.append('sku', payload.sku);
        if (payload.category) formData.append('category', payload.category);
        if (payload.price != null) formData.append('price', payload.price);
        formData.append('description', payload.description);
        state.editUploadFiles.forEach((file) => formData.append('images', file));

        const res = await fetch(ENDPOINTS.productDetail(id), {
          method: 'PUT',
          body: formData,
          headers: { 'X-CSRFToken': getCSRFToken() },
          credentials: 'same-origin'
        });
        if (!res.ok) {
          const txt = await res.text();
          if (editFormError) { editFormError.textContent = txt || res.statusText; editFormError.classList.remove('hidden'); }
          throw new Error(txt || res.statusText);
        }
      } else {
        await fetchJSON(ENDPOINTS.productDetail(id), { method: 'PUT', body: JSON.stringify(payload) });
      }
      closeEditModal();
      await loadProducts();
    } catch (e) {
      if (editFormError) { editFormError.textContent = e.message || 'Lưu thất bại'; editFormError.classList.remove('hidden'); } else {
        alert('Lưu thất bại: ' + (e.message || ''));
      }
    } finally {
      saveEditBtn.disabled = false;
      saveEditBtn.textContent = orig;
    }
  }

  function validateForm() {
    if (!formError) return true;
    formError.textContent = '';
    formError.classList.add('hidden');
    if (!fName || !fName.value.trim()) {
      formError.textContent = 'Vui lòng nhập tên sản phẩm';
      formError.classList.remove('hidden');
      return false;
    }
    if (!fSku || !fSku.value.trim()) {
      formError.textContent = 'Vui lòng nhập mã SKU';
      formError.classList.remove('hidden');
      return false;
    }
    return true;
  }

  async function createOrUpdateProduct() {
    if (!validateForm()) return;
    const payload = {
      name: fName ? fName.value.trim() : '',
      sku: fSku ? fSku.value.trim() : '',
      price: fPrice && fPrice.value ? Number(fPrice.value) : null,
      category: fCategory && fCategory.value ? Number(fCategory.value) : null,
      status: fStatus ? fStatus.value : 'active',
      accuracy_rate: fAccuracy && fAccuracy.value ? Number(fAccuracy.value) : null,
      detection_count: fDetectCount && fDetectCount.value ? Number(fDetectCount.value) : 0,
      description: fDesc ? fDesc.value.trim() : ''
    };
    const id = fId && fId.value ? fId.value : null;
    const url = id ? ENDPOINTS.productDetail(id) : ENDPOINTS.products;
    const method = id ? 'PUT' : 'POST';

    saveProductBtn.disabled = true;
    const originalLabel = saveProductBtn.textContent;
    saveProductBtn.textContent = 'Đang lưu...';

    // DEBUG: show payload in console to verify price is present
    try { console.log('Creating/updating product payload', payload, 'uploadFiles:', state.uploadFiles.length); } catch(e){}

    try {
      // If there are files to upload, send multipart/form-data
      if (state.uploadFiles && state.uploadFiles.length > 0) {
        const formData = new FormData();
        formData.append('name', payload.name);
        formData.append('sku', payload.sku);
        if (payload.price != null) formData.append('price', payload.price);
        if (payload.category) formData.append('category', payload.category);
        formData.append('status', payload.status);
        if (payload.accuracy_rate != null) formData.append('accuracy_rate', payload.accuracy_rate);
        formData.append('detection_count', payload.detection_count);
        formData.append('description', payload.description);
        state.uploadFiles.forEach((file, idx) => formData.append('images', file));

        const res = await fetch(url, {
          method,
          body: formData,
          headers: { 'X-CSRFToken': getCSRFToken() },
          credentials: 'same-origin'
        });
        if (!res.ok) {
          const txt = await res.text();
          throw new Error(txt || res.statusText);
        }
      } else {
        // JSON path
        await fetchJSON(url, { method, body: JSON.stringify(payload) });
      }

      closeModal();
      await loadProducts();
    } catch (e) {
      if (formError) {
        formError.textContent = e.message || 'Không thể lưu dữ liệu';
        formError.classList.remove('hidden');
      } else {
        alert(e.message || 'Không thể lưu dữ liệu');
      }
    } finally {
      saveProductBtn.disabled = false;
      saveProductBtn.textContent = originalLabel;
    }
  }

  async function exportProducts() {
    try {
      const url = `${ENDPOINTS.export}?${buildQuery()}`;
      const a = document.createElement('a');
      a.href = url;
      a.download = 'products.csv';
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (e) {
      console.warn('export', e);
    }
  }

  // Functions to open/close and populate the view modal
  function openViewModal(product) {
    if (!viewModal) {
      console.error('openViewModal: view modal not found');
      return;
    }
    // populate fields safely
    if (vpProductName) vpProductName.textContent = product?.name || '';
    const catName = product?.category_name ?? (product?.category ? product.category : '');
    if (vpProductSubtitle) vpProductSubtitle.textContent = `${catName} • Mã SP: ${product?.sku || ''}`;

    // If product has an image_url show image section; otherwise hide image containers
    if (product?.image_url) {
      if (vpMainImage) { vpMainImage.src = product.image_url; vpMainImage.classList.remove('hidden'); }
      if (vpMainImageWrapper) vpMainImageWrapper.classList.remove('hidden');
      if (vpImages) {
        vpImages.classList.remove('hidden');
        vpImages.innerHTML = '';
        const imgs = [product.image_url, '/static/images/details-1.svg', '/static/images/details-2.svg'];
        imgs.forEach(u => {
          const d = document.createElement('div');
          d.className = 'thumb';
          const im = document.createElement('img');
          im.src = u;
          d.appendChild(im);
          vpImages.appendChild(d);
        });
      }
    } else {
      if (vpMainImage) vpMainImage.classList.add('hidden');
      if (vpMainImageWrapper) vpMainImageWrapper.classList.add('hidden');
      if (vpImages) { vpImages.classList.add('hidden'); vpImages.innerHTML = ''; }
    }

    if (vpStatus) vpStatus.textContent = product?.status_display || product?.status || '—';
    if (vpAccuracy) vpAccuracy.textContent = (product?.accuracy_rate != null ? Number(product.accuracy_rate).toFixed(1) + '%' : '—');
    if (vpDetectionCount) vpDetectionCount.textContent = fmt.format(product?.detection_count || 0);
    if (vpLastDetected) vpLastDetected.textContent = (product?.last_detected_at ? timeAgo(product.last_detected_at) : 'Chưa phát hiện');
    if (vpCategory) vpCategory.textContent = product?.category_name || catName || '—';
    if (vpPrice) vpPrice.textContent = (product?.price != null ? fmt.format(product.price) + ' VNĐ' : '—');
    if (vpBarcode) vpBarcode.textContent = product?.sku || '—';
    if (vpCreatedAt) vpCreatedAt.textContent = product?.created_at ? new Date(product.created_at).toLocaleString('vi-VN') : '—';

    // store id for edit
    if (vpEditBtn && product?.id) vpEditBtn.dataset.productId = product.id;

    // show modal
    viewModal.classList.remove('hidden');
    viewModal.classList.add('flex');
  }

  function closeViewModal() {
    if (!viewModal) return;
    viewModal.classList.add('hidden');
    viewModal.classList.remove('flex');
    if (vpEditBtn) delete vpEditBtn.dataset.productId;
  }

  // wire view modal buttons
  if (vpCloseBtn) vpCloseBtn.addEventListener('click', closeViewModal);
  if (vpEditBtn) vpEditBtn.addEventListener('click', () => {
    const id = vpEditBtn.dataset.productId;
    if (!id) { closeViewModal(); return; }
    fetchJSON(ENDPOINTS.productDetail(id)).then(p => { closeViewModal(); openEditModal(p); }).catch(e => { console.warn('opening edit from view modal failed', e); });
  });

  // Event bindings (guard for nulls)
  if (searchInput) searchInput.addEventListener('input', () => { state.search = searchInput.value.trim(); state.page = 1; loadProducts(); });
  if (statusFilter) statusFilter.addEventListener('change', () => { state.status = statusFilter.value; state.page = 1; loadProducts(); });
  if (categoryFilter) categoryFilter.addEventListener('change', () => { state.category = categoryFilter.value; state.page = 1; loadProducts(); });
  if (prevBtn) prevBtn.addEventListener('click', () => { if (state.page > 1) { state.page--; loadProducts(); }});
  if (nextBtn) nextBtn.addEventListener('click', () => { state.page++; loadProducts(); });
  if (openCreateBtn) openCreateBtn.addEventListener('click', () => openModal('create'));
  if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
  if (saveProductBtn) saveProductBtn.addEventListener('click', createOrUpdateProduct);
  if (exportBtn) exportBtn.addEventListener('click', exportProducts);

  // Edit modal bindings
  if (closeEditModalBtn) closeEditModalBtn.addEventListener('click', closeEditModal);
  if (cancelEditBtn) cancelEditBtn.addEventListener('click', closeEditModal);
  if (saveEditBtn) saveEditBtn.addEventListener('click', saveEditProduct);

  // Table action delegation
  if (tbody) tbody.addEventListener('click', async (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const id = btn.dataset.id;
    const action = btn.dataset.action;
    if (!id || !action) return;

    if (action === 'edit') {
      try {
        const product = await fetchJSON(ENDPOINTS.productDetail(id));
        // open dedicated edit modal (visual matches the image)
        openEditModal(product);
      } catch (e) { console.warn('detail', e); }
    } else if (action === 'delete') {
      if (!confirm('Bạn có chắc muốn xóa sản phẩm này?')) return;
      try {
        await fetchJSON(ENDPOINTS.productDetail(id), { method: 'DELETE' });
        await loadProducts();
      } catch (e) { alert('Xóa thất bại: ' + (e.message || '')); }
    } else if (action === 'view') {
      try {
        const product = await fetchJSON(ENDPOINTS.productDetail(id));
        openViewModal(product);
      } catch (e) { console.warn('view', e); }
    }
  });

  // Dropzone and file selection handlers
  if (chooseFilesBtn && fFiles) {
    chooseFilesBtn.addEventListener('click', () => fFiles.click());
    fFiles.addEventListener('change', (ev) => {
      addFiles(ev.target.files);
      // reset input so same file can be reselected
      fFiles.value = '';
    });
  }

  if (dropZone) {
    ['dragenter','dragover'].forEach(evt => dropZone.addEventListener(evt, (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.add('ring-2','ring-gem-mid'); }));
    ['dragleave','drop'].forEach(evt => dropZone.addEventListener(evt, (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.remove('ring-2','ring-gem-mid'); }));
    dropZone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      if (dt && dt.files) addFiles(dt.files);
    });
  }

  // Edit modal file handlers
  if (chooseEditFilesBtn && editFiles) {
    chooseEditFilesBtn.addEventListener('click', () => editFiles.click());
    editFiles.addEventListener('change', (ev) => {
      addEditFiles(ev.target.files);
      editFiles.value = '';
    });
  }

  if (editDropZone) {
    ['dragenter','dragover'].forEach(evt => editDropZone.addEventListener(evt, (e) => { e.preventDefault(); e.stopPropagation(); editDropZone.classList.add('ring-2','ring-gem-mid'); }));
    ['dragleave','drop'].forEach(evt => editDropZone.addEventListener(evt, (e) => { e.preventDefault(); e.stopPropagation(); editDropZone.classList.remove('ring-2','ring-gem-mid'); }));
    editDropZone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      if (dt && dt.files) addEditFiles(dt.files);
    });
  }

  // cancel button inside modal
  const cancelBtn = $('#cancelAddProductBtn');
  if (cancelBtn) cancelBtn.addEventListener('click', (e) => { e.preventDefault(); closeModal(); });

  // cancel edit buttons already wired earlier (closeEditModal and cancelEditBtn)

  // Init
  loadMetrics();
  loadCategories();
  loadProducts();
})();
