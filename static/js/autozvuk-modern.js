(function () {
  'use strict';

  function ready(callback) {
    if (document.readyState !== 'loading') {
      callback();
      return;
    }

    document.addEventListener('DOMContentLoaded', callback);
  }

  ready(function () {
    var header = document.querySelector('.az-header');
    var scrollTopButton = document.querySelector('.az-scroll-top');
    var yearNode = document.getElementById('azCurrentYear');
    var alertCloseButtons = document.querySelectorAll('.az-alert-close');

    if (yearNode) {
      yearNode.textContent = new Date().getFullYear();
    }

    function updateScrollState() {
      var isScrolled = window.scrollY > 20;

      if (header) {
        header.classList.toggle('az-scrolled', isScrolled);
      }

      if (scrollTopButton) {
        scrollTopButton.classList.toggle('az-visible', window.scrollY > 420);
      }
    }

    updateScrollState();
    window.addEventListener('scroll', updateScrollState, { passive: true });

    if (scrollTopButton) {
      scrollTopButton.addEventListener('click', function () {
        window.scrollTo({
          top: 0,
          behavior: 'smooth'
        });
      });
    }

    alertCloseButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        var alert = button.closest('.az-alert');

        if (!alert) {
          return;
        }

        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-8px)';

        setTimeout(function () {
          alert.remove();
        }, 220);
      });
    });

    setTimeout(function () {
      document.querySelectorAll('.az-alert').forEach(function (alert) {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-8px)';

        setTimeout(function () {
          alert.remove();
        }, 220);
      });
    }, 6000);

    document.querySelectorAll('.az-main-menu .nav-link:not(.dropdown-toggle)').forEach(function (link) {
      link.addEventListener('click', function () {
        var nav = document.getElementById('azMainNav');

        if (!nav || typeof window.jQuery === 'undefined') {
          return;
        }

        if (window.innerWidth < 992 && nav.classList.contains('show')) {
          window.jQuery(nav).collapse('hide');
        }
      });
    });
  });
})();


(function () {
  'use strict';

  function ready(callback) {
    if (document.readyState !== 'loading') {
      callback();
      return;
    }

    document.addEventListener('DOMContentLoaded', callback);
  }

  ready(function () {
    var banner = document.getElementById('azCookieBanner');
    var acceptButton = document.getElementById('azAcceptCookies');

    if (!banner || !acceptButton) {
      return;
    }

    setTimeout(function () {
      banner.classList.add('az-cookie-visible');
    }, 250);

    acceptButton.addEventListener('click', function () {
      banner.classList.add('az-cookie-hiding');
      banner.classList.remove('az-cookie-visible');

      document.cookie = [
        'cookies_accepted=true',
        'path=/',
        'max-age=' + 60 * 60 * 24 * 365,
        'SameSite=Lax'
      ].join('; ');

      setTimeout(function () {
        banner.remove();
      }, 460);
    });
  });
})();

(function () {
  'use strict';

  function ready(callback) {
    if (document.readyState !== 'loading') {
      callback();
      return;
    }

    document.addEventListener('DOMContentLoaded', callback);
  }

  ready(function () {
    document.querySelectorAll('.az-print-page').forEach(function (button) {
      button.addEventListener('click', function () {
        window.print();
      });
    });
  });
})();

(function () {
  'use strict';

  function ready(callback) {
    if (document.readyState !== 'loading') {
      callback();
      return;
    }

    document.addEventListener('DOMContentLoaded', callback);
  }

  ready(function () {
    var form = document.getElementById('azSuspensionForm');

    if (!form) {
      return;
    }

    var prefix = form.getAttribute('data-prefix');
    var status = form.getAttribute('data-status');
    var body = document.getElementById('azFormsetBody');
    var template = document.getElementById('azEmptyPartTemplate');
    var addButton = document.querySelector('.az-add-part-row');

    function getWearColor(value) {
      if (value >= 70) {
        return '#dc3545';
      }

      if (value >= 40) {
        return '#f4b214';
      }

      return '#28a745';
    }

    function updateWearUI(slider) {
      var row = slider.closest('.az-suspension-part-row');

      if (!row) {
        return;
      }

      var value = parseInt(slider.value || '0', 10);
      var label = row.querySelector('[data-wear-value]');
      var color = getWearColor(value);

      if (label) {
        label.textContent = value + '%';
      }

      slider.style.background = [
        'linear-gradient(90deg, ',
        color,
        ' 0%, ',
        color,
        ' ',
        value,
        '%, #e5e7eb ',
        value,
        '%, #e5e7eb 100%)'
      ].join('');
    }

    function syncSeverityByWear(slider) {
      var row = slider.closest('.az-suspension-part-row');

      if (!row) {
        return;
      }

      var value = parseInt(slider.value || '0', 10);
      var severity = row.querySelector('select[name$="-severity"]');

      if (!severity || severity.dataset.touched === '1') {
        return;
      }

      if (value >= 70) {
        severity.value = 'crit';
      } else if (value >= 40) {
        severity.value = 'warn';
      } else {
        severity.value = 'ok';
      }
    }

    function updateReplacementHint(slider) {
      var row = slider.closest('.az-suspension-part-row');

      if (!row) {
        return;
      }

      var value = parseInt(slider.value || '0', 10);
      var checkbox = row.querySelector('input[type="checkbox"][name$="-needs_replacement"]');
      var hint = row.querySelector('.replacement-hint');

      if (!hint) {
        return;
      }

      if (checkbox && checkbox.dataset.touched === '1') {
        hint.textContent = '';
        hint.className = 'replacement-hint text-muted';
        return;
      }

      if (value >= 70) {
        hint.textContent = 'Рекомендация: заменить';
        hint.className = 'replacement-hint badge bg-danger';
      } else if (value >= 40) {
        hint.textContent = 'Рекомендация: наблюдать / перепроверить';
        hint.className = 'replacement-hint badge bg-warning text-dark';
      } else {
        hint.textContent = 'Рекомендация: замена не требуется';
        hint.className = 'replacement-hint badge bg-success';
      }
    }

    function bindRow(row) {
      if (!row) {
        return;
      }

      var slider = row.querySelector('.az-wear-slider');
      var severity = row.querySelector('select[name$="-severity"]');
      var checkbox = row.querySelector('input[type="checkbox"][name$="-needs_replacement"]');
      var removeButton = row.querySelector('[data-remove-row]');

      if (severity) {
        severity.addEventListener('change', function () {
          severity.dataset.touched = '1';
        });
      }

      if (checkbox) {
        checkbox.addEventListener('change', function () {
          checkbox.dataset.touched = '1';

          var hint = row.querySelector('.replacement-hint');

          if (hint) {
            hint.textContent = '';
            hint.className = 'replacement-hint text-muted';
          }
        });
      }

      if (slider) {
        slider.addEventListener('input', function () {
          updateWearUI(slider);
          syncSeverityByWear(slider);
          updateReplacementHint(slider);
        });

        updateWearUI(slider);
        syncSeverityByWear(slider);

        var hint = row.querySelector('.replacement-hint');

        if (!hint || !hint.textContent.trim()) {
          updateReplacementHint(slider);
        }
      }

      if (removeButton) {
        removeButton.addEventListener('click', function () {
          removeRow(row);
        });
      }
    }

    function removeRow(row) {
      var deleteCheckbox = row.querySelector('input[type="checkbox"][name$="-DELETE"]');

      if (deleteCheckbox) {
        deleteCheckbox.checked = true;
        row.classList.add('az-row-removed');
        return;
      }

      row.remove();
    }

    function addForm() {
      var totalForms = document.getElementById('id_' + prefix + '-TOTAL_FORMS');

      if (!totalForms || !template || !body) {
        return;
      }

      var index = parseInt(totalForms.value || '0', 10);
      var html = template.innerHTML.split('__prefix__').join(index);
      var wrapper = document.createElement('tbody');

      wrapper.innerHTML = html.trim();

      var newRow = wrapper.querySelector('.az-suspension-part-row');

      if (!newRow) {
        return;
      }

      body.appendChild(newRow);
      totalForms.value = index + 1;

      bindRow(newRow);

      var firstInput = newRow.querySelector('input, select, textarea');

      if (firstInput) {
        firstInput.focus();
      }
    }

    if (addButton) {
      addButton.addEventListener('click', addForm);
    }

    document.querySelectorAll('.az-suspension-part-row').forEach(function (row) {
      bindRow(row);
    });

    if (status === 'signed') {
      form.querySelectorAll('input, select, textarea, button').forEach(function (element) {
        element.disabled = true;
      });
    }
  });
})();

(function () {
  'use strict';

  function ready(callback) {
    if (document.readyState !== 'loading') {
      callback();
      return;
    }

    document.addEventListener('DOMContentLoaded', callback);
  }

  ready(function () {
    var form = document.getElementById('azPasswordResetForm');

    if (!form) {
      return;
    }

    var password1 = document.getElementById('id_password1');
    var password2 = document.getElementById('id_password2');
    var matchHint = document.getElementById('azPasswordMatchHint');

    var rules = {
      length: document.querySelector('[data-rule="length"]'),
      upper: document.querySelector('[data-rule="upper"]'),
      lower: document.querySelector('[data-rule="lower"]'),
      digit: document.querySelector('[data-rule="digit"]'),
      special: document.querySelector('[data-rule="special"]')
    };

    function setRule(name, ok) {
      if (!rules[name]) {
        return;
      }

      rules[name].classList.toggle('az-rule-ok', ok);
    }

    function getChecks(value) {
      return {
        length: value.length >= 8,
        upper: /[A-ZА-Я]/.test(value),
        lower: /[a-zа-я]/.test(value),
        digit: /\d/.test(value),
        special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(value)
      };
    }

    function validatePasswordRules() {
      if (!password1) {
        return true;
      }

      var value = password1.value || '';
      var checks = getChecks(value);

      Object.keys(checks).forEach(function (key) {
        setRule(key, checks[key]);
      });

      return Object.keys(checks).every(function (key) {
        return checks[key];
      });
    }

    function validateMatch() {
      if (!password1 || !password2) {
        return true;
      }

      var ok = password1.value === password2.value;

      if (matchHint) {
        matchHint.hidden = ok || !password2.value;
      }

      password2.classList.toggle('is-invalid', !ok && !!password2.value);

      return ok;
    }

    function validateAll() {
      var rulesOk = validatePasswordRules();
      var matchOk = validateMatch();

      return rulesOk && matchOk;
    }

    if (password1) {
      password1.addEventListener('input', validateAll);
    }

    if (password2) {
      password2.addEventListener('input', validateAll);
    }

    form.addEventListener('submit', function (event) {
      if (!validateAll()) {
        event.preventDefault();

        if (password1 && !validatePasswordRules()) {
          password1.focus();
        } else if (password2 && !validateMatch()) {
          password2.focus();
        }
      }
    });

    validateAll();
  });
})();

