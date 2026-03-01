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
        const page = e.target.dataset.page;

        document.querySelectorAll('.menu a').forEach(a => a.classList.remove('active'));
        e.target.classList.add('active');

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
        const response = await apiRequest('/api/v1/admin/students?limit=5000');
        const students = await response.json();

        const statsHtml = `
            <div class="stat-card">
                <h3>Jami talabalar</h3>
                <p class="stat-number">${students.length}</p>
            </div>
        `;
        document.getElementById('stats').innerHTML = statsHtml;
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

// Build test card HTML (shared for both types)
function buildTestCard(test) {
    const startStr = formatDateTime(test.start_time);
    const endStr = formatDateTime(test.end_time);
    return `
        <div class="test-card">
            <h3>${test.title}</h3>
            <p>Kod: ${test.test_code}</p>
            <p>${test.is_active ? '✅ Faol' : '❌ Nofaol'}</p>
            <p>⏰ Boshlanish: ${startStr}</p>
            <p>⏰ Tugash: ${endStr}</p>
            ${test.extra_minutes > 0 ? `<p>➕ Qo'shimcha: ${test.extra_minutes} daqiqa</p>` : ''}
            <div class="test-card-actions">
                <button class="btn-export" onclick="exportExcel('${test.id}')">📊 Excel yuklab olish</button>
                <button class="btn-export" onclick="exportPDF('${test.id}')">📄 PDF yuklab olish</button>
                <button class="btn-edit" onclick="openEditModal('${test.id}', '${test.test_type || 'sertifikat'}')">✏️ Tahrirlash</button>
                <button class="btn-primary" onclick="extendAllSessions('${test.id}', '${test.title}')">⏱️ +5 min</button>
                <button class="btn-delete" onclick="deleteTest('${test.id}', '${test.title}')">🗑️ O'chirish</button>
                <button class="btn-reset" onclick="clearSessions('${test.id}', '${test.title}')">🔄 Sessiyalarni tozalash</button>
            </div>
        </div>
    `;
}

// ==========================================
// SERTIFIKAT TESTS
// ==========================================
async function loadTests() {
    try {
        const response = await apiRequest('/api/v1/tests/?test_type=sertifikat');
        const tests = await response.json();

        let html = '<div class="test-cards">';
        tests.forEach(test => { html += buildTestCard(test); });
        html += '</div>';

        document.getElementById('tests-list').innerHTML = html;
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

        let html = '<div class="test-cards">';
        tests.forEach(test => { html += buildTestCard(test); });
        html += '</div>';

        document.getElementById('prezident-list').innerHTML = html;
    } catch (error) {
        console.error('Error loading prezident tests:', error);
    }
}

// ==========================================
// EXPORT / DELETE / EXTEND (shared)
// ==========================================
async function exportExcel(testId) {
    try {
        const response = await fetch(`${API_BASE}/api/v1/admin/reports/${testId}/excel`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('adminToken')}` }
        });
        if (!response.ok) throw new Error('Yuklab olishda xatolik');
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'test_results.xlsx'; a.click();
        URL.revokeObjectURL(url);
    } catch (error) {
        alert('Excel export xatolik: ' + error.message);
    }
}

async function exportPDF(testId) {
    try {
        const response = await fetch(`${API_BASE}/api/v1/admin/reports/${testId}/pdf`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('adminToken')}` }
        });
        if (!response.ok) throw new Error('Yuklab olishda xatolik');
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'test_results.pdf'; a.click();
        URL.revokeObjectURL(url);
    } catch (error) {
        alert('PDF export xatolik: ' + error.message);
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
                mcqGrid += `<div class="mcq-answer-input"><label>Q${i}:</label><select id="edit-prez-mcq-${i}">${optionsHTML}</select></div>`;
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
                mcqGrid += `<div class="mcq-answer-input"><label>Q${i}:</label><select id="edit-mcq-${i}">${optionsHTML}</select></div>`;
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
                        <h4>Savol ${i}</h4>
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
        mcqGrid += `<div class="mcq-answer-input"><label>Q${i}:</label><select id="mcq-${i}">${optionsHTML}</select></div>`;
    }

    let openEndedHTML = '<div class="open-ended-section"><h3>Yozma savollar (36-45)</h3>';
    for (let i = 36; i <= 45; i++) {
        openEndedHTML += `
            <div class="open-question">
                <h4>Savol ${i}</h4>
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
        mcqGrid += `<div class="mcq-answer-input"><label>Q${i}:</label><select id="prez-mcq-${i}">${optionsHTML}</select></div>`;
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
    container.innerHTML = '<p style="color: #666;">Adminlar ro\'yxati faqat yangi admin qo\'shish uchun.</p>';
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
    if (password.length < 4) {
        alert('Parol kamida 4 ta belgidan iborat bo\'lishi kerak!');
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
