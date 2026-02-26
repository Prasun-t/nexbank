$(document).ready(function () {

  // ─── SIDEBAR TOGGLE ────────────────────────────────────────────────────────
  $('#sidebarToggle').on('click', function () {
    if (window.innerWidth <= 768) {
      $('body').toggleClass('sidebar-open');
    } else {
      $('body').toggleClass('sidebar-collapsed');
    }
  });

  // Close sidebar on mobile when clicking outside
  $(document).on('click', function (e) {
    if (window.innerWidth <= 768) {
      if (!$(e.target).closest('#sidebar, #sidebarToggle').length) {
        $('body').removeClass('sidebar-open');
      }
    }
  });

  // ─── AUTO-DISMISS ALERTS ───────────────────────────────────────────────────
  setTimeout(function () {
    $('.alert.alert-success, .alert.alert-info').fadeOut(600);
  }, 4000);

  // ─── PASSWORD TOGGLE (login page) ─────────────────────────────────────────
  $('#togglePassword').on('click', function () {
    const input = $('#loginPassword');
    const icon = $(this).find('i');
    if (input.attr('type') === 'password') {
      input.attr('type', 'text');
      icon.removeClass('fa-eye').addClass('fa-eye-slash');
    } else {
      input.attr('type', 'password');
      icon.removeClass('fa-eye-slash').addClass('fa-eye');
    }
  });

  // ─── PASSWORD TOGGLE (register) ────────────────────────────────────────────
  $('#toggleRegPassword').on('click', function () {
    const input = $('#regPassword');
    const icon = $(this).find('i');
    if (input.attr('type') === 'password') {
      input.attr('type', 'text');
      icon.removeClass('fa-eye').addClass('fa-eye-slash');
    } else {
      input.attr('type', 'password');
      icon.removeClass('fa-eye-slash').addClass('fa-eye');
    }
  });

  // ─── PASSWORD STRENGTH METER ───────────────────────────────────────────────
  $('#regPassword').on('input', function () {
    const val = $(this).val();
    const bar = $('#strengthBar');
    const progress = $('#strengthProgress');
    const text = $('#strengthText');

    if (!val) { bar.addClass('d-none'); return; }
    bar.removeClass('d-none');

    let score = 0;
    if (val.length >= 6) score++;
    if (val.length >= 10) score++;
    if (/[A-Z]/.test(val)) score++;
    if (/[0-9]/.test(val)) score++;
    if (/[^A-Za-z0-9]/.test(val)) score++;

    const levels = [
      { pct: 20, cls: 'bg-danger', label: 'Very Weak' },
      { pct: 40, cls: 'bg-warning', label: 'Weak' },
      { pct: 60, cls: 'bg-info', label: 'Fair' },
      { pct: 80, cls: 'bg-primary', label: 'Strong' },
      { pct: 100, cls: 'bg-success', label: 'Very Strong' },
    ];
    const l = levels[score - 1] || levels[0];
    progress.css('width', l.pct + '%').attr('class', 'progress-bar ' + l.cls);
    text.text(l.label);
  });

  // ─── LOGIN FORM VALIDATION ─────────────────────────────────────────────────
  $('#loginForm').on('submit', function (e) {
    let valid = true;
    const email = $('input[name="email"]').val().trim();
    const password = $('input[name="password"]').val();

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      $('#emailError').removeClass('d-none');
      valid = false;
    } else {
      $('#emailError').addClass('d-none');
    }

    if (!password) {
      $('#passwordError').removeClass('d-none');
      valid = false;
    } else {
      $('#passwordError').addClass('d-none');
    }

    if (!valid) e.preventDefault();
  });

  // ─── REGISTER FORM VALIDATION ──────────────────────────────────────────────
  $('#registerForm').on('submit', function (e) {
    let valid = true;

    const name = $('input[name="full_name"]').val().trim();
    if (!name) {
      $('#nameError').removeClass('d-none');
      valid = false;
    } else {
      $('#nameError').addClass('d-none');
    }

    const email = $('input[name="email"]').val().trim();
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      $('#emailError').removeClass('d-none');
      valid = false;
    } else {
      $('#emailError').addClass('d-none');
    }

    const pw = $('#regPassword').val();
    if (!pw || pw.length < 6) {
      $('#passwordError').removeClass('d-none');
      valid = false;
    } else {
      $('#passwordError').addClass('d-none');
    }

    const confirm = $('#confirmPassword').val();
    if (pw !== confirm) {
      $('#confirmError').removeClass('d-none');
      valid = false;
    } else {
      $('#confirmError').addClass('d-none');
    }

    if (!valid) e.preventDefault();
  });

  // ─── LOADING SPINNER ON FORM SUBMIT ───────────────────────────────────────
  $('form').on('submit', function () {
    const btn = $(this).find('button[type="submit"]');
    if (btn.length && !btn.prop('disabled')) {
      const originalHtml = btn.html();
      btn.html('<span class="spinner-border spinner-border-sm me-2"></span>Processing...');
      btn.prop('disabled', true);
      // Re-enable if validation prevented submit
      setTimeout(() => {
        btn.html(originalHtml);
        btn.prop('disabled', false);
      }, 5000);
    }
  });

  // ─── ACTIVE NAV HIGHLIGHT ─────────────────────────────────────────────────
  const path = window.location.pathname;
  $('#sidebar .nav-link').each(function () {
    if ($(this).attr('href') === path) {
      $(this).addClass('active');
    }
  });

  // ─── NUMBER FORMAT DISPLAY ─────────────────────────────────────────────────
  // Format currency inputs on blur
  $('input[type="number"][name="amount"]').on('blur', function () {
    const val = parseFloat($(this).val());
    if (!isNaN(val)) {
      $(this).val(val.toFixed(2));
    }
  });

});

// ─── Jinja2 helper (exposed to templates) ────────────────────────────────────
function formatCurrency(amount) {
  return '$' + parseFloat(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
