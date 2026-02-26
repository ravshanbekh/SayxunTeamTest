/**
 * Main application logic for test taking
 */

const API_BASE = window.location.origin;
let sessionToken = null;
let timer = null;
let mcqAnswers = {};
let writtenAnswers = {};

// Get session token from URL
function getSessionToken() {
    const params = new URLSearchParams(window.location.search);
    return params.get('token');
}

// Show/hide loading
function setLoading(isLoading) {
    const loading = document.getElementById('loading');
    if (isLoading) {
        loading.classList.remove('hidden');
    } else {
        loading.classList.add('hidden');
    }
}

// Load session and start test
async function loadSession() {
    sessionToken = getSessionToken();

    if (!sessionToken) {
        alert('Test havolasi noto\'g\'ri. Iltimos, botdan yangi havola oling.');
        return;
    }

    try {
        setLoading(true);

        // Get session details
        const response = await fetch(`${API_BASE}/api/v1/sessions/${sessionToken}`);

        if (!response.ok) {
            throw new Error('Sessiya topilmadi yoki muddati tugagan');
        }

        const session = await response.json();

        // Check if session is valid
        if (!session.is_valid) {
            setLoading(false);
            if (session.is_submitted) {
                alert('Bu test allaqachon topshirilgan. Natijalaringizni Telegram botdan tekshiring.');
            } else if (session.is_expired) {
                alert('Test vaqti tugagan. Yangi link olish uchun botga murojaat qiling.');
            } else {
                alert('Bu sessiyaning muddati tugagan yoki topshirilgan.');
            }
            return;
        }

        // Get test details from session (session already has test info)
        document.getElementById('test-title').textContent = session.test_title || 'Test';

        // Initialize UI
        createMCQGrid();
        createWrittenFields();

        // Start timer
        timer = new window.Timer(
            session.expires_at,
            showWarning,
            handleTimeExpire
        );
        timer.start();

    } catch (error) {
        console.error('Error loading session:', error);
        alert('Testni yuklashda xatolik: ' + error.message);
    } finally {
        setLoading(false);
    }
}

// Create MCQ answer grid
function createMCQGrid() {
    const container = document.getElementById('mcq-container');
    container.innerHTML = '';

    for (let i = 1; i <= 35; i++) {
        const item = document.createElement('div');
        item.className = 'mcq-item';

        // Questions 1-32: 4 options (A, B, C, D)
        // Questions 33-35: 6 options (A, B, C, D, E, F)
        const options = i <= 32 ? ['A', 'B', 'C', 'D'] : ['A', 'B', 'C', 'D', 'E', 'F'];

        const optionsHTML = options.map(opt =>
            `<button class="option-btn" data-question="${i}" data-option="${opt}">${opt}</button>`
        ).join('');

        item.innerHTML = `
            <div class="mcq-number">${i}-savol</div>
            <div class="mcq-options">
                ${optionsHTML}
            </div>
        `;
        container.appendChild(item);
    }

    // Add click handlers
    container.addEventListener('click', (e) => {
        if (e.target.classList.contains('option-btn')) {
            const question = e.target.dataset.question;
            const option = e.target.dataset.option;

            // Remove selected class from all options for this question
            const buttons = container.querySelectorAll(`[data-question="${question}"]`);
            buttons.forEach(btn => btn.classList.remove('selected'));

            // Add selected class to clicked option
            e.target.classList.add('selected');

            // Store answer
            mcqAnswers[question] = option;
        }
    });
}

// Create written answer fields with MathLive math-field
function createWrittenFields() {
    const container = document.getElementById('written-container');
    container.innerHTML = '';

    // Questions 36-45: Each has a) and b) sub-parts
    for (let i = 36; i <= 45; i++) {
        const item = document.createElement('div');
        item.className = 'written-item';
        item.innerHTML = `
            <div class="written-number">${i}-savol</div>
            <div class="sub-answer">
                <label>a)</label>
                <div class="math-field-wrapper">
                    <math-field 
                        class="math-input" 
                        id="written-${i}-a"
                        virtual-keyboard-mode="onfocus"
                    ></math-field>
                </div>
            </div>
            <div class="sub-answer">
                <label>b)</label>
                <div class="math-field-wrapper">
                    <math-field 
                        class="math-input" 
                        id="written-${i}-b"
                        virtual-keyboard-mode="onfocus"
                    ></math-field>
                </div>
            </div>
        `;
        container.appendChild(item);

        if (!writtenAnswers[i]) {
            writtenAnswers[i] = { a: '', b: '' };
        }

        // Add input handlers for math-field elements
        const mfA = item.querySelector(`#written-${i}-a`);
        const mfB = item.querySelector(`#written-${i}-b`);

        mfA.addEventListener('input', () => {
            writtenAnswers[i].a = mfA.value; // LaTeX string
        });
        mfB.addEventListener('input', () => {
            writtenAnswers[i].b = mfB.value; // LaTeX string
        });
    }
}

// Show warning
function showWarning() {
    const warning = document.getElementById('warning');
    warning.style.display = 'block';
}

// Handle time expire - auto submit
async function handleTimeExpire() {
    alert('Vaqt tugadi! Testingiz avtomatik topshirilmoqda...');
    await submitTest();
}

// Submit test
let isSubmitting = false;

async function submitTest() {
    if (isSubmitting) return; // Prevent double submit
    isSubmitting = true;

    if (timer) {
        timer.stop();
    }

    // Prepare MCQ answers (1-35)
    const mcqArray = [];
    for (let i = 1; i <= 35; i++) {
        mcqArray.push({
            question_number: i,
            answer: mcqAnswers[i] || null
        });
    }

    // Prepare written answers (36-45 with a/b sub-parts)
    const writtenArray = [];
    for (let i = 36; i <= 45; i++) {
        writtenArray.push({
            question_number: i,
            answer: writtenAnswers[i] || { a: null, b: null }
        });
    }

    const submission = {
        session_token: sessionToken,
        mcq_answers: mcqArray,
        written_answers: writtenArray
    };

    try {
        setLoading(true);

        const response = await fetch(`${API_BASE}/api/v1/results/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(submission)
        });

        // Both 200 (existing result) and 201 (new result) are success
        if (response.ok) {
            const result = await response.json();

            // Disable further interaction
            document.getElementById('submit-btn').disabled = true;
            document.querySelectorAll('.option-btn').forEach(btn => btn.disabled = true);
            document.querySelectorAll('.math-input').forEach(mf => mf.disabled = true);

            // Show results on page
            showResults(result);
        } else {
            let errorMessage = 'Topshirishda xatolik';
            try {
                const error = await response.json();
                errorMessage = error.detail || errorMessage;
            } catch (e) {
                errorMessage = `Server xatoligi (${response.status})`;
            }
            throw new Error(errorMessage);
        }

    } catch (error) {
        console.error('Error submitting test:', error);
        alert('Testni topshirishda xatolik: ' + error.message);
        isSubmitting = false; // Allow retry on error
    } finally {
        setLoading(false);
    }
}

// Setup submit button
document.getElementById('submit-btn').addEventListener('click', async () => {
    const confirmed = confirm('Testni topshirmoqchimisiz? Bu amalni qaytarib bo\'lmaydi.');
    if (confirmed) {
        await submitTest();
    }
});

// Initialize on page load
window.addEventListener('DOMContentLoaded', loadSession);

// Show results after submission
function showResults(result) {
    const container = document.querySelector('.container');

    // Build MCQ results grid (5 per row)
    const mcqAnswers = result.mcq_answers || [];
    let mcqRows = '';
    for (let i = 0; i < mcqAnswers.length; i += 5) {
        const chunk = mcqAnswers.slice(i, i + 5);
        const items = chunk.map(a => {
            const icon = a.is_correct ? '✅' : '❌';
            const cls = a.is_correct ? 'result-correct' : 'result-wrong';
            return `<span class="result-item ${cls}">${a.question_number}-${icon}</span>`;
        }).join('');
        mcqRows += `<div class="result-row">${items}</div>`;
    }

    // Build written results
    const writtenAnswers = result.written_answers || [];
    let writtenHTML = '';
    if (writtenAnswers.length > 0) {
        writtenHTML = writtenAnswers.map(wa => {
            const iconA = (wa.score_a === 1) ? '✅' : '❌';
            const iconB = (wa.score_b === 1) ? '✅' : '❌';
            return `<div class="result-written-item">${wa.question_number}-savol: a) ${iconA}  b) ${iconB}</div>`;
        }).join('');
    }

    const mcqScore = result.mcq_score || 0;
    const writtenScore = result.written_score || 0;
    const totalScore = result.total_score || 0;

    container.innerHTML = `
        <div class="results-page">
            <div class="results-header">
                <div class="results-check">✅</div>
                <h1>Test muvaffaqiyatli topshirildi!</h1>
            </div>

            <div class="results-section">
                <h2>📝 Test savollari (1-35)</h2>
                <div class="results-mcq-grid">
                    ${mcqRows}
                </div>
            </div>

            ${writtenAnswers.length > 0 ? `
            <div class="results-section">
                <h2>✍️ Yozma savollar (36-45)</h2>
                <div class="results-written-grid">
                    ${writtenHTML}
                </div>
            </div>
            ` : ''}

            <div class="results-summary">
                <h2>📈 Umumiy natija</h2>
                <div class="results-scores">
                    <div class="score-item">
                        <div class="score-label">📝 Test</div>
                        <div class="score-value">${mcqScore}/35</div>
                    </div>
                    <div class="score-item">
                        <div class="score-label">✍️ Yozma</div>
                        <div class="score-value">${writtenScore}/20</div>
                    </div>
                    <div class="score-item score-total">
                        <div class="score-label">⭐ Jami</div>
                        <div class="score-value">${totalScore}</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Prevent accidental page close
window.addEventListener('beforeunload', (e) => {
    if (timer && timer.interval) {
        e.preventDefault();
        e.returnValue = '';
    }
});
