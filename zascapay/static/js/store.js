(function() {
  const API_BASE = '/api';
  const ENDPOINTS = {
    stores: `${API_BASE}/stores/`,
    storeDetail: (id) => `${API_BASE}/stores/${id}/`,
    restore: (id) => `${API_BASE}/stores/${id}/restore/`,
    metrics: `${API_BASE}/stores/metrics/`,
    export: `${API_BASE}/stores/export/`,
    categories: `${API_BASE}/categories/`
  };
  // bulk endpoints
  ENDPOINTS.bulkRestart = `${API_BASE}/stores/bulk_restart/`;
  ENDPOINTS.bulkAlert = `${API_BASE}/stores/bulk_alert/`;
  ENDPOINTS.bulkUpdateModel = `${API_BASE}/stores/bulk_update_model/`;
  ENDPOINTS.bulkConfigure = `${API_BASE}/stores/bulk_configure/`;
  const fmt = new Intl.NumberFormat('vi-VN');
  const $ = (sel) => document.querySelector(sel);

  const tbody = $('#storeTbody');
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
  const storeModal = $('#add_store_model');
  const closeModalBtn = $('#closeModalBtn');
  const saveStoreBtn = $('#saveStoreBtn');
  const exportBtn = $('#exportBtn');
  // header 'select all' checkbox in table has id="selectAll" in templates/store.html
  // Use a getter to fetch the checkbox element at use-time. This is resilient to
  // different script load orders and avoids ReferenceError if other code
  // attempts to access the element before this module runs.
  function getSelectAllCheckbox() { return document.querySelector('#selectAll'); }

  // small UI hooks for new store modal: confidence range/value
  const confidenceRange = $('#confidenceRange');
  const confidenceValue = $('#confidenceValue');
  // decimal confidence inputs used in updated templates (0..1)
  const confidenceDecimal = $('#confidenceDecimal');
  const confidenceDecimalLabel = $('#confidenceDecimalLabel');

  // View modal elements
  const viewModal = $('#view_store_model');
  const vsCloseBtn = $('#vsCloseBtn');
  const vsEditBtn = $('#vsEditBtn');
  const vsStoreName = $('#vsStoreName');
  const vsStoreSubtitle = $('#vsStoreSubtitle');
  const vsMainImage = $('#vsMainImage');
  const vsMainImageWrapper = $('#vsMainImageWrapper');
  const vsImages = $('#vsImages');
  const vsStatus = $('#vsStatus');
  const vsAccuracy = $('#vsAccuracy');
  const vsDetectionCount = $('#vsDetectionCount');
  const vsLastDetected = $('#vsLastDetected');
  const vsCategory = $('#vsCategory');
  const vsAddress = $('#vsAddress');
  const vsCreatedAt = $('#vsCreatedAt');

  // Fields in add modal form
  const fId = $('#storeId');
  const fName = $('#fName');
  const fCode = $('#fCode');
  const fAddress = $('#fAddress');
  const fCategory = $('#fCategory');
  const fStatus = $('#fStatus');
  const fDesc = $('#fDesc');
  const formError = $('#formError');

  // Edit modal elements
  const editModal = $('#edit_store_model');
  const closeEditModalBtn = $('#closeEditModalBtn');
  const cancelEditBtn = $('#cancelEditBtn');
  const saveEditBtn = $('#saveEditBtn');
  const editName = $('#editName');
  const editCode = $('#editCode');
  const editCategory = $('#editCategory');
  const editAddress = $('#editAddress');
  const editDesc = $('#editDesc');
  const editFormError = $('#editFormError');
  // additional edit modal fields (match the richer template)
  const editIp = $('#editIp');
  const editPort = $('#editPort');
  const editModelVersion = $('#editModelVersion');
  const editConfidenceDecimal = $('#editConfidenceDecimal');
  const editConfidenceDecimalLabel = $('#editConfidenceDecimalLabel');
  const editFrequency = $('#editFrequency');
  const editStatus = $('#editStatus');
  const editAutoFeedback = $('#editAutoFeedback');
  const editCollectUncertain = $('#editCollectUncertain');
  const editAutoErrorReport = $('#editAutoErrorReport');

  const state = { page: 1, page_size: 10, search: '', status: '', category: '' };

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
      let tx;
      try { tx = await res.text(); } catch (_) { tx = res.statusText; }
      throw new Error(tx || res.statusText);
    }
    const ct = res.headers.get('content-type') || '';
    return ct.includes('application/json') ? res.json() : null;
  }

  function statusBadge(s) {
    if (s === 'active') return '<span class="inline-flex items-center rounded-full bg-blue-100 text-blue-700 px-2.5 py-1 text-xs font-medium">Hoạt Động</span>';
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

  function rowHTML(s) {
    const acc = (s.accuracy_rate != null) ? `${Number(s.accuracy_rate).toFixed(1)}%` : '-';
    const det = fmt.format(s.detection_count || 0);
    const cat = s.category_name || '';
    const img = '<div class="h-10 w-10 rounded-lg bg-slate-200 grid place-content-center text-[10px] text-slate-500">IMG</div>';
    return `
      <tr class="border-t border-slate-100">
        <td class="px-4 py-4 align-top"><input type="checkbox" class="row-select" data-id="${s.id}"/></td>
        <td class="px-4 py-4">
          <div class="flex items-center gap-3">
            ${img}
            <div>
              <div class="font-medium">${escapeHtml(s.name)}</div>
              <div class="text-xs text-slate-500">${escapeHtml(s.address || '')}</div>
            </div>
          </div>
        </td>
        <td class="px-4 py-4">${escapeHtml(cat)}</td>
        <td class="px-4 py-4">${escapeHtml(s.code)}</td>
        <td class="px-4 py-4">${statusBadge(s.status)}</td>
        <td class="px-4 py-4">${acc}</td>
        <td class="px-4 py-4">${det}</td>
        <td class="px-4 py-4">${timeAgo(s.last_updated_at)}</td>
        <td class="px-4 py-4">
          <div class="flex items-center gap-3 text-slate-500">
            <button class="hover:text-gem-dark" title="Xem" data-action="view" data-id="${s.id}">
              <svg class="h-4 w-4" viewBox="0 0 24 24" style="fill:currentColor"><path d="M12 5c7 0 10 7 10 7s-3 7-10 7S2 12 2 12s3-7 10-7Zm0 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"/></svg>
            </button>
            <button class="hover:text-orange-600" title="Sửa" data-action="edit" data-id="${s.id}">
              <svg class="h-4 w-4" viewBox="0 0 24 24" style="fill:currentColor"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25Zm14.71-9.04a1.003 1.003 0 0 0 0-1.42l-2.5-2.5a1.003 1.003 0 0 0-1.42 0l-1.83 1.83 3.75 3.75 1.99-1.66Z"/></svg>
            </button>
            <button class="hover:text-red-600" title="Xóa" data-action="delete" data-id="${s.id}">
              <svg class="h-4 w-4" viewBox="0 0 24 24" style="fill:currentColor"><path d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12ZM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4Z"/></svg>
            </button>
          </div>
        </td>
      </tr>`;
  }

  async function loadMetrics() {
    try {
      const data = await fetchJSON(ENDPOINTS.metrics);
      kpiTotal.textContent = fmt.format(data.total_stores || 0);
      kpiActive.textContent = fmt.format(data.active_stores || 0);
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

  async function loadStores() {
    const url = `${ENDPOINTS.stores}?${buildQuery()}`;
    if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="px-4 py-6 text-center text-slate-500">Đang tải...</td></tr>`;
    try {
      const data = await fetchJSON(url);
      const items = data.results || [];
      if (!items.length) {
        tbody.innerHTML = `<tr><td colspan="9" class="px-4 py-6 text-center text-slate-500">Không có dữ liệu</td></tr>`;
      } else {
        tbody.innerHTML = items.map(rowHTML).join('');
        // uncheck selectAll after rendering
        const selAll = getSelectAllCheckbox();
        if (selAll) selAll.checked = false;
        // ensure select-all listener is attached (defensive: some pages may load scripts before element exists)
        if (selAll && !selAll.dataset.listenerAttached) {
        if (selAll && !selAll.dataset.listenerAttached) {
          selAll.addEventListener('change', (e) => {
            const checked = e.target.checked;
            document.querySelectorAll('.row-select').forEach(r => r.checked = checked);
          });
        }
          selAll.dataset.listenerAttached = '1';
        }
      }
      const count = data.count ?? items.length;
      const start = (state.page - 1) * state.page_size + 1;
      const end = Math.min(state.page * state.page_size, count);
      pageInfo.textContent = `Hiển thị ${start} đến ${end} của ${fmt.format(count)} cửa hàng`;
      prevBtn.disabled = !data.previous;
      nextBtn.disabled = !data.next;
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="9" class="px-4 py-6 text-center text-orange-600">Lỗi tải dữ liệu: ${escapeHtml(e.message)}</td></tr>`;
      pageInfo.textContent = '';
    }
  }

  function openModal(mode, store) {
    if (!storeModal) return;
    storeModal.classList.remove('hidden');
    storeModal.classList.add('flex');
    if (formError) { formError.classList.add('hidden'); formError.textContent = ''; }
    const titleEl = document.getElementById('modalTitle');
    if (titleEl) titleEl.textContent = mode === 'create' ? 'Thêm Cửa Hàng Mới' : 'Cập Nhật Cửa Hàng';
    if (mode === 'create') {
      if (fId) fId.value = '';
      if (fName) fName.value = '';
      if (fCode) fCode.value = '';
      if (fAddress) fAddress.value = '';
      if (fCategory) fCategory.value = categoryFilter ? categoryFilter.value || '' : '';
      if (fStatus) fStatus.value = 'active';
      if (fDesc) fDesc.value = '';
      // set default confidence when creating
      if (confidenceRange) confidenceRange.value = confidenceRange.value || '85';
      if (confidenceValue && confidenceRange) confidenceValue.textContent = confidenceRange.value + '%';
    } else if (store) {
      if (fId) fId.value = store.id;
      if (fName) fName.value = store.name || '';
      if (fCode) fCode.value = store.code || '';
      if (fAddress) fAddress.value = store.address || '';
      if (fCategory) fCategory.value = store.category || '';
      if (fStatus) fStatus.value = store.status || 'active';
      if (fDesc) fDesc.value = store.description || '';
      // if the store has a saved confidence value, set the slider
      if (typeof store.confidence !== 'undefined' && confidenceRange) {
        confidenceRange.value = String(store.confidence);
        if (confidenceValue) confidenceValue.textContent = confidenceRange.value + '%';
      } else if (confidenceRange && confidenceValue) {
        // fallback ensure UI synced
        confidenceValue.textContent = confidenceRange.value + '%';
      }
    }
  }

  function closeModal() {
    if (!storeModal) return;
    storeModal.classList.add('hidden');
    storeModal.classList.remove('flex');
  }

  function openEditModal(store) {
    if (!editModal) return;
    editModal.classList.remove('hidden');
    editModal.classList.add('flex');
    if (store) {
      if (editName) editName.value = store.name || '';
      if (editCode) editCode.value = store.code || '';
      if (editCategory) editCategory.value = store.category || '';
      if (editAddress) editAddress.value = store.address || '';
      if (editDesc) editDesc.value = store.description || '';
      // optional UI-only fields: populate when available from API or leave defaults
      if (editIp) editIp.value = store.ip_address || '';
      if (editPort) editPort.value = store.port || '';
      if (editModelVersion) editModelVersion.value = store.model_version || '';
      if (editFrequency) editFrequency.value = store.frequency || editFrequency.value || '24';
      if (editStatus) editStatus.value = store.status || 'active';
      if (editAutoFeedback) editAutoFeedback.checked = !!store.auto_feedback;
      if (editCollectUncertain) editCollectUncertain.checked = !!store.collect_uncertain;
      if (editAutoErrorReport) editAutoErrorReport.checked = !!store.auto_error_report;
      // confidence/accuracy mapping: prefer write-only 'confidence' if present, otherwise use accuracy_rate as fallback
      if (editConfidenceDecimal) {
        if (typeof store.confidence !== 'undefined' && store.confidence !== null) {
          // store.confidence is 0-100 -> convert to 0-1 decimal
          editConfidenceDecimal.value = String(Number(store.confidence) / 100);
        } else if (typeof store.accuracy_rate !== 'undefined' && store.accuracy_rate !== null) {
          // accuracy_rate stored as percent (0-100)
          editConfidenceDecimal.value = String(Number(store.accuracy_rate) / 100);
        }
        if (editConfidenceDecimalLabel) {
          // normalize to 2 decimal places for display
          const v = Number(editConfidenceDecimal.value) || 0;
          editConfidenceDecimalLabel.textContent = v.toFixed(2);
        }
      }
      editModal.dataset.storeId = store.id;
    }
    if (editFormError) { editFormError.textContent = ''; editFormError.classList.add('hidden'); }
  }

  function closeEditModal() {
    if (!editModal) return;
    editModal.classList.add('hidden');
    editModal.classList.remove('flex');
    delete editModal.dataset.storeId;
    if (editFormError) { editFormError.textContent = ''; editFormError.classList.add('hidden'); }
  }

  async function saveEditStore() {
    if (!editModal) return;
    const id = editModal.dataset.storeId;
    if (!id) {
      if (editFormError) { editFormError.textContent = 'Không có cửa hàng để lưu'; editFormError.classList.remove('hidden'); }
      return;
    }
    if (!editName || !editName.value.trim()) {
      if (editFormError) { editFormError.textContent = 'Vui lòng nhập tên cửa hàng'; editFormError.classList.remove('hidden'); }
      return;
    }
    if (!editCode || !editCode.value.trim()) {
      if (editFormError) { editFormError.textContent = 'Vui lòng nhập mã cửa hàng'; editFormError.classList.remove('hidden'); }
      return;
    }

    const payload = {
      name: editName.value.trim(),
      code: editCode.value.trim(),
      category: editCategory && editCategory.value ? Number(editCategory.value) : null,
      address: editAddress ? editAddress.value.trim() : '',
      description: editDesc ? editDesc.value.trim() : '',
      // include status if available in UI
      ...(editStatus ? { status: editStatus.value } : {}),
    };
    // include confidence (UI is decimal 0..1) -> backend expects integer 0..100
    if (editConfidenceDecimal) {
      const dec = Number(editConfidenceDecimal.value);
      if (!Number.isNaN(dec)) {
        payload.confidence = Math.round(Math.max(0, Math.min(1, dec)) * 100);
      }
    }

    saveEditBtn.disabled = true;
    const orig = saveEditBtn.textContent;
    saveEditBtn.textContent = 'Đang lưu...';
    try {
      await fetchJSON(ENDPOINTS.storeDetail(id), { method: 'PUT', body: JSON.stringify(payload) });
      closeEditModal();
      await loadStores();
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
      formError.textContent = 'Vui lòng nhập tên cửa hàng';
      formError.classList.remove('hidden');
      return false;
    }
    if (!fCode || !fCode.value.trim()) {
      formError.textContent = 'Vui lòng nhập mã cửa hàng';
      formError.classList.remove('hidden');
      return false;
    }
    return true;
  }

  async function createOrUpdateStore() {
    if (!validateForm()) return;
    // validate selected category exists in the dropdown options (prevent sending invalid PK)
    if (fCategory && fCategory.value) {
      const found = Array.from(fCategory.options).some(o => String(o.value) === String(fCategory.value));
      if (!found) {
        if (formError) {
          formError.textContent = 'Danh mục đã chọn không hợp lệ. Vui lòng chọn lại.';
          formError.classList.remove('hidden');
        } else {
          alert('Danh mục đã chọn không hợp lệ. Vui lòng chọn lại.');
        }
        return;
      }
    }

    const payload = {
      name: fName ? fName.value.trim() : '',
      code: fCode ? fCode.value.trim() : '',
      address: fAddress ? fAddress.value.trim() : '',
      category: fCategory && fCategory.value ? Number(fCategory.value) : null,
      status: fStatus ? fStatus.value : 'active',
      description: fDesc ? fDesc.value.trim() : ''
    };
    // include confidence: if decimal input (0..1) is present, convert to 0..100 int; otherwise fall back to slider value 0..100
    if (confidenceDecimal) {
      const dec = Number(confidenceDecimal.value);
      if (!Number.isNaN(dec)) {
        payload.confidence = Math.round(Math.max(0, Math.min(1, dec)) * 100);
      }
    } else if (confidenceRange) {
      const conf = Number(confidenceRange.value);
      if (!Number.isNaN(conf)) payload.confidence = conf;
    }
    const id = fId && fId.value ? fId.value : null;
    const url = id ? ENDPOINTS.storeDetail(id) : ENDPOINTS.stores;
    const method = id ? 'PUT' : 'POST';

    saveStoreBtn.disabled = true;
    const originalLabel = saveStoreBtn.textContent;
    saveStoreBtn.textContent = 'Đang lưu...';

    try {
      await fetchJSON(url, { method, body: JSON.stringify(payload) });
      closeModal();
      await loadStores();
    } catch (e) {
      if (formError) {
        formError.textContent = e.message || 'Không thể lưu dữ liệu';
        formError.classList.remove('hidden');
      } else {
        alert(e.message || 'Không thể lưu dữ liệu');
      }
    } finally {
      saveStoreBtn.disabled = false;
      saveStoreBtn.textContent = originalLabel;
    }
  }

  async function exportStores() {
    try {
      const url = `${ENDPOINTS.export}?${buildQuery()}`;
      const a = document.createElement('a');
      a.href = url;
      a.download = 'stores.csv';
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (e) {
      console.warn('export', e);
    }
  }

  function openViewModal(store) {
    if (!viewModal) return;
    if (vsStoreName) vsStoreName.textContent = store?.name || '';
    const catName = store?.category_name ?? (store?.category ? store.category : '');
    if (vsStoreSubtitle) vsStoreSubtitle.textContent = `${catName} • Mã CH: ${store?.code || ''}`;

    if (store?.image_url) {
      if (vsMainImage) { vsMainImage.src = store.image_url; vsMainImage.classList.remove('hidden'); }
      if (vsMainImageWrapper) vsMainImageWrapper.classList.remove('hidden');
      if (vsImages) {
        vsImages.classList.remove('hidden');
        vsImages.innerHTML = '';
        const imgs = [store.image_url];
        imgs.forEach(u => {
          const d = document.createElement('div');
          d.className = 'thumb';
          const im = document.createElement('img');
          im.src = u;
          d.appendChild(im);
          vsImages.appendChild(d);
        });
      }
    } else {
      if (vsMainImage) vsMainImage.classList.add('hidden');
      if (vsMainImageWrapper) vsMainImageWrapper.classList.add('hidden');
      if (vsImages) { vsImages.classList.add('hidden'); vsImages.innerHTML = ''; }
    }

    if (vsStatus) vsStatus.textContent = store?.status_display || store?.status || '—';
    if (vsAccuracy) vsAccuracy.textContent = (store?.accuracy_rate != null ? Number(store.accuracy_rate).toFixed(1) + '%' : '—');
    if (vsDetectionCount) vsDetectionCount.textContent = fmt.format(store?.detection_count || 0);
    if (vsLastDetected) vsLastDetected.textContent = (store?.last_detected_at ? timeAgo(store.last_detected_at) : 'Chưa phát hiện');
    if (vsCategory) vsCategory.textContent = store?.category_name || catName || '—';
    if (vsAddress) vsAddress.textContent = store?.address || '—';
    if (vsCreatedAt) vsCreatedAt.textContent = store?.created_at ? new Date(store.created_at).toLocaleString('vi-VN') : '—';

    if (vsEditBtn && store?.id) vsEditBtn.dataset.storeId = store.id;

    viewModal.classList.remove('hidden');
    viewModal.classList.add('flex');
  }

  function closeViewModal() {
    if (!viewModal) return;
    viewModal.classList.add('hidden');
    viewModal.classList.remove('flex');
    if (vsEditBtn) delete vsEditBtn.dataset.storeId;
  }

  if (vsCloseBtn) vsCloseBtn.addEventListener('click', closeViewModal);
  if (vsEditBtn) vsEditBtn.addEventListener('click', () => {
    const id = vsEditBtn.dataset.storeId;
    if (!id) { closeViewModal(); return; }
    fetchJSON(ENDPOINTS.storeDetail(id)).then(s => { closeViewModal(); openEditModal(s); }).catch(e => { console.warn('opening edit from view modal failed', e); });
  });

  if (searchInput) searchInput.addEventListener('input', () => { state.search = searchInput.value.trim(); state.page = 1; loadStores(); });
  if (statusFilter) statusFilter.addEventListener('change', () => { state.status = statusFilter.value; state.page = 1; loadStores(); });
  if (categoryFilter) categoryFilter.addEventListener('change', () => { state.category = categoryFilter.value; state.page = 1; loadStores(); });
  if (prevBtn) prevBtn.addEventListener('click', () => { if (state.page > 1) { state.page--; loadStores(); }});
  if (nextBtn) nextBtn.addEventListener('click', () => { state.page++; loadStores(); });
  if (openCreateBtn) openCreateBtn.addEventListener('click', async () => {
    try {
      // ensure categories are loaded before showing the create modal so user cannot pick an invalid id
      await loadCategories();
    } catch (e) {
      console.warn('loading categories before open modal failed', e);
    }
    openModal('create');
  });
  if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
  if (saveStoreBtn) saveStoreBtn.addEventListener('click', createOrUpdateStore);
  if (exportBtn) exportBtn.addEventListener('click', exportStores);

  // live update for confidence range inside the add/edit modal
  if (confidenceRange && confidenceValue) {
    // initialize (legacy slider)
    confidenceValue.textContent = confidenceRange.value + '%';
    confidenceRange.addEventListener('input', () => {
      confidenceValue.textContent = confidenceRange.value + '%';
    });
  }
  // decimal inputs (0..1)
  if (confidenceDecimal && confidenceDecimalLabel) {
    confidenceDecimalLabel.textContent = (Number(confidenceDecimal.value) || 0).toFixed(2);
    confidenceDecimal.addEventListener('input', () => {
      const v = Number(confidenceDecimal.value) || 0;
      confidenceDecimalLabel.textContent = v.toFixed(2);
    });
  }

  if (closeEditModalBtn) closeEditModalBtn.addEventListener('click', closeEditModal);
  if (cancelEditBtn) cancelEditBtn.addEventListener('click', closeEditModal);
  if (saveEditBtn) saveEditBtn.addEventListener('click', saveEditStore);

  if (tbody) tbody.addEventListener('click', async (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const id = btn.dataset.id;
    const action = btn.dataset.action;
    if (!id || !action) return;

    if (action === 'edit') {
      try {
        const store = await fetchJSON(ENDPOINTS.storeDetail(id));
        openEditModal(store);
      } catch (e) { console.warn('detail', e); }
    } else if (action === 'delete') {
      if (!confirm('Bạn có chắc muốn xóa cửa hàng này?')) return;
      try {
        await fetchJSON(ENDPOINTS.storeDetail(id), { method: 'DELETE' });
        await loadStores();
      } catch (e) { alert('Xóa thất bại: ' + (e.message || '')); }
    } else if (action === 'view') {
      try {
        const store = await fetchJSON(ENDPOINTS.storeDetail(id));
        openViewModal(store);
      } catch (e) { console.warn('view', e); }
    }
  });

  const cancelBtn = $('#cancelAddStoreBtn');
  if (cancelBtn) cancelBtn.addEventListener('click', (e) => { e.preventDefault(); closeModal(); });

  loadMetrics();
  loadCategories();
  loadStores();

  // Select all / row select handling
  // attach change handler to selectAll checkbox if present now
  const selAllInit = getSelectAllCheckbox();
  if (selAllInit) {
    selAllInit.addEventListener('change', (e) => {
      const checked = e.target.checked;
      document.querySelectorAll('.row-select').forEach(r => r.checked = checked);
    });
  }

  // Keep header checkbox state in sync when clicking a row checkbox
  document.addEventListener('change', (e) => {
    if (!e.target.classList) return;
    if (e.target.classList.contains('row-select')) {
      const all = document.querySelectorAll('.row-select');
      const checked = document.querySelectorAll('.row-select:checked');
      const selAll = getSelectAllCheckbox();
      if (selAll) selAll.checked = (all.length > 0 && checked.length === all.length);
    }
  });
})();
