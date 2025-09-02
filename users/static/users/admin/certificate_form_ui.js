// Admin UI for Certificates:
// - In-input native calendar for date_earned; hide Django "datetimeshortcuts".
// - date_earned: block future days (max=today), grey/disable them in popup.
// - Per-field Reset links + Reset all button.
// - Clear field errors as you type/change; top error banner shows/hides like projects.
//
// Server still enforces "no future" in Certificate.clean().

(function () {
  function onReady(fn) {
    if (document.readyState !== "loading") return fn();
    document.addEventListener("DOMContentLoaded", fn);
  }

  function toLocalISO(d) {
    const z = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
    return z.toISOString().slice(0, 10);
  }
  function todayISO() { return toLocalISO(new Date()); }

  function ensureHelpBelow(input, id, text) {
    if (!input) return null;
    let help = document.getElementById(id);
    if (!help) {
      help = document.createElement("div");
      help.id = id;
      help.className = "sf-note";
      input.insertAdjacentElement("afterend", help);
    }
    if (text) help.textContent = text;
    return help;
  }

  // --- Error banner helpers (same behavior as projects) ---
  function countAllErrors() {
    return document.querySelectorAll("#content-main form .errorlist li").length;
  }
  function ensureTopErrorNote() {
    let top = document.querySelector("#content-main .errornote");
    if (!top) {
      top = document.createElement("p");
      top.className = "errornote";
      const form = document.querySelector("#content-main form");
      if (form && form.parentElement) form.parentElement.insertBefore(top, form);
    }
    return top;
  }
  function updateTopErrorNoteVisibility() {
    const n = countAllErrors();
    const top = ensureTopErrorNote();
    if (n > 0) {
      top.textContent = n === 1 ? "Please correct the error below." : "Please correct the errors below.";
      top.style.display = "";
    } else {
      top.style.display = "none";
    }
  }
  function hideTopErrorNote() {
    const top = document.querySelector("#content-main .errornote");
    if (top) top.style.display = "none";
  }
  function clearFieldErrors(el) {
    const row = el.closest(".form-row") || el.closest("div");
    if (!row) return;
    const hadError = !!row.querySelector("ul.errorlist");
    row.querySelectorAll("ul.errorlist").forEach((ul) => ul.remove());
    row.classList.remove("errors");
    if (hadError) hideTopErrorNote();
    setTimeout(updateTopErrorNoteVisibility, 0);
  }

  // --- Django shortcuts & calendar decoration (grey out > today) ---
  function shortcutsFor(input) {
    const row = input.closest(".form-row") || input.parentElement;
    if (!row) return null;
    return row.querySelector(".datetimeshortcuts");
  }
  function toggleShortcuts(input, visible) {
    const box = shortcutsFor(input);
    if (box) box.style.display = visible ? "" : "none";
  }
  function setDateMode(el, asDate) {
    try {
      const target = asDate ? "date" : "text";
      if (el.getAttribute("type") !== target) el.setAttribute("type", target);
    } catch (_) {}
  }

  let activeDateInput = null;
  function visibleCalendarBox() {
    const boxes = Array.from(document.querySelectorAll(".calendarbox"));
    return boxes.find((b) => b.offsetParent !== null);
  }

  const MONTHS = { january:1,february:2,march:3,april:4,may:5,june:6,july:7,august:8,september:9,october:10,november:11,december:12 };
  function pad2(n){ return (n<10?"0":"")+n; }
  function isoFromCaptionAndDay(captionText, dayNum) {
    if (!captionText) return "";
    const parts = captionText.trim().split(/\s+/); // e.g. "September 2025"
    const month = MONTHS[(parts[0] || "").toLowerCase()];
    const year  = parseInt(parts[1], 10);
    if (!year || !month) return "";
    return `${year}-${pad2(month)}-${pad2(dayNum)}`;
  }

  function decorateAdminCalendar(dateInput) {
    const box = visibleCalendarBox();
    if (!box || !dateInput) return;
    const caption = box.querySelector("caption");
    const captionText = caption ? caption.textContent : "";
    const today = todayISO();

    // reset
    box.querySelectorAll("td").forEach((td) => {
      td.classList.remove("sf-cal-disabled");
      const a = td.querySelector("a");
      if (a) { a.style.pointerEvents = ""; a.style.opacity = ""; a.removeAttribute("aria-disabled"); }
    });
    box.querySelectorAll("td.nonday").forEach((td) => td.classList.add("sf-cal-disabled"));

    // grey/disable future days
    box.querySelectorAll("td a").forEach((a) => {
      const dayNum = parseInt(a.textContent, 10);
      if (!dayNum) return;
      const iso = isoFromCaptionAndDay(captionText, dayNum);
      if (!iso) return;
      if (iso > today) {
        const td = a.closest("td");
        if (td) td.classList.add("sf-cal-disabled");
        a.style.pointerEvents = "none";
        a.style.opacity = "0.35";
        a.setAttribute("aria-disabled", "true");
      }
    });
  }

  function patchDateTimeShortcuts(dateInput) {
    const D = window.DateTimeShortcuts;
    if (!D || D.__sf_cert_patched) return;
    D.__sf_cert_patched = true;

    const origHandle = D.handleCalendarCallback ? D.handleCalendarCallback.bind(D) : null;
    const origDismiss = D.dismissCalendar ? D.dismissCalendar.bind(D) : null;

    function afterPick(num) {
      try {
        const input = (D.calendarInputs && D.calendarInputs[num]) || dateInput;
        if (!input) return;
        const today = todayISO();
        const iso = input.value || "";
        if (iso && iso > today) input.value = ""; // refuse future picks
        clearFieldErrors(input);
      } catch (_) {}
      setTimeout(() => decorateAdminCalendar(dateInput), 0);
    }

    if (origHandle)  D.handleCalendarCallback = function (num) { const r = origHandle(num);  afterPick(num); return r; };
    if (origDismiss) D.dismissCalendar        = function (num) { const r = origDismiss(num); afterPick(num); return r; };
  }

  // --- Reset helpers (value/radio/select/multi/file) ---
  function captureInitial(form) {
    const elements = Array.from(form.querySelectorAll("input[id^='id_'], select[id^='id_'], textarea[id^='id_']"));
    elements.forEach((el) => {
      if (el.type === "checkbox") {
        el.dataset.sfInit = JSON.stringify({ kind: "checkbox", checked: el.checked });
      } else if (el.type === "radio") {
        el.dataset.sfInit = JSON.stringify({ kind: "radio", name: el.name, value: el.value, checked: el.checked });
      } else if (el.type === "file") {
        el.dataset.sfInit = JSON.stringify({ kind: "file" });
      } else if (el.multiple) {
        const vals = Array.from(el.options).filter(o => o.selected).map(o => o.value);
        el.dataset.sfInit = JSON.stringify({ kind: "multi", values: vals });
      } else {
        el.dataset.sfInit = JSON.stringify({ kind: "value", value: el.value });
      }
    });
  }

  function restoreInitialFor(el) {
    if (!el || !el.dataset.sfInit) return;
    const init = JSON.parse(el.dataset.sfInit);
    if (init.kind === "checkbox") {
      el.checked = !!init.checked;
      el.dispatchEvent(new Event("change", { bubbles: true }));
    } else if (init.kind === "radio") {
      const group = document.querySelectorAll(`input[type="radio"][name="${CSS.escape(el.name)}"]`);
      group.forEach(r => { r.checked = false; });
      const initiallyChecked = Array.from(group).find(r => {
        try { return JSON.parse(r.dataset.sfInit || "{}").checked; } catch (_) { return false; }
      });
      if (initiallyChecked) initiallyChecked.checked = true;
      (initiallyChecked || el).dispatchEvent(new Event("change", { bubbles: true }));
    } else if (init.kind === "multi") {
      Array.from(el.options).forEach(o => { o.selected = init.values.includes(o.value); });
      el.dispatchEvent(new Event("change", { bubbles: true }));
    } else if (init.kind === "file") {
      // Clear new selection and uncheck Django's "clear" checkbox if present.
      try { el.value = ""; } catch (_) {}
      const clearBox = document.querySelector(`input[type="checkbox"][name="${el.name}-clear"]`);
      if (clearBox) clearBox.checked = false;
      el.dispatchEvent(new Event("change", { bubbles: true }));
    } else {
      el.value = init.value || "";
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }
    clearFieldErrors(el);
  }

  function addResetLinkForField(fieldId, label, onClick) {
    const input = document.getElementById("id_" + fieldId);
    if (!input) return;
    const a = document.createElement("a");
    a.href = "#";
    a.className = "sf-reset-link";
    a.textContent = label || "Reset";
    a.addEventListener("click", function (e) {
      e.preventDefault();
      (onClick || restoreInitialFor)(input);
      input.focus();
    });
    input.insertAdjacentElement("afterend", a);
  }

  function addResetAllButton(form) {
    const submitRow = document.querySelector("#content-main .submit-row") || form;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.id = "sf-reset-all";
    btn.className = "sf-reset-all-button";
    btn.textContent = "Reset all";
    btn.addEventListener("click", function () {
      if (!confirm("Reset this certificate back to the values from when this page loaded?")) return;
      const els = Array.from(form.querySelectorAll("input[id^='id_'], select[id^='id_'], textarea[id^='id_']"));
      els.forEach(restoreInitialFor);
      hideTopErrorNote();
      setTimeout(updateTopErrorNoteVisibility, 0);
      const first = form.querySelector("input, select, textarea");
      if (first) first.focus();
    });
    submitRow.appendChild(btn);
  }

  onReady(function () {
    const form = document.querySelector("#content-main form");
    if (!form) return;

    const dateEarned = document.getElementById("id_date_earned");
    if (!dateEarned) return;

    // Hide outside shortcuts, use native in-input calendar, and clamp to today.
    toggleShortcuts(dateEarned, false);
    setDateMode(dateEarned, true);
    const today = todayISO();
    dateEarned.max = today;

    // Add dynamic helper under the field.
    ensureHelpBelow(
      dateEarned,
      "sf-cert-date-help",
      "Choose today or a past date (future dates are not allowed)."
    );

    // Error banner initial visibility + dismiss on first erroneous focus/click.
    updateTopErrorNoteVisibility();
    (function wireFirstErrorDismiss() {
      const firstErrorList = document.querySelector("#content-main form .errorlist");
      if (!firstErrorList) return;
      const firstErrorRow = firstErrorList.closest(".form-row") || firstErrorList.closest("div");
      if (!firstErrorRow) return;
      const firstErrField = firstErrorRow.querySelector("input, select, textarea, a, button");
      if (!firstErrField) return;
      const dismiss = () => hideTopErrorNote();
      firstErrField.addEventListener("focus", dismiss, { once: true });
      firstErrorRow.addEventListener("click", dismiss, { once: true });
    })();

    // Clear errors on edit/focus (same pattern as projects).
    document
      .querySelectorAll("#content-main form input, #content-main form textarea, #content-main form select")
      .forEach((el) => {
        el.addEventListener("input", () => clearFieldErrors(el));
        el.addEventListener("change", () => clearFieldErrors(el));
        el.addEventListener("blur", () => clearFieldErrors(el));
        el.addEventListener("focus", () => {
          const row = el.closest(".form-row") || el.closest("div");
          if (row && row.querySelector(".errorlist")) hideTopErrorNote();
        });
      });

    // Decorate popup calendar + refuse future picks.
    dateEarned.addEventListener("focus", function () {
      activeDateInput = dateEarned;
      setTimeout(() => decorateAdminCalendar(dateEarned), 50);
    });
    document.addEventListener("click", function (ev) {
      const box = visibleCalendarBox();
      if (box && box.contains(ev.target)) {
        setTimeout(() => decorateAdminCalendar(dateEarned), 0);
      }
    });
    patchDateTimeShortcuts(dateEarned);

    // Polling fallback for native pickers that don't always fire events.
    let last = dateEarned.value;
    setInterval(() => {
      if (dateEarned.value !== last) {
        last = dateEarned.value;
        // Client-side guard against future date.
        if (dateEarned.value && dateEarned.value > today) dateEarned.value = "";
        clearFieldErrors(dateEarned);
      }
    }, 250);

    // Resets
    captureInitial(form);
    ["title", "issuer", "date_earned", "file_upload"].forEach((fid) => {
      if (document.getElementById("id_" + fid)) addResetLinkForField(fid, "Reset");
    });
    addResetAllButton(form);
  });
})();
