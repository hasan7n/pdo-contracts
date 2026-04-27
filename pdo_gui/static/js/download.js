/**
 * JavaScript for the Download Data section of the policy dashboard.
 *
 * Submits the download form via AJAX and shows the resulting data path
 * in a modal popup once the download and decryption complete.
 */

const downloadForm   = document.getElementById('download-form');
const downloadResult = document.getElementById('download-result');

if (downloadForm) {
    downloadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        downloadResult.className = 'alert hidden';

        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', getCsrfToken());

        document.getElementById('loading-message').textContent =
            'Issuing credential and downloading data… This may take a while.';
        document.getElementById('loading-overlay').classList.remove('hidden');

        try {
            const res = await fetch(DOWNLOAD_URL, { method: 'POST', body: formData });
            const data = await res.json();
            document.getElementById('loading-overlay').classList.add('hidden');

            if (data.success) {
                showDataAvailablePopup(data.data_path);
            } else {
                downloadResult.textContent = data.error || 'Download failed.';
                downloadResult.className = 'alert alert-error';
            }
        } catch (err) {
            document.getElementById('loading-overlay').classList.add('hidden');
            downloadResult.textContent = 'Network error: ' + err.message;
            downloadResult.className = 'alert alert-error';
        }
    });
}

function showDataAvailablePopup(path) {
    // Remove any existing popup
    const existing = document.getElementById('data-popup');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'data-popup';
    overlay.style.cssText = `
        position: fixed; inset: 0; background: rgba(0,0,0,0.5);
        display: flex; align-items: center; justify-content: center; z-index: 9997;
    `;

    overlay.innerHTML = `
        <div style="background:#fff; border-radius:12px; padding:2rem 2.5rem;
                    max-width:500px; width:90%; box-shadow:0 8px 32px rgba(0,0,0,0.2);">
            <h2 style="color:#1e3a5f; margin-bottom:1rem;">Data Available</h2>
            <p style="margin-bottom:0.75rem; color:#444;">Your decrypted data is available at:</p>
            <code style="display:block; background:#f4f6f9; border-radius:6px;
                         padding:0.75rem 1rem; word-break:break-all; font-size:0.9rem;
                         color:#1e3a5f;">${path}</code>
            <div style="margin-top:1.5rem; text-align:right;">
                <button onclick="document.getElementById('data-popup').remove()"
                        class="btn btn-primary">OK</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
}

// getCsrfToken is shared — defined in policy.js which loads first on the dashboard.
// For safety, define a fallback here as well.
if (typeof getCsrfToken === 'undefined') {
    window.getCsrfToken = function () {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    };
}
