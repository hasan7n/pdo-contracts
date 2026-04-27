/**
 * JavaScript for Policy pages.
 *
 * On the create page: shows a loading overlay on submit.
 * On the dashboard: handles the tab navigation, register-authority AJAX form,
 * and set-policy-data AJAX form.
 */

function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    setTimeout(() => { toast.classList.add('hidden'); }, 4000);
}

function showLoading(message) {
    document.getElementById('loading-message').textContent = message || 'Processing…';
    document.getElementById('loading-overlay').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

// ── Create page ──────────────────────────────────────────────────────────────

const createForm = document.getElementById('policy-create-form');
if (createForm) {
    createForm.addEventListener('submit', () => {
        showLoading('Creating policy on the blockchain… This may take a minute.');
    });
}

// ── Dashboard: Tab navigation ─────────────────────────────────────────────────

const tabBtns = document.querySelectorAll('.tab-btn');
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.add('hidden'));
        const target = document.getElementById('tab-' + btn.dataset.tab);
        if (target) target.classList.remove('hidden');
    });
});

// ── Dashboard: Register authority ─────────────────────────────────────────────

const registerForm   = document.getElementById('register-authority-form');
const registerResult = document.getElementById('register-result');

if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        registerResult.className = 'alert hidden';

        const saId = document.getElementById('sa-select').value;
        const credType = document.getElementById('credential-type-input').value.trim();

        if (!saId || !credType) {
            registerResult.textContent = 'Please select a signature authority and enter a credential type.';
            registerResult.className = 'alert alert-error';
            return;
        }

        const formData = new FormData();
        formData.append('signature_authority_id', saId);
        formData.append('credential_type', credType);
        formData.append('csrfmiddlewaretoken', getCsrfToken());

        showLoading('Registering trusted authority…');

        try {
            const res = await fetch(REGISTER_AUTHORITY_URL, { method: 'POST', body: formData });
            const data = await res.json();
            hideLoading();

            if (data.success) {
                registerResult.textContent = 'Authority registered successfully.';
                registerResult.className = 'alert alert-success';
                showToast('Authority registered!', 'success');
                setTimeout(() => location.reload(), 1200);
            } else {
                registerResult.textContent = data.error || 'Registration failed.';
                registerResult.className = 'alert alert-error';
            }
        } catch (err) {
            hideLoading();
            registerResult.textContent = 'Network error: ' + err.message;
            registerResult.className = 'alert alert-error';
        }
    });
}

// ── Dashboard: Set policy data ────────────────────────────────────────────────

const setDataForm   = document.getElementById('set-policy-data-form');
const setDataResult = document.getElementById('set-data-result');

if (setDataForm) {
    setDataForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        setDataResult.className = 'alert hidden';

        const raw = document.getElementById('policy-data-input').value.trim();
        let parsed;
        try {
            parsed = JSON.parse(raw);
        } catch (_) {
            setDataResult.textContent = 'Invalid JSON — please check your input.';
            setDataResult.className = 'alert alert-error';
            return;
        }

        const formData = new FormData();
        formData.append('policy_data', JSON.stringify(parsed));
        formData.append('csrfmiddlewaretoken', getCsrfToken());

        showLoading('Updating policy data on the blockchain…');

        try {
            const res = await fetch(SET_POLICY_DATA_URL, { method: 'POST', body: formData });
            const data = await res.json();
            hideLoading();

            if (data.success) {
                setDataResult.textContent = 'Policy data updated successfully.';
                setDataResult.className = 'alert alert-success';
                showToast('Policy data set!', 'success');
                setTimeout(() => location.reload(), 1200);
            } else {
                setDataResult.textContent = data.error || 'Failed to set policy data.';
                setDataResult.className = 'alert alert-error';
            }
        } catch (err) {
            hideLoading();
            setDataResult.textContent = 'Network error: ' + err.message;
            setDataResult.className = 'alert alert-error';
        }
    });
}
