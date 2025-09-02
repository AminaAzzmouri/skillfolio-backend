// Admin UI behavior for Projects:
//
// - End date stays disabled until Status = "completed", then becomes enabled + required immediately.
//   Hide BOTH the native browser date picker icon (when locked) and the Django “datetimeshortcuts” widget.
// - Start date is validated server-side; we show dynamic help text based on Status.
// - Completed:   end_date.min = start_date + 1 day; end_date.max = today.
// - Planned:     start_date.min = today (no max).
// - In progress: start_date.max = today (no min).
// - Completed (UI tweak): start_date.max = today - 1 (so end=today never clashes with start).
//
// - Dynamic field visibility per Status (pure client JS).
//
// - Error UX banner always appears when there are errors; hides when you focus the first
//   erroneous field or fix any field; reappears if other errors remain.
//
// - Calendar greying/limits for Django popup calendar (if it appears for any reason).
//
// - Keep the native inside-the-input calendar for Start/End when enabled;
//   the outside “datetimeshortcuts” is always hidden for both fields.
//
// - Reset controls:
//   • Per-field “Reset” link beside each editable field.
//   • “Reset all” button in the submit row resets the entire form.
//
// - Certificate field is **link-only** on Project add/edit:
//   • Any Django related-object action icons (add/change/delete/view) rendered next to the
//     Certificate widget are removed here as a defensive client-side clamp (server-side flags
//     are already disabled in admin.py).
//
// NOTE: We still rely on model.clean() for final server-side enforcement.

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

  function addDaysISO(iso, days) {
    if (!iso) return "";
    const [Y, M, D] = iso.split("-").map((x) => parseInt(x, 10));
    const d = new Date(Y, M - 1, D);
    d.setDate(d.getDate() + days);
    return toLocalISO(d);
  }

  function getRowFor(fieldId) {
    const input = document.getElementById("id_" + fieldId);
    if (!input) return null;
    let row = input.closest(".form-row");
    if (!row) row = input.closest("div");
    return row;
  }

  function showRow(fieldId, show) {
    const row = getRowFor(fieldId);
    if (!row) return;
    if (show) {
      row.classList.remove("sf-hide");
      row.classList.remove("errors");
    } else {
      row.classList.add("sf-hide");
    }
  }

  function setLabel(fieldId, text) {
    const label = document.querySelector('label[for="id_' + fieldId + '"]');
    if (label) label.textContent = text;
  }

  function ensureHelpBelow(input, id) {
    let help = document.getElementById(id);
    if (!help) {
      help = document.createElement("div");
      help.id = id;
      help.className = "sf-note";
      input.insertAdjacentElement("afterend", help);
    }
    return help;
  }

  // ----- Error banner helpers -----
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

  // ---- Django admin “date shortcuts” helpers -----
  function shortcutsFor(input) {
    const row = input.closest(".form-row") || input.parentElement;
    if (!row) return null;
    return row.querySelector(".datetimeshortcuts");
  }
  function toggleShortcuts(input, visible) {
    const box = shortcutsFor(input);
    if (!box) return;
    box.style.display = visible ? "" : "none";
  }

  // Track which input the popup calendar belongs to.
  let activeDateInput = null;

  function visibleCalendarBox() {
    const boxes = Array.from(document.querySelectorAll(".calendarbox"));
    return boxes.find((b) => b.offsetParent !== null);
  }

  const MONTHS = { january:1,february:2,march:3,april:4,may:5,june:6,july:7,august:8,september:9,october:10,november:11,december:12 };
  function pad2(n){ return (n<10?"0":"")+n; }

  function isoFromCaptionAndDay(captionText, dayNum) {
    if (!captionText) return "";
    const parts = captionText.trim().split(/\s+/);
    const monthName = (parts[0] || "").toLowerCase();
    const year = parseInt(parts[1], 10);
    const month = MONTHS[monthName];
    if (!year || !month) return "";
    return `${year}-${pad2(month)}-${pad2(dayNum)}`;
  }

  // Decide if a given ISO date is allowed for a given input, based on status/start.
  function isAllowedForInput(input, iso, statusVal, startIso) {
    const today = todayISO();
    const yesterday = addDaysISO(today, -1);

    if (input.id === "id_start_date") {
      if (statusVal === "planned") return iso >= today;        // only today/future
      if (statusVal === "completed") return iso <= yesterday;  // completed → up to yesterday
      return iso <= today;                                      // in_progress → up to today
    }
    if (input.id === "id_end_date") {
      if (statusVal !== "completed") return false;              // should be locked anyway
      if (!iso) return false;
      if (iso > today) return false;                            // no future
      if (startIso) return iso > startIso;                      // strictly after start
      return true;
    }
    return true;
  }

  // Decorate invalid days in Django’s popup calendar.
  function decorateAdminCalendar() {
    const box = visibleCalendarBox();
    if (!box || !activeDateInput) return;

    const caption = box.querySelector("caption");
    const captionText = caption ? caption.textContent : "";
    const status = document.getElementById("id_status");
    const stVal = status ? status.value : "planned";
    const start = document.getElementById("id_start_date");
    const startIso = start ? start.value : "";

    box.querySelectorAll("td").forEach((td) => {
      td.classList.remove("sf-cal-disabled");
      const a = td.querySelector("a");
      if (a) { a.style.pointerEvents = ""; a.style.opacity = ""; a.removeAttribute("aria-disabled"); }
    });
    box.querySelectorAll("td.nonday").forEach((td) => td.classList.add("sf-cal-disabled"));

    box.querySelectorAll("td a").forEach((a) => {
      const dayNum = parseInt(a.textContent, 10);
      if (!dayNum) return;
      const iso = isoFromCaptionAndDay(captionText, dayNum);
      if (!iso) return;
      const ok = isAllowedForInput(activeDateInput, iso, stVal, startIso);
      if (!ok) {
        const td = a.closest("td");
        if (td) td.classList.add("sf-cal-disabled");
        a.style.pointerEvents = "none";
        a.style.opacity = "0.35";
        a.setAttribute("aria-disabled", "true");
      }
    });
  }

  function patchDateTimeShortcuts() {
    const D = window.DateTimeShortcuts;
    if (!D || D.__sf_patched) return;
    D.__sf_patched = true;

    const origHandle = D.handleCalendarCallback ? D.handleCalendarCallback.bind(D) : null;
       const origDismiss = D.dismissCalendar ? D.dismissCalendar.bind(D) : null;

    function afterPick(num) {
      try {
        const input = (D.calendarInputs && D.calendarInputs[num]) || activeDateInput;
        if (!input) return;
        const status = document.getElementById("id_status");
        const stVal = status ? status.value : "planned";
        const startIso = (document.getElementById("id_start_date") || {}).value || "";
        const iso = input.value || "";
        if (iso && !isAllowedForInput(input, iso, stVal, startIso)) input.value = "";
        clearFieldErrors(input);
      } catch (e) {}
      setTimeout(decorateAdminCalendar, 0);
    }

    if (origHandle) D.handleCalendarCallback = function (num) { const r = origHandle(num); afterPick(num); return r; };
    if (origDismiss) D.dismissCalendar = function (num) { const r = origDismiss(num); afterPick(num); return r; };
  }

  // Flip an input between date/text to truly remove native calendar on all browsers when locked.
  function setDateMode(el, asDate) {
    try {
      const current = el.getAttribute("type");
      const target = asDate ? "date" : "text";
      if (current !== target) el.setAttribute("type", target);
    } catch (_) {}
  }

  // ---------- RESET helpers ----------
  function captureInitial(form) {
    const elements = Array.from(form.querySelectorAll("input[id^='id_'], select[id^='id_'], textarea[id^='id_']"));
    elements.forEach((el) => {
      if (el.type === "checkbox") {
        el.dataset.sfInit = JSON.stringify({ kind: "checkbox", checked: el.checked });
      } else if (el.type === "radio") {
        el.dataset.sfInit = JSON.stringify({ kind: "radio", name: el.name, value: el.value, checked: el.checked });
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
    } else {
      el.value = init.value || "";
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }
    clearFieldErrors(el);
  }

  function clearAllErrors(form) {
    form.querySelectorAll(".errorlist").forEach((ul) => ul.remove());
    form.querySelectorAll(".errors").forEach((row) => row.classList.remove("errors"));
    hideTopErrorNote();
    setTimeout(updateTopErrorNoteVisibility, 0);
  }

  function addResetLinkForField(fieldId, label, onClick) {
    const input = document.getElementById("id_" + fieldId);
    if (!input) return;
    let anchor = document.createElement("a");
    anchor.href = "#";
    anchor.className = "sf-reset-link";
    anchor.textContent = label || "Reset";
    anchor.addEventListener("click", function (e) {
      e.preventDefault();
      onClick ? onClick(input) : restoreInitialFor(input);
      if (fieldId === "status") onStatusChange();
      else if (fieldId === "start_date") onStartChange();
      else if (fieldId === "end_date") setTimeout(decorateAdminCalendar, 0);
      input.focus();
    });
    const help = (input.nextElementSibling && input.nextElementSibling.classList.contains("sf-note")) ? input.nextElementSibling : null;
    (help || input).insertAdjacentElement("afterend", anchor);
  }

  function addResetAllButton(form) {
    const submitRow = document.querySelector("#content-main .submit-row") || form;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.id = "sf-reset-all";
    btn.className = "sf-reset-all-button";
    btn.textContent = "Reset all";
    btn.addEventListener("click", function () {
      if (!confirm("Reset the entire form back to the values from when this page loaded?")) return;
      const elements = Array.from(form.querySelectorAll("input[id^='id_'], select[id^='id_'], textarea[id^='id_']"));
      elements.forEach(restoreInitialFor);
      onStatusChange();
      clearAllErrors(form);
      setTimeout(decorateAdminCalendar, 0);
      const first = form.querySelector("input, select, textarea");
      if (first) first.focus();
    });
    submitRow.appendChild(btn);
  }

  // Defensive clamp: remove any related-object action icons next to Certificate
  function hideCertificateRelatedActions() {
    const cert = document.getElementById("id_certificate");
    if (!cert) return;
    const wrap = cert.closest(".related-widget-wrapper") || cert.parentElement;
    if (!wrap) return;
    // Buttons/links Django may render around the FK widget
    wrap.querySelectorAll(
      "a.related-widget-wrapper-link, " +         // generic class in newer Django versions
      "a.add-related, a.change-related, a.delete-related, a.view-related" // older classes
    ).forEach(a => a.remove());
  }

  onReady(function () {
    const form = document.querySelector("#content-main form");
    if (!form) return;

    const status = document.getElementById("id_status");
    const start = document.getElementById("id_start_date");
    const end = document.getElementById("id_end_date");
    if (!status || !start || !end) return;

    // Keep native pickers; hide outside shortcuts early.
    setDateMode(start, true);
    toggleShortcuts(start, false);
    toggleShortcuts(end, false);

    // Defensive: ensure Certificate widget has no add/edit/delete/view icons
    hideCertificateRelatedActions();

    updateTopErrorNoteVisibility();

    // Hide banner when focusing the first erroneous field (if any)
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

    // Clear that field’s error on any value changes (typing or picker)
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

    // Also clear errors when clicking "Today" etc. (defensive)
    [start, end].forEach((inp) => {
      const sc = shortcutsFor(inp);
      if (sc) sc.addEventListener("click", function () { setTimeout(() => clearFieldErrors(inp), 0); });
      inp.addEventListener("focus", function () { activeDateInput = inp; setTimeout(decorateAdminCalendar, 50); });
      if (sc) sc.addEventListener("mousedown", function () { activeDateInput = inp; setTimeout(decorateAdminCalendar, 50); });
    });

    // Polling fallback for native pickers that don’t fire events consistently
    let lastStart = start.value;
    let lastEnd = end.value;
    setInterval(() => {
      if (start.value !== lastStart) { lastStart = start.value; clearFieldErrors(start); }
      if (end.value !== lastEnd)     { lastEnd = end.value;     clearFieldErrors(end); }
    }, 250);

    // Dynamic help under Start/End (we suppress static help in Admin form)
    const startHelp = ensureHelpBelow(start, "sf-start-help");
    const endHelp = ensureHelpBelow(end, "sf-end-help");

    function setDisabled(el, disabled) {
      el.disabled = !!disabled;
      if (disabled) { el.readOnly = true; el.classList.add("sf-disabled"); }
      else { el.readOnly = false; el.classList.remove("sf-disabled"); }
    }

    function applyStartConstraints() {
      const today = todayISO();
      const yesterday = addDaysISO(today, -1);
      if (status.value === "planned") {
        start.min = today; start.removeAttribute("max");
      } else if (status.value === "completed") {
        start.max = yesterday; start.removeAttribute("min");
      } else {
        start.max = today; start.removeAttribute("min");
      }
    }

    function applyEndConstraints() {
      const isCompleted = status.value === "completed";
      const today = todayISO();

      if (isCompleted) {
        setDisabled(end, false);
        setDateMode(end, true);         // ensure native date UI (inside the input)
        toggleShortcuts(end, false);    // keep outside shortcuts hidden
        end.required = true;
        end.max = today;
        if (start.value) end.min = addDaysISO(start.value, 1);
        else end.removeAttribute("min");
      } else {
        end.required = false;
        end.value = "";
        setDisabled(end, true);
        setDateMode(end, false);        // remove native icon when locked
        toggleShortcuts(end, false);    // keep outside shortcuts hidden
        end.removeAttribute("min");
        end.removeAttribute("max");
      }
    }

    function setStartHelp() {
      if (status.value === "planned") {
        startHelp.textContent = "Required field: please choose current date or future date";
      } else if (status.value === "in_progress") {
        startHelp.textContent = "Required field: please choose a past date or current";
      } else {
        startHelp.textContent = "Required field: please choose a past date or current. No future dates are accepted";
      }
    }
    function setEndHelp() {
      if (status.value === "completed") {
        endHelp.textContent = "Required field: End Date cannot be the same as Start date";
      } else {
        endHelp.textContent = "Required only when a project is completed";
      }
    }

    const plannedVisible = [
      "user","title","status","start_date","end_date","work_type","duration_text",
      "primary_goal","certificate","tools_used","description","date_created",
    ];
    const inProgressExtra = ["problem_solved","skills_used","challenges_short","skills_to_improve"];
    const allFields = [
      "user","title","status","start_date","end_date","work_type","duration_text","primary_goal",
      "certificate","problem_solved","tools_used","skills_used","challenges_short","skills_to_improve",
      "description","date_created",
    ];

    function applyVisibility() {
      const st = status.value;
      let visible = plannedVisible.slice();
      if (st === "in_progress") visible = visible.concat(inProgressExtra);
      else if (st === "completed") visible = allFields.slice();
      allFields.forEach((f) => showRow(f, visible.includes(f)));

      if (st === "planned") {
        setLabel("tools_used", "Tools to be used");
        setLabel("problem_solved", "Problem solved so far");
        setLabel("skills_used", "Skills practiced so far");
        setLabel("challenges_short", "Challenges encountered so far");
        setLabel("skills_to_improve", "Skills to improve");
      } else if (st === "in_progress") {
        setLabel("tools_used", "Tools used so far");
        setLabel("problem_solved", "Problem solved so far");
        setLabel("skills_used", "Skills practiced so far");
        setLabel("challenges_short", "Challenges encountered so far");
        setLabel("skills_to_improve", "Skills to improve");
      } else {
        setLabel("tools_used", "Tools used");
        setLabel("problem_solved", "Problem solved");
        setLabel("skills_used", "Skills practiced");
        setLabel("challenges_short", "Challenges encountered");
        setLabel("skills_to_improve", "Skills to improve in the future");
      }
    }

    function onStatusChange() {
      applyStartConstraints();
      applyEndConstraints();
      setStartHelp();
      setEndHelp();
      setTimeout(decorateAdminCalendar, 0);
      applyVisibility();
    }

    function onStartChange() {
      if (status.value === "completed") {
        if (start.value) end.min = addDaysISO(start.value, 1);
        else end.removeAttribute("min");
      }
      setTimeout(decorateAdminCalendar, 0);
    }

    end.addEventListener("click", function (e) {
      if (end.disabled || end.readOnly || end.getAttribute("type") !== "date") {
        e.preventDefault(); end.blur();
      }
    });
    end.addEventListener("input", function () {
      if (end.disabled || end.readOnly || end.getAttribute("type") !== "date") end.value = "";
    });

    document.addEventListener("click", function (ev) {
      const box = visibleCalendarBox();
      if (!box) return;
      if (box.contains(ev.target)) setTimeout(decorateAdminCalendar, 0);
    });

    // ---- Capture initial values and wire per-field + all reset ----
    captureInitial(form);

    const resettable = [
      "title","status","start_date","end_date","work_type","primary_goal","certificate",
      "problem_solved","tools_used","skills_used","challenges_short","skills_to_improve","description"
    ];
    resettable.forEach((fid) => {
      if (document.getElementById("id_" + fid)) addResetLinkForField(fid, "Reset", null);
    });

    addResetAllButton(form);

    // Initial pass
    patchDateTimeShortcuts();
    onStatusChange();
    status.addEventListener("change", onStatusChange);
    start.addEventListener("change", onStartChange);
    start.addEventListener("focus", () => { activeDateInput = start; setTimeout(decorateAdminCalendar, 50); });
    end.addEventListener("focus", () => { activeDateInput = end; setTimeout(decorateAdminCalendar, 50); });
  });
})();
