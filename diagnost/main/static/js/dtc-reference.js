(function () {
  function normalizeDtcInput(input) {
    if (!input) return;

    input.addEventListener('input', function () {
      var cursor = input.selectionStart;
      input.value = input.value.toUpperCase().replace(/\s+/g, '');
      input.setSelectionRange(cursor, cursor);
    });
  }

  function initDtcSearchForms() {
    var inputs = document.querySelectorAll('[data-dtc-input]');
    inputs.forEach(normalizeDtcInput);
  }

  document.addEventListener('DOMContentLoaded', initDtcSearchForms);
})();
