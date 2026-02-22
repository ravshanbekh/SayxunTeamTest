/**
 * Dashboard and main admin functionality
 */

// MathLive virtual keyboard: resize modal when keyboard appears/disappears
if (window.mathVirtualKeyboard) {
    window.mathVirtualKeyboard.addEventListener('geometrychange', () => {
        const kbRect = window.mathVirtualKeyboard.boundingRect;
        // Find any visible modal-content
        const editModal = document.getElementById('edit-test-modal');
        const createModal = document.getElementById('create-test-modal');
        const visibleModal = (editModal && !editModal.classList.contains('hidden')) ? editModal
            : (createModal && !createModal.classList.contains('hidden')) ? createModal : null;

        if (!visibleModal) return;
        const modalContent = visibleModal.querySelector('.modal-content');
        if (!modalContent) return;

        if (kbRect && kbRect.height > 0) {
            // Keyboard is visible — shrink modal content to fit above keyboard
            const availableHeight = window.innerHeight - kbRect.height - 20;
            modalContent.style.maxHeight = availableHeight + 'px';
            modalContent.style.transition = 'max-height 0.2s ease';

            // Auto-scroll focused math-field into view
            const focused = modalContent.querySelector('math-field:focus-within');
            if (focused) {
                setTimeout(() => focused.scrollIntoView({ behavior: 'smooth', block: 'center' }), 100);
            }
        } else {
            // Keyboard hidden — restore normal height
            modalContent.style.maxHeight = '90vh';
        }
    });
}

// Page navigation
document.querySelectorAll('.menu a[data-page]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const page = e.target.dataset.page;

        // Update active link
        document.querySelectorAll('.menu a').forEach(a => a.classList.remove('active'));
        e.target.classList.add('active');

        // Show page
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(page + '-page').classList.add('active');

        // Load page data
        if (page === 'dashboard') loadDashboard();
        if (page === 'tests') loadTests();


        if (page === 'students') loadStudents();
        if (page === 'admins') loadAdmins();
    });
});

// Load dashboard
async function loadDashboard() {
    try {
        const response = await apiRequest('/api/v1/admin/students');
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

// Helper to format datetime
function formatDateTime(isoStr) {
    if (!isoStr) return 'Belgilanmagan';
    const d = new Date(isoStr);
    return d.toLocaleString('uz-UZ', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

// Helper to convert ISO to datetime-local input format
function toDatetimeLocal(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    // Adjust for timezone offset
    const offset = d.getTimezoneOffset();
    const adjusted = new Date(d.getTime() - offset * 60 * 1000);
    return adjusted.toISOString().slice(0, 16);
}

// Load tests
async function loadTests() {
    try {
        const response = await apiRequest('/api/v1/tests/');
        const tests = await response.json();

        let html = '<div class="test-cards">';
        tests.forEach(test => {
            const startStr = formatDateTime(test.start_time);
            const endStr = formatDateTime(test.end_time);
            html += `
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
                        <button class="btn-edit" onclick="openEditModal('${test.id}')">✏️ Tahrirlash</button>
                        <button class="btn-primary" onclick="extendAllSessions('${test.id}', '${test.title}')">⏱️ +5 min</button>
                        <button class="btn-delete" onclick="deleteTest('${test.id}', '${test.title}')">🗑️ O'chirish</button>
                        <button class="btn-reset" onclick="clearSessions('${test.id}', '${test.title}')">🔄 Sessiyalarni tozalash</button>
                    </div>
                </div>
            `;
        });
        html += '</div>';

        document.getElementById('tests-list').innerHTML = html;
    } catch (error) {
        console.error('Error loading tests:', error);
    }
}



// Load students
async function loadStudents() {
    try {
        const response = await apiRequest('/api/v1/admin/students');
        const students = await response.json();

        let html = '<table><tr><th>Ism</th><th>Familiya</th><th>Viloyat</th><th>Ro\'yxatdan o\'tgan</th></tr>';
        students.forEach(student => {
            const date = new Date(student.created_at).toLocaleDateString();
            html += `<tr><td>${student.full_name}</td><td>${student.surname}</td><td>${student.region}</td><td>${date}</td></tr>`;
        });
        html += '</table>';

        document.getElementById('students-list').innerHTML = html;
    } catch (error) {
        console.error('Error loading students:', error);
    }
}

// Export functions
async function exportExcel(testId) {
    try {
        const response = await fetch(`${API_BASE}/api/v1/admin/export/${testId}/excel`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('adminToken')}`
            }
        });
        if (!response.ok) throw new Error('Yuklab olishda xatolik');
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'test_results.xlsx';
        a.click();
        URL.revokeObjectURL(url);
    } catch (error) {
        alert('Excel export xatolik: ' + error.message);
    }
}

async function exportPDF(testId) {
    try {
        const response = await fetch(`${API_BASE}/api/v1/admin/export/${testId}/pdf`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('adminToken')}`
            }
        });
        if (!response.ok) throw new Error('Yuklab olishda xatolik');
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'test_results.pdf';
        a.click();
        URL.revokeObjectURL(url);
    } catch (error) {
        alert('PDF export xatolik: ' + error.message);
    }
}

// ==========================================
// DELETE TEST
// ==========================================
async function deleteTest(testId, testTitle) {
    if (!confirm(`"${testTitle}" testini o'chirishni xohlaysizmi?\n\nBu amalni qaytarib bo'lmaydi! Barcha natijalar ham o'chiriladi.`)) {
        return;
    }

    try {
        await apiRequest(`/api/v1/tests/${testId}`, {
            method: 'DELETE'
        });

        alert('Test muvaffaqiyatli o\'chirildi!');
        loadTests();
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
}

// ==========================================
// CLEAR SESSIONS
// ==========================================
async function clearSessions(testId, testTitle) {
    if (!confirm(`"${testTitle}" testining barcha sessionlarini tozalashni xohlaysizmi?\n\nBarcha natijalar ham o'chiriladi va talabalar testni qayta topshira oladi.`)) {
        return;
    }

    try {
        const response = await apiRequest(`/api/v1/admin/sessions/${testId}`, {
            method: 'DELETE'
        });

        const data = await response.json();
        alert(`Tozalandi!\n${data.sessions_deleted} ta session va ${data.results_deleted} ta natija o'chirildi.`);
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
}

// ==========================================
// EDIT TEST
// ==========================================
let currentEditTestId = null;

async function openEditModal(testId) {
    currentEditTestId = testId;

    try {
        // Load test data with answer key
        const response = await apiRequest(`/api/v1/tests/${testId}`);
        if (!response.ok) {
            throw new Error(`Server xatosi (${response.status})`);
        }
        const test = await response.json();

        // Fill in basic fields
        document.getElementById('edit-test-code').value = test.test_code;
        document.getElementById('edit-test-title').value = test.title;
        document.getElementById('edit-test-desc').value = test.description || '';
        document.getElementById('edit-test-active').checked = test.is_active;
        document.getElementById('edit-test-start-time').value = toDatetimeLocal(test.start_time);
        document.getElementById('edit-test-end-time').value = toDatetimeLocal(test.end_time);

        // Generate MCQ answer inputs
        let mcqGrid = '';
        for (let i = 1; i <= 35; i++) {
            const options = i <= 32
                ? ['A', 'B', 'C', 'D']
                : ['A', 'B', 'C', 'D', 'E', 'F'];

            const currentVal = (test.answer_key && test.answer_key.mcq_answers) ? (test.answer_key.mcq_answers[i] || 'A') : 'A';
            const optionsHTML = options.map(opt =>
                `<option value="${opt}" ${opt === currentVal ? 'selected' : ''}>${opt}</option>`
            ).join('');

            mcqGrid += `
                <div class="mcq-answer-input">
                    <label>Q${i}:</label>
                    <select id="edit-mcq-${i}">
                        ${optionsHTML}
                    </select>
                </div>
            `;
        }

        // Open-ended questions with MathLive math-field
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
                    <div class="sub-answer">
                        <label>a)</label>
                        <math-field id="edit-open-${i}-a" class="admin-math-input" virtual-keyboard-mode="onfocus"></math-field>
                    </div>
                    <div class="sub-answer">
                        <label>b)</label>
                        <math-field id="edit-open-${i}-b" class="admin-math-input" virtual-keyboard-mode="onfocus"></math-field>
                    </div>
                </div>
            `;
        }
        openEndedHTML += '</div>';

        document.getElementById('edit-mcq-answers-grid').innerHTML = mcqGrid + openEndedHTML;
        document.getElementById('edit-test-modal').classList.remove('hidden');

        // Populate math-field values after DOM render
        setTimeout(() => {
            for (const [id, val] of Object.entries(editMathValues)) {
                const mf = document.getElementById(id);
                if (mf && val) mf.value = val;
            }
        }, 100);
    } catch (error) {
        alert('Test ma\'lumotlarini yuklashda xatolik: ' + error.message);
    }
}

document.getElementById('cancel-edit').addEventListener('click', () => {
    document.getElementById('edit-test-modal').classList.add('hidden');
    currentEditTestId = null;
});

document.getElementById('edit-test-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    // Collect MCQ answers
    const mcqAnswers = {};
    for (let i = 1; i <= 35; i++) {
        mcqAnswers[String(i)] = document.getElementById(`edit-mcq-${i}`).value;
    }

    // Collect open-ended answers
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
        answer_key: {
            mcq_answers: mcqAnswers,
            written_questions: writtenQuestions
        }
    };

    try {
        await apiRequest(`/api/v1/tests/${currentEditTestId}`, {
            method: 'PATCH',
            body: JSON.stringify(updateData)
        });

        alert('Test muvaffaqiyatli yangilandi!');
        document.getElementById('edit-test-modal').classList.add('hidden');
        currentEditTestId = null;
        loadTests();
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
});


// ==========================================
// CREATE TEST MODAL
// ==========================================
document.getElementById('create-test-btn').addEventListener('click', () => {
    // Generate MCQ answer inputs
    let mcqGrid = '';
    for (let i = 1; i <= 35; i++) {
        const options = i <= 32
            ? ['A', 'B', 'C', 'D']
            : ['A', 'B', 'C', 'D', 'E', 'F'];

        const optionsHTML = options.map(opt => `<option value="${opt}">${opt}</option>`).join('');

        mcqGrid += `
            <div class="mcq-answer-input">
                <label>Q${i}:</label>
                <select id="mcq-${i}">
                    ${optionsHTML}
                </select>
            </div>
        `;
    }

    // Add open-ended questions (36-45) with MathLive math-field
    let openEndedHTML = '<div class="open-ended-section"><h3>Yozma savollar (36-45)</h3>';
    for (let i = 36; i <= 45; i++) {
        openEndedHTML += `
            <div class="open-question">
                <h4>Savol ${i}</h4>
                <div class="sub-answer">
                    <label>a)</label>
                    <math-field id="open-${i}-a" class="admin-math-input" virtual-keyboard-mode="onfocus"></math-field>
                </div>
                <div class="sub-answer">
                    <label>b)</label>
                    <math-field id="open-${i}-b" class="admin-math-input" virtual-keyboard-mode="onfocus"></math-field>
                </div>
            </div>
        `;
    }
    openEndedHTML += '</div>';

    document.getElementById('mcq-answers-grid').innerHTML = mcqGrid + openEndedHTML;

    // Reset form
    document.getElementById('create-test-form').reset();
    document.getElementById('create-test-modal').classList.remove('hidden');
});

document.getElementById('cancel-create').addEventListener('click', () => {
    document.getElementById('create-test-modal').classList.add('hidden');
});

document.getElementById('create-test-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    // Collect MCQ answers (1-35)
    const mcqAnswers = {};
    for (let i = 1; i <= 35; i++) {
        mcqAnswers[String(i)] = document.getElementById(`mcq-${i}`).value;
    }

    // Collect open-ended answers (36-45)
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
        answer_key: {
            mcq_answers: mcqAnswers,
            written_questions: writtenQuestions
        }
    };

    try {
        await apiRequest('/api/v1/tests/', {
            method: 'POST',
            body: JSON.stringify(testData)
        });

        alert('Test muvaffaqiyatli yaratildi!');
        document.getElementById('create-test-modal').classList.add('hidden');
        loadTests();
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
});

// Expose functions globally

window.exportExcel = exportExcel;
window.exportPDF = exportPDF;
window.deleteTest = deleteTest;
window.openEditModal = openEditModal;
window.clearSessions = clearSessions;
window.extendAllSessions = extendAllSessions;

// ==========================================
// EXTEND ALL SESSIONS (+5 min)
// ==========================================
async function extendAllSessions(testId, testTitle) {
    if (!confirm(`"${testTitle}" testidagi barcha faol sessiyalarga +5 daqiqa qo'shilsinmi?`)) {
        return;
    }
    try {
        const response = await apiRequest(`/api/v1/admin/tests/${testId}/extend-all`, {
            method: 'POST'
        });
        const data = await response.json();
        alert(data.message + (data.skipped > 0 ? `\n${data.skipped} ta sessiya limitga yetgan` : ''));
    } catch (error) {
        alert('Xatolik: ' + error.message);
    }
}

// Load dashboard on init
if (isLoggedIn()) {
    loadDashboard();
}

// =================== ADMIN MANAGEMENT ===================

// Load admins list
async function loadAdmins() {
    const container = document.getElementById('admin-list');
    container.innerHTML = '<p style="color: #666;">Adminlar ro\'yxati faqat yangi admin qo\'shish uchun.</p>';
}

// Open add admin modal
document.getElementById('add-admin-btn').addEventListener('click', () => {
    document.getElementById('add-admin-modal').classList.remove('hidden');
    document.getElementById('new-admin-username').value = '';
    document.getElementById('new-admin-password').value = '';
});

// Cancel add admin
document.getElementById('cancel-add-admin').addEventListener('click', () => {
    document.getElementById('add-admin-modal').classList.add('hidden');
});

// Submit new admin
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
            method: 'POST',
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        alert(`✅ Admin "${data.username}" muvaffaqiyatli qo'shildi!`);
        document.getElementById('add-admin-modal').classList.add('hidden');
    } catch (error) {
        alert('❌ Xatolik: ' + error.message);
    }
});
