/**
 * Dashboard and main admin functionality
 */

// MathLive virtual keyboard: resize modal when keyboard appears/disappears
if (window.mathVirtualKeyboard) {
    window.mathVirtualKeyboard.addEventListener('geometrychange', () => {
        const kbRect = window.mathVirtualKeyboard.boundingRect;
        // Find any visible modal-content
        const modals = ['edit-test-modal', 'create-test-modal', 'edit-prezident-modal', 'create-prezident-modal'];
        let visibleModal = null;
        for (const id of modals) {
            const m = document.getElementById(id);
            if (m && !m.classList.contains('hidden')) { visibleModal = m; break; }
        }

        if (!visibleModal) return;
        const modalContent = visibleModal.querySelector('.modal-content');
        if (!modalContent) return;

        if (kbRect && kbRect.height > 0) {
            const availableHeight = window.innerHeight - kbRect.height - 20;
            modalContent.style.maxHeight = availableHeight + 'px';
            modalContent.style.transition = 'max-height 0.2s ease';
            const focused = modalContent.querySelector('math-field:focus-within');
            if (focused) {
                setTimeout(() => focused.scrollIntoView({ behavior: 'smooth', block: 'center' }), 100);
            }
        } else {
            modalContent.style.maxHeight = '90vh';
        }
    });
}

// Page navigation
document.querySelectorAll('.menu a[data-page]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const page = link.dataset.page;

        document.querySelectorAll('.menu a').forEach(a => a.classList.remove('active'));
        link.classList.add('active');

        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(page + '-page').classList.add('active');

        if (page === 'dashboard') loadDashboard();
        if (page === 'tests') loadTests();
        if (page === 'prezident') loadPrezidentTests();
        if (page === 'admins') loadAdmins();
        if (page === 'payments') loadPayments();
    });
});

// ==========================================
// DASHBOARD
// ==========================================
async function loadDashboard() {
    refreshPaymentsBadge();
    try {
        const [students, sertifikat, prezident] = await Promise.all([
            apiRequest('/api/v1/admin/students?limit=5000').then(r => r.json()),
            apiRequest('/api/v1/tests/?test_type=sertifikat').then(r => r.json()),
            apiRequest('/api/v1/tests/?test_type=prezident').then(r => r.json()),
        ]);
        const active = [...sertifikat, ...prezident].filter(t => t.is_active).length;

        const stat = (img, label, value) => `
            <div class="stat-card">
                <img class="illus" src="../brand/${img}.webp" alt="">
                <div><h3>${label}</h3><p class="stat-number">${value}</p></div>
            </div>`;
        document.getElementById('stats').innerHTML =
            stat('icon-students', "Ro'yxatdan o'tgan talabalar", students.length) +
            stat('icon-certificate', 'Sertifikat testlari', sertifikat.length) +
            stat('icon-school', 'Prezident maktabi testlari', prezident.length) +
            stat('icon-exam', 'Hozir faol testlar', active);
        document.getElementById('recent-tests').innerHTML = `
            <h2>Imtihon qanday o'tkaziladi</h2>
            <ol class="steps">
                <li><b>Test yarating</b><span>Javoblar kalitini kiriting, boshlanish va tugash vaqtini belgilang.</span></li>
                <li><b>Kodni tarqating</b><span>Talabalar botga test kodini yuborib, testni telefonda ishlaydi.</span></li>
                <li><b>Offline natijalarni qo'shing</b><span>Qog'ozda topshirganlarni Excel shablon orqali yuklang.</span></li>
                <li><b>Rasch natijani oling</b><span>Test tugagach, milliy sertifikat uslubidagi PDF yoki Excel'ni yuklab oling.</span></li>
            </ol>
        `;
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// ==========================================
// HELPERS
// ==========================================
function formatDateTime(isoStr) {
    if (!isoStr) return 'Belgilanmagan';
    const d = new Date(isoStr);
    return d.toLocaleString('uz-UZ', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function toDatetimeLocal(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    const offset = d.getTimezoneOffset();
    const adjusted = new Date(d.getTime() - offset * 60 * 1000);
    return adjusted.toISOString().slice(0, 16);
}

// ==========================================
// Sana-vaqt tanlagich (flatpickr) — qiymat formati o'zgarmaydi: YYYY-MM-DDTHH:MM
// ==========================================
const DATETIME_PREFIXES = ['test', 'edit-test', 'prez-test', 'edit-prez-test'];

function addPickerActions(_dates, _str, fp) {
    const bar = document.createElement('div');
    bar.className = 'fp-actions';
    bar.innerHTML = `
        <button type="button" data-act="clear">Tozalash</button>
        <button type="button" data-act="now">Hozir</button>
        <button type="button" data-act="ok" class="is-primary">Tayyor</button>`;
    bar.addEventListener('click', (e) => {
        const act = e.target.closest('button')?.dataset.act;
        if (act === 'clear') { fp.clear(); fp.close(); }
        if (act === 'now') fp.setDate(new Date(), true);
        if (act === 'ok') fp.close();
    });
    fp.calendarContainer.appendChild(bar);
}

function initDatePickers() {
    if (!window.flatpickr) return;  // kutubxona yuklanmasa, oddiy maydon qoladi
    DATETIME_PREFIXES.forEach(prefix => ['start', 'end'].forEach(kind => {
        flatpickr(`#${prefix}-${kind}-time`, {
            enableTime: true,
            time_24hr: true,
            dateFormat: 'Y-m-d\\TH:i',
            altInput: true,
            altFormat: 'd.m.Y, H:i',
            altInputClass: 'dt-input',
            locale: 'uz_latn',
            disableMobile: true,
            static: true,
            onReady: addPickerActions,
            onOpen: (_d, _s, fp) => requestAnimationFrame(() =>
                fp.calendarContainer.scrollIntoView({ block: 'nearest', behavior: 'smooth' })),
        }).altInput.placeholder = 'Sana va vaqtni tanlang';
    }));
}

function setDateTime(id, value) {
    const el = document.getElementById(id);
    if (el._flatpickr) el._flatpickr.setDate(value || null, false);
    else el.value = value || '';
}

function clearDateTimes(prefix) {
    setDateTime(`${prefix}-start-time`, '');
    setDateTime(`${prefix}-end-time`, '');
}

initDatePickers();

// ==========================================
// Javob tanlagich: A B C D tugmalari; qiymat yashirin maydonda (id o'zgarmaydi)
// ==========================================
function answerPicker(id, num, options, current = 'A') {
    const buttons = options.map(opt => `
        <button type="button" class="ans-opt${opt === current ? ' is-on' : ''}" data-value="${opt}"
                aria-pressed="${opt === current}">${opt}</button>`).join('');
    return `<div class="mcq-answer-input">
        <span class="mcq-num">${num}</span>
        <div class="ans-opts" role="group" aria-label="${num}-savol javobi">${buttons}</div>
        <input type="hidden" id="${id}" value="${current}">
    </div>`;
}

function chooseAnswer(button) {
    const group = button.closest('.mcq-answer-input');
    group.querySelectorAll('.ans-opt').forEach(b => {
        const on = b === button;
        b.classList.toggle('is-on', on);
        b.setAttribute('aria-pressed', on);
    });
    group.querySelector('input[type="hidden"]').value = button.dataset.value;
}

document.addEventListener('click', (e) => {
    const button = e.target.closest('.ans-opt');
    if (button) chooseAnswer(button);
});

// Klaviaturadan tez kiritish: harf bosilsa tanlanadi va keyingi savolga o'tiladi
document.addEventListener('keydown', (e) => {
    const current = e.target.closest?.('.ans-opt');
    if (!current || e.ctrlKey || e.metaKey || e.altKey) return;
    const group = current.closest('.mcq-answer-input');
    const match = [...group.querySelectorAll('.ans-opt')]
        .find(b => b.dataset.value === e.key.toUpperCase());
    if (!match) return;
    e.preventDefault();
    chooseAnswer(match);
    const next = group.nextElementSibling?.querySelector('.ans-opt.is-on');
    (next || match).focus();
});

// Ikonkalar (inline SVG, 24x24, chiziqli)
const ICON_PATHS = {
    award: '<circle cx="12" cy="9" r="6"/><path d="m8.5 13.8-1.5 7.2 5-2.6 5 2.6-1.5-7.2"/>',
    sheet: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/>',
    file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M8 13h8M8 17h5"/>',
    download: '<path d="M12 4v11"/><path d="m7 10 5 5 5-5"/><path d="M5 20h14"/>',
    upload: '<path d="M12 20V9"/><path d="m7 14 5-5 5 5"/><path d="M5 4h14"/>',
    list: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
    edit: '<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    reset: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
    trash: '<path d="M4 7h16"/><path d="M10 11v6M14 11v6"/><path d="M6 7l1 13h10l1-13"/><path d="M9 7V4h6v3"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
};

function icon(name) {
    return `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${ICON_PATHS[name] || ''}</svg>`;
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[ch]));
}

// onclick atributi ichida xavfsiz ishlatish uchun (masalan, test nomi)
function jsArg(value) {
    return escapeHtml(JSON.stringify(String(value ?? '')));
}

// Test kartasi: ma'lumot + vazifasi bo'yicha guruhlangan amallar
function buildTestCard(test) {
    const type = test.test_type || 'sertifikat';
    const id = test.id;
    const title = jsArg(test.title);
    const isSertifikat = type === 'sertifikat';

    const resultsGroup = `
        <div class="action-group">
            <span class="action-group-label">Natijalar</span>
            <div class="test-card-actions">
                ${isSertifikat ? `
                <button class="btn is-strong" onclick="exportRasch('${id}', 'pdf', this)">${icon('award')} Rasch natija · PDF</button>
                <button class="btn" onclick="exportRasch('${id}', 'excel', this)">${icon('award')} Rasch natija · Excel</button>` : ''}
                <button class="btn" onclick="exportExcel('${id}', this)">${icon('sheet')} Javoblar jadvali · Excel</button>
                <button class="btn" onclick="exportPDF('${id}', this)">${icon('file')} Javoblar jadvali · PDF</button>
            </div>
        </div>`;

    const offlineGroup = isSertifikat ? `
        <div class="action-group">
            <span class="action-group-label">Offline</span>
            <div class="test-card-actions">
                <button class="btn" onclick="downloadOfflineTemplate('${id}', this)">${icon('download')} Shablonni yuklab olish</button>
                <button class="btn" onclick="uploadOfflineResults('${id}')">${icon('upload')} Natijalarni yuklash</button>
                <button class="btn" onclick="manageOfflineResults('${id}')">${icon('list')} Yuklanganlar</button>
            </div>
        </div>` : '';

    const manageGroup = `
        <div class="action-group">
            <span class="action-group-label">Boshqarish</span>
            <div class="test-card-actions">
                <button class="btn" onclick="openEditModal('${id}', '${type}')">${icon('edit')} Tahrirlash</button>
                <button class="btn" onclick="extendAllSessions('${id}', ${title})">${icon('clock')} Hammaga +5 daqiqa</button>
                <button class="btn" onclick="clearSessions('${id}', ${title})">${icon('reset')} Sessiyalarni tozalash</button>
                <button class="btn is-danger push-right" onclick="deleteTest('${id}', ${title})">${icon('trash')} Testni o'chirish</button>
            </div>
        </div>`;

    return `
        <article class="test-card ${test.is_active ? 'is-active' : ''}">
            <div class="test-card-head">
                <div>
                    <h3>${escapeHtml(test.title)}</h3>
                    <div class="test-meta">
                        <span>Kod <span class="test-code">${escapeHtml(test.test_code)}</span></span>
                        <span class="price-chip ${test.price > 0 ? 'is-paid' : ''}">${test.price > 0 ? formatSum(test.price) : 'Bepul'}</span>
                        <span>${icon('calendar')} ${formatDateTime(test.start_time)} — ${formatDateTime(test.end_time)}</span>
                        ${test.extra_minutes > 0 ? `<span>${icon('clock')} +${test.extra_minutes} daqiqa qo'shilgan</span>` : ''}
                    </div>
                </div>
                <span class="status ${test.is_active ? 'is-on' : 'is-off'}">${test.is_active ? 'Faol' : 'Nofaol'}</span>
            </div>
            <div class="action-groups">
                ${resultsGroup}
                ${offlineGroup}
                ${manageGroup}
            </div>
        </article>
    `;
}

function renderTestList(tests, containerId, createButtonId) {
    const container = document.getElementById(containerId);
    if (!tests.length) {
        container.innerHTML = `
            <div class="empty-state">
                <img class="illus" src="../brand/${containerId === 'prezident-list' ? 'icon-school' : 'icon-certificate'}.webp" alt="">
                <h3>Hali test yo'q</h3>
                <p>Javoblar kalitini kiritib birinchi testni yarating. Kodini talabalarga bersangiz, ular botda testni boshlay oladi.</p>
                <button class="btn-primary" onclick="document.getElementById('${createButtonId}').click()">${icon('plus')} Yangi test</button>
            </div>`;
        return;
    }
    container.innerHTML = `<div class="test-cards">${tests.map(buildTestCard).join('')}</div>`;
}

// ==========================================
// SERTIFIKAT TESTS
// ==========================================
async function loadTests() {
    try {
        const response = await apiRequest('/api/v1/tests/?test_type=sertifikat');
        const tests = await response.json();
        renderTestList(tests, 'tests-list', 'create-test-btn');
    } catch (error) {
        console.error('Error loading tests:', error);
    }
}

// ==========================================
// PREZIDENT TESTS
// ==========================================
async function loadPrezidentTests() {
    try {
        const response = await apiRequest('/api/v1/tests/?test_type=prezident');
        const tests = await response.json();
        renderTestList(tests, 'prezident-list', 'create-prezident-btn');
    } catch (error) {
        console.error('Error loading prezident tests:', error);
    }
}

// ==========================================
// EXPORT / DELETE / EXTEND (shared)
// ==========================================
// Fayl yuklab olish: fetch -> blob -> vaqtinchalik havola.
// Havola darhol o'chirilmaydi (katta fayllarda, masalan Rasch PDF, yuklash uzilib qolardi).
const pendingDownloads = new Set();

async function downloadFile(path, filename, button) {
    if (pendingDownloads.has(path)) return;
    pendingDownloads.add(path);
    const originalHtml = button ? button.innerHTML : null;
    if (button) {
        button.disabled = true;
        button.classList.add('is-busy');
        button.innerHTML = `${icon('clock')} Tayyorlanmoqda…`;
    }
    try {
        const response = await fetch(`${API_BASE}${path}`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('adminToken')}` },
            cache: 'no-store'
        });
        if (response.status === 401) {
            localStorage.removeItem('adminToken');
            showLoginPage();
            throw new Error('Sessiya tugagan, qaytadan kiring');
        }
        if (!response.ok) {
            let message = `Server xatoligi (${response.status})`;
            try {
                const data = await response.json();
                if (typeof data.detail === 'string') message = data.detail;
            } catch (e) { /* JSON emas */ }
            throw new Error(message);
        }
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 60000);
    } finally {
        pendingDownloads.delete(path);
        if (button) {
            button.disabled = false;
            button.classList.remove('is-busy');
            button.innerHTML = originalHtml;
        }
    }
}

async function exportExcel(testId, button) {
    try {
        await downloadFile(`/api/v1/admin/reports/${testId}/excel`, 'javoblar_jadvali.xlsx', button);
    } catch (error) {
        alert('Excel yuklab olinmadi: ' + error.message);
    }
}

async function exportPDF(testId, button) {
    try {
        await downloadFile(`/api/v1/admin/reports/${testId}/pdf`, 'javoblar_jadvali.pdf', button);
    } catch (error) {
        alert('PDF yuklab olinmadi: ' + error.message);
    }
}

// Rasch modeli asosidagi milliy sertifikat uslubidagi natijalar
async function exportRasch(testId, format, button) {
    try {
        const filename = format === 'pdf' ? 'rasch_natijalar.pdf' : 'rasch_natijalar.xlsx';
        await downloadFile(`/api/v1/admin/reports/${testId}/rasch/${format}`, filename, button);
    } catch (error) {
        alert('Rasch natija yuklab olinmadi: ' + error.message);
    }
}

// ==========================================
// OFFLINE NATIJALAR (Excel 0/1)
// ==========================================
async function downloadOfflineTemplate(testId, button) {
    try {
        await downloadFile(`/api/v1/admin/tests/${testId}/offline/template`, 'offline_shablon.xlsx', button);
    } catch (error) {
        alert('Shablon xatolik: ' + error.message);
    }
}

function uploadOfflineResults(testId) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.xlsx';
    input.onchange = async () => {
        const file = input.files[0];
        if (!file) return;
        const form = new FormData();
        form.append('file', file);
        try {
            const response = await fetch(`${API_BASE}/api/v1/admin/tests/${testId}/offline/upload`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('adminToken')}` },
                body: form
            });
            const data = await response.json();
            if (!response.ok) {
                const detail = data.detail || {};
                const message = typeof detail === 'string' ? detail : (detail.message || 'Xatolik');
                const errors = (detail.errors || []).slice(0, 20).join('\n');
                alert('❌ ' + message + (errors ? '\n\n' + errors : ''));
                return;
            }
            alert('✅ ' + data.message +
                (data.replaced ? `\n(oldingi ${data.replaced} ta offline natija almashtirildi)` : '') +
                '\n\nOffline natijalar Rasch hisobotiga onlayn natijalar bilan birga kiradi.');
        } catch (error) {
            alert('Yuklashda xatolik: ' + error.message);
        }
    };
    input.click();
}

async function manageOfflineResults(testId) {
    try {
        const response = await apiRequest(`/api/v1/admin/tests/${testId}/offline`);
        const data = await response.json();
        if (data.count === 0) {
            alert("Bu test uchun offline natijalar yuklanmagan.\n\n'📥 Offline shablon' tugmasi orqali shablonni oling, to'ldiring va '📤 Offline natija yuklash' orqali yuklang.");
            return;
        }
        const preview = data.results.slice(0, 15)
            .map((r, i) => `${i + 1}. ${r.name}${r.region ? ' (' + r.region + ')' : ''} — ${r.correct} ta to'g'ri`)
            .join('\n');
        const more = data.count > 15 ? `\n... va yana ${data.count - 15} ta` : '';
        if (confirm(`Offline natijalar: ${data.count} ta\n\n${preview}${more}\n\nBarcha offline natijalarni O'CHIRISH uchun OK bosing.`)) {
            const del = await apiRequest(`/api/v1/admin/tests/${testId}/offline`, { method: 'DELETE' });
            const result = await del.json();
            alert(result.message);
        }
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
}

async function deleteTest(testId, testTitle) {
    if (!confirm(`"${testTitle}" testini o'chirishni xohlaysizmi?\n\nBu amalni qaytarib bo'lmaydi! Barcha natijalar ham o'chiriladi.`)) return;
    try {
        await apiRequest(`/api/v1/tests/${testId}`, { method: 'DELETE' });
        alert('Test muvaffaqiyatli o\'chirildi!');
        loadTests();
        loadPrezidentTests();
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
}

async function clearSessions(testId, testTitle) {
    if (!confirm(`"${testTitle}" testining barcha sessionlarini tozalashni xohlaysizmi?\n\nBarcha natijalar ham o'chiriladi va talabalar testni qayta topshira oladi.`)) return;
    try {
        const response = await apiRequest(`/api/v1/admin/sessions/${testId}`, { method: 'DELETE' });
        const data = await response.json();
        alert(`Tozalandi!\n${data.sessions_deleted} ta session va ${data.results_deleted} ta natija o'chirildi.`);
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
}

async function extendAllSessions(testId, testTitle) {
    if (!confirm(`"${testTitle}" testidagi barcha faol sessiyalarga +5 daqiqa qo'shilsinmi?`)) return;
    try {
        const response = await apiRequest(`/api/v1/admin/tests/${testId}/extend-all`, { method: 'POST' });
        const data = await response.json();
        alert(data.message + (data.skipped > 0 ? `\n${data.skipped} ta sessiya limitga yetgan` : ''));
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
}

// ==========================================
// EDIT TEST (both types)
// ==========================================
let currentEditTestId = null;
let currentEditTestType = 'sertifikat';

async function openEditModal(testId, testType) {
    currentEditTestId = testId;
    currentEditTestType = testType || 'sertifikat';

    try {
        const response = await apiRequest(`/api/v1/tests/${testId}`);
        if (!response.ok) throw new Error(`Server xatosi (${response.status})`);
        const test = await response.json();

        if (currentEditTestType === 'prezident') {
            // Prezident edit modal
            document.getElementById('edit-prez-test-code').value = test.test_code;
            document.getElementById('edit-prez-test-title').value = test.title;
            document.getElementById('edit-prez-test-desc').value = test.description || '';
            document.getElementById('edit-prez-test-active').checked = test.is_active;
            setDateTime('edit-prez-test-start-time', toDatetimeLocal(test.start_time));
            setDateTime('edit-prez-test-end-time', toDatetimeLocal(test.end_time));
            fillPrice('edit-prez-test', test.price);

            // 40 MCQ (A-D)
            let mcqGrid = '';
            for (let i = 1; i <= 40; i++) {
                const options = ['A', 'B', 'C', 'D'];
                const currentVal = (test.answer_key && test.answer_key.mcq_answers) ? (test.answer_key.mcq_answers[i] || 'A') : 'A';
                mcqGrid += answerPicker(`edit-prez-mcq-${i}`, i, options, currentVal);
            }
            document.getElementById('edit-prez-mcq-answers-grid').innerHTML = mcqGrid;
            document.getElementById('edit-prezident-modal').classList.remove('hidden');
        } else {
            // Sertifikat edit modal (existing logic)
            document.getElementById('edit-test-code').value = test.test_code;
            document.getElementById('edit-test-title').value = test.title;
            document.getElementById('edit-test-desc').value = test.description || '';
            document.getElementById('edit-test-active').checked = test.is_active;
            setDateTime('edit-test-start-time', toDatetimeLocal(test.start_time));
            setDateTime('edit-test-end-time', toDatetimeLocal(test.end_time));
            fillPrice('edit-test', test.price);

            let mcqGrid = '';
            for (let i = 1; i <= 35; i++) {
                const options = i <= 32 ? ['A', 'B', 'C', 'D'] : ['A', 'B', 'C', 'D', 'E', 'F'];
                const currentVal = (test.answer_key && test.answer_key.mcq_answers) ? (test.answer_key.mcq_answers[i] || 'A') : 'A';
                mcqGrid += answerPicker(`edit-mcq-${i}`, i, options, currentVal);
            }

            let openEndedHTML = '<div class="open-ended-section"><h3>Yozma savollar (36-45)</h3>';
            const editMathValues = {};
            for (let i = 36; i <= 45; i++) {
                const aVal = (test.answer_key && test.answer_key.written_questions && test.answer_key.written_questions[i])
                    ? (test.answer_key.written_questions[i].a || '') : '';
                const bVal = (test.answer_key && test.answer_key.written_questions && test.answer_key.written_questions[i])
                    ? (test.answer_key.written_questions[i].b || '') : '';
                editMathValues[`edit-open-${i}-a`] = aVal;
                editMathValues[`edit-open-${i}-b`] = bVal;
                openEndedHTML += `
                    <div class="open-question">
                        <h4>${i}</h4>
                        <div class="sub-answer"><label>a)</label><math-field id="edit-open-${i}-a" class="admin-math-input" virtual-keyboard-mode="onfocus"></math-field></div>
                        <div class="sub-answer"><label>b)</label><math-field id="edit-open-${i}-b" class="admin-math-input" virtual-keyboard-mode="onfocus"></math-field></div>
                    </div>`;
            }
            openEndedHTML += '</div>';

            document.getElementById('edit-mcq-answers-grid').innerHTML = mcqGrid + openEndedHTML;
            document.getElementById('edit-test-modal').classList.remove('hidden');

            setTimeout(() => {
                for (const [id, val] of Object.entries(editMathValues)) {
                    const mf = document.getElementById(id);
                    if (mf && val) mf.value = val;
                }
            }, 100);
        }
    } catch (error) {
        alert('Test ma\'lumotlarini yuklashda xatolik: ' + error.message);
    }
}

// Cancel edit modals
document.getElementById('cancel-edit').addEventListener('click', () => {
    document.getElementById('edit-test-modal').classList.add('hidden');
    currentEditTestId = null;
});
document.getElementById('cancel-edit-prez').addEventListener('click', () => {
    document.getElementById('edit-prezident-modal').classList.add('hidden');
    currentEditTestId = null;
});

// Submit sertifikat edit
document.getElementById('edit-test-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const mcqAnswers = {};
    for (let i = 1; i <= 35; i++) {
        mcqAnswers[String(i)] = document.getElementById(`edit-mcq-${i}`).value;
    }

    const writtenQuestions = {};
    for (let i = 36; i <= 45; i++) {
        writtenQuestions[String(i)] = {
            a: document.getElementById(`edit-open-${i}-a`).value,
            b: document.getElementById(`edit-open-${i}-b`).value
        };
    }

    const updateData = {
        test_code: document.getElementById('edit-test-code').value,
        title: document.getElementById('edit-test-title').value,
        description: document.getElementById('edit-test-desc').value,
        is_active: document.getElementById('edit-test-active').checked,
        start_time: document.getElementById('edit-test-start-time').value || null,
        end_time: document.getElementById('edit-test-end-time').value || null,
        price: readPrice('edit-test'),
        answer_key: { mcq_answers: mcqAnswers, written_questions: writtenQuestions }
    };

    try {
        await apiRequest(`/api/v1/tests/${currentEditTestId}`, {
            method: 'PATCH', body: JSON.stringify(updateData)
        });
        alert('Test muvaffaqiyatli yangilandi!');
        document.getElementById('edit-test-modal').classList.add('hidden');
        currentEditTestId = null;
        loadTests();
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
});

// Submit prezident edit
document.getElementById('edit-prezident-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const mcqAnswers = {};
    for (let i = 1; i <= 40; i++) {
        mcqAnswers[String(i)] = document.getElementById(`edit-prez-mcq-${i}`).value;
    }

    const updateData = {
        test_code: document.getElementById('edit-prez-test-code').value,
        title: document.getElementById('edit-prez-test-title').value,
        description: document.getElementById('edit-prez-test-desc').value,
        is_active: document.getElementById('edit-prez-test-active').checked,
        start_time: document.getElementById('edit-prez-test-start-time').value || null,
        end_time: document.getElementById('edit-prez-test-end-time').value || null,
        price: readPrice('edit-prez-test'),
        answer_key: { mcq_answers: mcqAnswers, written_questions: {} }
    };

    try {
        await apiRequest(`/api/v1/tests/${currentEditTestId}`, {
            method: 'PATCH', body: JSON.stringify(updateData)
        });
        alert('Test muvaffaqiyatli yangilandi!');
        document.getElementById('edit-prezident-modal').classList.add('hidden');
        currentEditTestId = null;
        loadPrezidentTests();
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
});

// ==========================================
// CREATE SERTIFIKAT TEST
// ==========================================
document.getElementById('create-test-btn').addEventListener('click', () => {
    let mcqGrid = '';
    for (let i = 1; i <= 35; i++) {
        const options = i <= 32 ? ['A', 'B', 'C', 'D'] : ['A', 'B', 'C', 'D', 'E', 'F'];
        mcqGrid += answerPicker(`mcq-${i}`, i, options);
    }

    let openEndedHTML = '<div class="open-ended-section"><h3>Yozma savollar (36-45)</h3>';
    for (let i = 36; i <= 45; i++) {
        openEndedHTML += `
            <div class="open-question">
                <h4>${i}</h4>
                <div class="sub-answer"><label>a)</label><math-field id="open-${i}-a" class="admin-math-input" virtual-keyboard-mode="onfocus"></math-field></div>
                <div class="sub-answer"><label>b)</label><math-field id="open-${i}-b" class="admin-math-input" virtual-keyboard-mode="onfocus"></math-field></div>
            </div>`;
    }
    openEndedHTML += '</div>';

    document.getElementById('mcq-answers-grid').innerHTML = mcqGrid + openEndedHTML;
    document.getElementById('create-test-form').reset();
    clearDateTimes('test');
    fillPrice('test', 0);
    document.getElementById('create-test-modal').classList.remove('hidden');
});

document.getElementById('cancel-create').addEventListener('click', () => {
    document.getElementById('create-test-modal').classList.add('hidden');
});

document.getElementById('create-test-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const mcqAnswers = {};
    for (let i = 1; i <= 35; i++) {
        mcqAnswers[String(i)] = document.getElementById(`mcq-${i}`).value;
    }

    const writtenQuestions = {};
    for (let i = 36; i <= 45; i++) {
        writtenQuestions[String(i)] = {
            a: document.getElementById(`open-${i}-a`).value,
            b: document.getElementById(`open-${i}-b`).value
        };
    }

    const testData = {
        test_code: document.getElementById('test-code').value,
        title: document.getElementById('test-title').value,
        description: document.getElementById('test-desc').value || null,
        start_time: document.getElementById('test-start-time').value || null,
        end_time: document.getElementById('test-end-time').value || null,
        test_type: 'sertifikat',
        price: readPrice('test'),
        answer_key: { mcq_answers: mcqAnswers, written_questions: writtenQuestions }
    };

    try {
        await apiRequest('/api/v1/tests/', { method: 'POST', body: JSON.stringify(testData) });
        alert('Test muvaffaqiyatli yaratildi!');
        document.getElementById('create-test-modal').classList.add('hidden');
        loadTests();
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
});

// ==========================================
// CREATE PREZIDENT TEST
// ==========================================
document.getElementById('create-prezident-btn').addEventListener('click', () => {
    let mcqGrid = '';
    for (let i = 1; i <= 40; i++) {
        const options = ['A', 'B', 'C', 'D'];
        mcqGrid += answerPicker(`prez-mcq-${i}`, i, options);
    }

    document.getElementById('prez-mcq-answers-grid').innerHTML = mcqGrid;
    document.getElementById('create-prezident-form').reset();
    clearDateTimes('prez-test');
    fillPrice('prez-test', 0);
    document.getElementById('create-prezident-modal').classList.remove('hidden');
});

document.getElementById('cancel-create-prez').addEventListener('click', () => {
    document.getElementById('create-prezident-modal').classList.add('hidden');
});

document.getElementById('create-prezident-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const mcqAnswers = {};
    for (let i = 1; i <= 40; i++) {
        mcqAnswers[String(i)] = document.getElementById(`prez-mcq-${i}`).value;
    }

    const testData = {
        test_code: document.getElementById('prez-test-code').value,
        title: document.getElementById('prez-test-title').value,
        description: document.getElementById('prez-test-desc').value || null,
        start_time: document.getElementById('prez-test-start-time').value || null,
        end_time: document.getElementById('prez-test-end-time').value || null,
        test_type: 'prezident',
        price: readPrice('prez-test'),
        answer_key: { mcq_answers: mcqAnswers, written_questions: {} }
    };

    try {
        await apiRequest('/api/v1/tests/', { method: 'POST', body: JSON.stringify(testData) });
        alert('Test muvaffaqiyatli yaratildi!');
        document.getElementById('create-prezident-modal').classList.add('hidden');
        loadPrezidentTests();
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
});

// ==========================================
// EXPOSE FUNCTIONS
// ==========================================
window.exportExcel = exportExcel;
window.exportPDF = exportPDF;
window.exportRasch = exportRasch;
window.downloadOfflineTemplate = downloadOfflineTemplate;
window.uploadOfflineResults = uploadOfflineResults;
window.manageOfflineResults = manageOfflineResults;
window.deleteTest = deleteTest;
window.openEditModal = openEditModal;
window.clearSessions = clearSessions;
window.extendAllSessions = extendAllSessions;

// Load dashboard on init
if (isLoggedIn()) {
    loadDashboard();
}

// =================== ADMIN MANAGEMENT ===================
async function loadAdmins() {
    const container = document.getElementById('admin-list');
    container.innerHTML = "<p>Bu yerda yangi admin qo'shishingiz mumkin. Har bir admin barcha testlarni ko'radi va boshqaradi, shuning uchun loginni faqat ishonchli o'qituvchilarga bering.</p>";
}

document.getElementById('add-admin-btn').addEventListener('click', () => {
    document.getElementById('add-admin-modal').classList.remove('hidden');
    document.getElementById('new-admin-username').value = '';
    document.getElementById('new-admin-password').value = '';
});

document.getElementById('cancel-add-admin').addEventListener('click', () => {
    document.getElementById('add-admin-modal').classList.add('hidden');
});

document.getElementById('add-admin-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('new-admin-username').value.trim();
    const password = document.getElementById('new-admin-password').value;

    if (!username || !password) {
        alert('Foydalanuvchi nomi va parolni kiriting!');
        return;
    }
    if (password.length < 6) {
        alert('Parol kamida 6 ta belgidan iborat bo\'lishi kerak!');
        return;
    }

    try {
        const response = await apiRequest('/api/v1/auth/register', {
            method: 'POST', body: JSON.stringify({ username, password })
        });
        const data = await response.json();
        alert(`✅ Admin "${data.username}" muvaffaqiyatli qo'shildi!`);
        document.getElementById('add-admin-modal').classList.add('hidden');
    } catch (error) {
        alert('❌ Xatolik: ' + error.message);
    }
});

// ==========================================
// NARX (pullik / bepul test)
// ==========================================
function formatSum(value) {
    return `${Number(value || 0).toLocaleString('ru-RU').replace(/,/g, ' ')} so'm`;
}

function fillPrice(prefix, price) {
    const paid = document.getElementById(`${prefix}-paid`);
    const input = document.getElementById(`${prefix}-price`);
    paid.checked = Number(price) > 0;
    input.value = Number(price) > 0 ? price : '';
    input.disabled = !paid.checked;
}

function readPrice(prefix) {
    const paid = document.getElementById(`${prefix}-paid`).checked;
    const value = parseInt(document.getElementById(`${prefix}-price`).value, 10);
    return paid && value > 0 ? value : 0;
}

['test', 'edit-test', 'prez-test', 'edit-prez-test'].forEach(prefix => {
    const paid = document.getElementById(`${prefix}-paid`);
    const input = document.getElementById(`${prefix}-price`);
    paid.addEventListener('change', () => {
        input.disabled = !paid.checked;
        if (paid.checked) input.focus();
    });
});

// ==========================================
// TO'LOVLAR (cheklar)
// ==========================================
let paymentStatus = 'pending';
let paymentItems = [];
const receiptUrls = new Map();   // payment id -> blob URL (rasm/PDF)

async function fetchReceipt(id) {
    if (receiptUrls.has(id)) return receiptUrls.get(id);
    const response = await fetch(`${API_BASE}/api/v1/admin/payments/${id}/file`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('adminToken')}` },
        cache: 'no-store'
    });
    if (!response.ok) throw new Error('Chek fayli topilmadi yoki o\'chirilgan');
    const url = URL.createObjectURL(await response.blob());
    receiptUrls.set(id, url);
    return url;
}

function updatePaymentsBadge(pending) {
    const badge = document.getElementById('payments-badge');
    badge.textContent = pending;
    badge.classList.toggle('hidden', !pending);
}

async function refreshPaymentsBadge() {
    try {
        const data = await (await apiRequest('/api/v1/admin/payments?status=pending')).json();
        updatePaymentsBadge(data.counts.pending);
    } catch (e) { /* jim */ }
}

async function loadPaymentSettings() {
    try {
        const s = await (await apiRequest('/api/v1/admin/payment-settings')).json();
        document.getElementById('pay-card-number').value = s.card_number || '';
        document.getElementById('pay-card-holder').value = s.card_holder || '';
        document.getElementById('pay-note').value = s.note || '';
        const details = document.getElementById('pay-settings');
        if (!s.card_number) details.open = true;
    } catch (e) { console.error(e); }
}

async function loadPayments() {
    loadPaymentSettings();
    const list = document.getElementById('payments-list');
    try {
        const data = await (await apiRequest(`/api/v1/admin/payments?status=${paymentStatus}`)).json();
        paymentItems = data.items;
        ['pending', 'approved', 'rejected'].forEach(k => {
            document.getElementById(`count-${k}`).textContent = data.counts[k];
        });
        updatePaymentsBadge(data.counts.pending);
        renderPayments();
    } catch (error) {
        list.innerHTML = `<div class="empty-state"><h3>Ro'yxat yuklanmadi</h3><p>${escapeHtml(error.message)}</p></div>`;
    }
}

function paymentStatusLabel(item) {
    if (item.status === 'approved') return '<span class="status is-on">Tasdiqlangan</span>';
    if (item.status === 'rejected') return '<span class="status is-off">Rad etilgan</span>';
    return '<span class="status is-wait">Kutilmoqda</span>';
}

function renderPayments() {
    const list = document.getElementById('payments-list');
    const pending = paymentStatus === 'pending';
    document.getElementById('pay-bulk').classList.toggle('hidden', !pending || !paymentItems.length);
    document.getElementById('pay-select-all').checked = false;
    updateSelectedButton();

    if (!paymentItems.length) {
        const texts = {
            pending: ["Tekshiriladigan chek yo'q", "Talabalar botga chek yuborganda ular shu yerda paydo bo'ladi."],
            approved: ["Tasdiqlangan to'lov yo'q", "Tasdiqlangan cheklar shu yerda ko'rinadi."],
            rejected: ["Rad etilgan to'lov yo'q", "Rad etilgan cheklar shu yerda ko'rinadi."],
        }[paymentStatus];
        list.innerHTML = `<div class="empty-state"><img class="illus" src="../brand/icon-exam.webp" alt=""><h3>${texts[0]}</h3><p>${texts[1]}</p></div>`;
        return;
    }

    list.innerHTML = `<div class="pay-list">${paymentItems.map(item => {
        const test = item.test ? `<span><span class="test-code">${escapeHtml(item.test.code)}</span> ${escapeHtml(item.test.title)}</span>` : '<span class="muted">Balansni to\'ldirish</span>';
        const thumb = item.has_file
            ? (item.content_type === 'application/pdf'
                ? `<button class="pay-thumb is-pdf" onclick="openReceipt('${item.id}')" aria-label="Chekni ko'rish">PDF</button>`
                : `<button class="pay-thumb" onclick="openReceipt('${item.id}')" aria-label="Chekni ko'rish"><img data-receipt="${item.id}" alt=""></button>`)
            : `<span class="pay-thumb is-gone" title="Chek o'chirilgan">—</span>`;
        const amount = pending
            ? `<label class="amount-input"><input type="number" min="1000" step="1000" value="${item.amount}" data-amount="${item.id}"> so'm</label>`
            : `<b>${formatSum(item.amount)}</b>`;
        const created = formatDateTime(item.created_at);
        const keep = item.file_expires_at ? `<small class="muted">Chek ${formatDateTime(item.file_expires_at)} gacha saqlanadi</small>` : '';
        return `
            <div class="pay-row" data-id="${item.id}">
                ${pending ? `<input type="checkbox" class="pay-check" value="${item.id}" aria-label="Belgilash">` : '<span></span>'}
                ${thumb}
                <div class="pay-who">
                    <b>${escapeHtml(item.user.name)}</b>
                    <small>${escapeHtml(item.user.region || '')} · Telegram ID ${item.user.telegram_id}</small>
                </div>
                <div class="pay-test">${test}<small class="muted">${created}</small>${keep}</div>
                <div class="pay-amount">${amount}${item.note ? `<small class="muted">Sabab: ${escapeHtml(item.note)}</small>` : ''}</div>
                <div class="pay-actions">
                    ${pending ? `
                        <button class="btn is-strong" onclick="approvePayments(['${item.id}'])">Tasdiqlash</button>
                        <button class="btn is-danger" onclick="rejectPayment('${item.id}')">Rad etish</button>`
                      : paymentStatusLabel(item)}
                </div>
            </div>`;
    }).join('')}</div>`;

    // Rasm cheklar uchun kichik ko'rinish
    list.querySelectorAll('img[data-receipt]').forEach(async img => {
        try { img.src = await fetchReceipt(img.dataset.receipt); } catch (e) { img.alt = '—'; }
    });
    list.querySelectorAll('.pay-check').forEach(cb => cb.addEventListener('change', updateSelectedButton));
}

function selectedPaymentIds() {
    return [...document.querySelectorAll('.pay-check:checked')].map(cb => cb.value);
}

function updateSelectedButton() {
    const n = selectedPaymentIds().length;
    const btn = document.getElementById('pay-approve-selected');
    btn.disabled = n === 0;
    btn.textContent = n ? `Belgilanganlarni tasdiqlash (${n})` : 'Belgilanganlarni tasdiqlash';
}

function collectAmounts(ids) {
    const amounts = {};
    ids.forEach(id => {
        const input = document.querySelector(`input[data-amount="${id}"]`);
        const item = paymentItems.find(p => p.id === id);
        if (input && item && Number(input.value) !== item.amount) amounts[id] = Number(input.value);
    });
    return amounts;
}

async function approvePayments(ids) {
    if (!ids.length) return;
    const total = ids.reduce((sum, id) => {
        const input = document.querySelector(`input[data-amount="${id}"]`);
        return sum + Number(input ? input.value : 0);
    }, 0);
    if (ids.length > 1 && !confirm(`${ids.length} ta to'lov (${formatSum(total)}) tasdiqlansinmi?`)) return;
    try {
        const response = await apiRequest('/api/v1/admin/payments/approve', {
            method: 'POST', body: JSON.stringify({ ids, amounts: collectAmounts(ids) })
        });
        const data = await response.json();
        closeReceipt();
        await loadPayments();
        if (ids.length > 1) alert(data.message);
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
}

async function approveAllPayments() {
    const n = Number(document.getElementById('count-pending').textContent);
    if (!n || !confirm(`Kutilayotgan barcha ${n} ta to'lov tasdiqlansinmi?`)) return;
    try {
        const data = await (await apiRequest('/api/v1/admin/payments/approve-all', { method: 'POST' })).json();
        await loadPayments();
        alert(data.message);
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
}

async function rejectPayment(id) {
    const note = prompt("Rad etish sababi (talabaga yuboriladi, ixtiyoriy):", '');
    if (note === null) return;
    try {
        await apiRequest(`/api/v1/admin/payments/${id}/reject`, { method: 'POST', body: JSON.stringify({ note }) });
        closeReceipt();
        await loadPayments();
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
}

let openedReceiptId = null;

async function openReceipt(id) {
    const item = paymentItems.find(p => p.id === id);
    if (!item) return;
    openedReceiptId = id;
    const view = document.getElementById('receipt-view');
    view.innerHTML = '<p class="muted">Yuklanmoqda…</p>';
    document.getElementById('receipt-heading').textContent = `${item.user.name} — ${formatSum(item.amount)}`;
    document.getElementById('receipt-meta').textContent =
        `${item.test ? item.test.code + ' · ' + item.test.title : "Balansni to'ldirish"} · ${formatDateTime(item.created_at)}`;
    const pending = item.status === 'pending';
    document.getElementById('receipt-approve').classList.toggle('hidden', !pending);
    document.getElementById('receipt-reject').classList.toggle('hidden', !pending);
    document.getElementById('receipt-modal').classList.remove('hidden');
    try {
        const url = await fetchReceipt(id);
        view.innerHTML = item.content_type === 'application/pdf'
            ? `<iframe src="${url}" title="PDF chek"></iframe><a class="btn" href="${url}" target="_blank" rel="noopener">PDF'ni yangi oynada ochish</a>`
            : `<img src="${url}" alt="To'lov cheki">`;
    } catch (error) {
        view.innerHTML = `<p class="muted">${escapeHtml(error.message)}</p>`;
    }
}

function closeReceipt() {
    openedReceiptId = null;
    document.getElementById('receipt-modal').classList.add('hidden');
}

document.getElementById('receipt-close').addEventListener('click', closeReceipt);
document.getElementById('receipt-approve').addEventListener('click', () => openedReceiptId && approvePayments([openedReceiptId]));
document.getElementById('receipt-reject').addEventListener('click', () => openedReceiptId && rejectPayment(openedReceiptId));
document.getElementById('pay-approve-selected').addEventListener('click', () => approvePayments(selectedPaymentIds()));
document.getElementById('pay-approve-all').addEventListener('click', approveAllPayments);
document.getElementById('pay-select-all').addEventListener('change', (e) => {
    document.querySelectorAll('.pay-check').forEach(cb => { cb.checked = e.target.checked; });
    updateSelectedButton();
});
document.querySelectorAll('.tabs .tab').forEach(tab => tab.addEventListener('click', () => {
    document.querySelectorAll('.tabs .tab').forEach(t => t.classList.remove('is-active'));
    tab.classList.add('is-active');
    paymentStatus = tab.dataset.status;
    loadPayments();
}));
document.getElementById('pay-settings-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        await apiRequest('/api/v1/admin/payment-settings', {
            method: 'PUT',
            body: JSON.stringify({
                card_number: document.getElementById('pay-card-number').value,
                card_holder: document.getElementById('pay-card-holder').value,
                note: document.getElementById('pay-note').value,
            })
        });
        alert("Rekvizitlar saqlandi. Bot talabalarga shu kartani ko'rsatadi.");
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
});

window.openReceipt = openReceipt;
window.approvePayments = approvePayments;
window.rejectPayment = rejectPayment;

if (isLoggedIn()) {
    refreshPaymentsBadge();
}
setInterval(() => { if (isLoggedIn()) refreshPaymentsBadge(); }, 60000);
