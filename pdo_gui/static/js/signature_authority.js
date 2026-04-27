/**
 * JavaScript for Signature Authority pages.
 *
 * On the create page: shows a loading overlay on form submit.
 * On the dashboard: dynamically renders claim fields based on the selected
 * template, auto-fills the "key" claim with the subject's channel public key,
 * and submits the sign-credential form via AJAX.
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

const createForm = document.getElementById('sa-create-form');
if (createForm) {
    createForm.addEventListener('submit', () => {
        showLoading('Creating signature authority on the blockchain… This may take a minute.');
    });
}

// ── Dashboard page ───────────────────────────────────────────────────────────

const templateSelect = document.getElementById('template-select');
const subjectSelect  = document.getElementById('subject-select');
const claimsContainer = document.getElementById('claims-container');
const claimsFields    = document.getElementById('claims-fields');
const signBtn         = document.getElementById('sign-btn');
const signForm        = document.getElementById('sign-credential-form');
const signResult      = document.getElementById('sign-result');

function buildClaimsFields(claimsKeys) {
    claimsFields.innerHTML = '';
    claimsKeys.forEach(key => {
        const group = document.createElement('div');
        group.className = 'form-group';
        group.innerHTML = `
            <label for="claim-${key}">${key}</label>
            <input type="text" id="claim-${key}" data-claim-key="${key}" required placeholder="${key}">
        `;
        claimsFields.appendChild(group);
    });
}

async function maybeFillChannelKey() {
    const tplId = templateSelect && templateSelect.value;
    if (!tplId || !TEMPLATES_DATA || !TEMPLATES_DATA[tplId]) return;
    const tpl = TEMPLATES_DATA[tplId];
    if (tpl.type_ !== 'public_key') return;

    const userId = subjectSelect && subjectSelect.value;
    if (!userId) return;

    try {
        const url = CHANNEL_KEY_URL.replace('{id}', userId);
        const res = await fetch(url);
        const data = await res.json();
        if (data.key) {
            const keyInput = document.getElementById('claim-key');
            if (keyInput) keyInput.value = data.key;
        }
    } catch (_) { /* non-fatal */ }
}

function updateClaimsForm() {
    const tplId = templateSelect && templateSelect.value;
    if (!tplId || !TEMPLATES_DATA || !TEMPLATES_DATA[tplId]) {
        claimsContainer && claimsContainer.classList.add('hidden');
        signBtn && (signBtn.disabled = true);
        return;
    }

    const tpl = TEMPLATES_DATA[tplId];
    buildClaimsFields(tpl.claims_keys);
    claimsContainer.classList.remove('hidden');
    signBtn.disabled = false;

    maybeFillChannelKey();
}

if (templateSelect) {
    templateSelect.addEventListener('change', updateClaimsForm);
}

if (subjectSelect) {
    subjectSelect.addEventListener('change', maybeFillChannelKey);
}

if (signForm) {
    signForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        signResult.className = 'alert hidden';

        const tplId = templateSelect.value;
        const userId = subjectSelect.value;
        if (!tplId || !userId) {
            signResult.textContent = 'Please select a template and a subject user.';
            signResult.className = 'alert alert-error';
            return;
        }

        // Collect claims from inputs
        const claims = {};
        claimsFields.querySelectorAll('[data-claim-key]').forEach(input => {
            claims[input.dataset.claimKey] = input.value.trim();
        });

        const formData = new FormData();
        formData.append('template_id', tplId);
        formData.append('subject_user_id', userId);
        formData.append('claims', JSON.stringify(claims));
        formData.append('csrfmiddlewaretoken', getCsrfToken());

        showLoading('Signing credential on the blockchain…');
        signBtn.disabled = true;

        try {
            const res = await fetch(SIGN_URL, { method: 'POST', body: formData });
            const data = await res.json();
            hideLoading();
            signBtn.disabled = false;

            if (data.success) {
                signResult.textContent = data.message || 'Credential signed successfully.';
                signResult.className = 'alert alert-success';
                // Reset form
                templateSelect.value = '';
                subjectSelect.value = '';
                claimsContainer.classList.add('hidden');
                showToast('Credential signed!', 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                signResult.textContent = data.error || 'Failed to sign credential.';
                signResult.className = 'alert alert-error';
            }
        } catch (err) {
            hideLoading();
            signBtn.disabled = false;
            signResult.textContent = 'Network error: ' + err.message;
            signResult.className = 'alert alert-error';
        }
    });
}
