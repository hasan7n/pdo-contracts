// Populate the "Use Asset" modal with the clicked asset's DID + name.
// The trigger button carries:
//   data-modal-open="use-modal"
//   data-asset-did="..."
//   data-asset-name="..."

document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-modal-open="use-modal"]');
    if (!btn) return;
    var didEl = document.getElementById('use-asset-did');
    var nameEl = document.getElementById('use-asset-name');
    if (didEl) didEl.value = btn.dataset.assetDid || '';
    if (nameEl) nameEl.textContent = btn.dataset.assetName || '';
});
