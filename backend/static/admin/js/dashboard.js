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
    });
});

// ==========================================
// DASHBOARD
// ==========================================
async function loadDashboard() {
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
            document.getElementById('edit-prez-test-start-time').value = toDatetimeLocal(test.start_time);
            document.getElementById('edit-prez-test-end-time').value = toDatetimeLocal(test.end_time);

            // 40 MCQ (A-D)
            let mcqGrid = '';
            for (let i = 1; i <= 40; i++) {
                const options = ['A', 'B', 'C', 'D'];
                const currentVal = (test.answer_key && test.answer_key.mcq_answers) ? (test.answer_key.mcq_answers[i] || 'A') : 'A';
                const optionsHTML = options.map(opt =>
                    `<option value="${opt}" ${opt === currentVal ? 'selected' : ''}>${opt}</option>`
                ).join('');
                mcqGrid += `<div class="mcq-answer-input"><label>${i}</label><select id="edit-prez-mcq-${i}">${optionsHTML}</select></div>`;
            }
            document.getElementById('edit-prez-mcq-answers-grid').innerHTML = mcqGrid;
            document.getElementById('edit-prezident-modal').classList.remove('hidden');
        } else {
            // Sertifikat edit modal (existing logic)
            document.getElementById('edit-test-code').value = test.test_code;
            document.getElementById('edit-test-title').value = test.title;
            document.getElementById('edit-test-desc').value = test.description || '';
            document.getElementById('edit-test-active').checked = test.is_active;
            document.getElementById('edit-test-start-time').value = toDatetimeLocal(test.start_time);
            document.getElementById('edit-test-end-time').value = toDatetimeLocal(test.end_time);

            let mcqGrid = '';
            for (let i = 1; i <= 35; i++) {
                const options = i <= 32 ? ['A', 'B', 'C', 'D'] : ['A', 'B', 'C', 'D', 'E', 'F'];
                const currentVal = (test.answer_key && test.answer_key.mcq_answers) ? (test.answer_key.mcq_answers[i] || 'A') : 'A';
                const optionsHTML = options.map(opt =>
                    `<option value="${opt}" ${opt === currentVal ? 'selected' : ''}>${opt}</option>`
                ).join('');
                mcqGrid += `<div class="mcq-answer-input"><label>${i}</label><select id="edit-mcq-${i}">${optionsHTML}</select></div>`;
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
        const optionsHTML = options.map(opt => `<option value="${opt}">${opt}</option>`).join('');
        mcqGrid += `<div class="mcq-answer-input"><label>${i}</label><select id="mcq-${i}">${optionsHTML}</select></div>`;
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
        const optionsHTML = options.map(opt => `<option value="${opt}">${opt}</option>`).join('');
        mcqGrid += `<div class="mcq-answer-input"><label>${i}</label><select id="prez-mcq-${i}">${optionsHTML}</select></div>`;
    }

    document.getElementById('prez-mcq-answers-grid').innerHTML = mcqGrid;
    document.getElementById('create-prezident-form').reset();
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
