// On the "Expose Asset" page, prefill the policy_data textarea from the
// selected policy template's schema (carried in data-schema on the option).

(function () {
    function init() {
        var select = document.getElementById('id_policy_template');
        var textarea = document.getElementById('id_policy_data');
        if (!select || !textarea) return;

        function prefill() {
            var opt = select.options[select.selectedIndex];
            if (!opt) return;
            try {
                var schema = JSON.parse(opt.dataset.schema || '{}');
                textarea.value = JSON.stringify(schema, null, 2);
            } catch (e) { /* leave textarea untouched */ }
        }
        select.addEventListener('change', prefill);
        prefill();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
