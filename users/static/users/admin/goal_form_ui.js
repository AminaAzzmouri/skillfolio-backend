// Goal form admin UI polish:
// - Inside-input calendar for Deadline (hide Django datetimeshortcuts).
// - Deadline min=today; past days greyed/blocked in popup calendar.
// - Per-field “Reset” links + “Reset all”.
// - Top error banner: shows if any errors; hides when focusing the first error
//   or after fixing a field; reappears if other errors remain.
// - Small dynamic helper under Deadline.
//
// Notes:
// We keep server-side enforcement (Goal.clean): deadline cannot be in the past,
// target_projects must be positive, etc.

(function () {
  function onReady(fn){ if(document.readyState!=="loading") return fn(); document.addEventListener("DOMContentLoaded", fn); }
  function toLocalISO(d){ const z=new Date(d.getTime()-d.getTimezoneOffset()*60000); return z.toISOString().slice(0,10); }
  function todayISO(){ return toLocalISO(new Date()); }

  // -------- generic helpers
  function ensureHelpBelow(input,id){
    let help=document.getElementById(id);
    if(!help){
      help=document.createElement("div");
      help.id=id;
      help.className="sf-note";
      input.insertAdjacentElement("afterend", help);
    }
    return help;
  }
  function countAllErrors(){ return document.querySelectorAll("#content-main form .errorlist li").length; }
  function ensureTopErrorNote(){
    let top=document.querySelector("#content-main .errornote");
    if(!top){
      top=document.createElement("p");
      top.className="errornote";
      const form=document.querySelector("#content-main form");
      if(form && form.parentElement) form.parentElement.insertBefore(top, form);
    }
    return top;
  }
  function updateTopErrorNoteVisibility(){
    const n=countAllErrors();
    const top=ensureTopErrorNote();
    if(n>0){
      top.textContent = n===1 ? "Please correct the error below." : "Please correct the errors below.";
      top.style.display="";
    } else {
      top.style.display="none";
    }
  }
  function hideTopErrorNote(){
    const top=document.querySelector("#content-main .errornote");
    if(top) top.style.display="none";
  }
  function clearFieldErrors(el){
    const row=el.closest(".form-row") || el.closest("div");
    if(!row) return;
    const had=row.querySelector("ul.errorlist");
    row.querySelectorAll("ul.errorlist").forEach(ul=>ul.remove());
    row.classList.remove("errors");
    if(had) hideTopErrorNote();
    setTimeout(updateTopErrorNoteVisibility,0);
  }

  // ---- Django admin date popup helpers
  function shortcutsFor(input){
    const row=input.closest(".form-row") || input.parentElement;
    if(!row) return null;
    return row.querySelector(".datetimeshortcuts");
  }
  function toggleShortcuts(input, visible){
    const box=shortcutsFor(input);
    if(!box) return;
    box.style.display = visible ? "" : "none";
  }
  function setDateMode(el, asDate){
    try{
      const cur=el.getAttribute("type");
      const tgt=asDate ? "date" : "text";
      if(cur!==tgt) el.setAttribute("type", tgt);
    }catch(_){}
  }
  let activeDateInput=null;
  function visibleCalendarBox(){
    const boxes=Array.from(document.querySelectorAll(".calendarbox"));
    return boxes.find(b=>b.offsetParent!==null);
  }
  const MONTHS={january:1,february:2,march:3,april:4,may:5,june:6,july:7,august:8,september:9,october:10,november:11,december:12};
  function pad2(n){ return (n<10?"0":"")+n; }
  function isoFromCaptionAndDay(captionText, dayNum){
    if(!captionText) return "";
    const parts=captionText.trim().split(/\s+/); // "April 2025"
    const monthName=(parts[0]||"").toLowerCase();
    const year=parseInt(parts[1],10);
    const month=MONTHS[monthName];
    if(!year || !month) return "";
    return `${year}-${pad2(month)}-${pad2(dayNum)}`;
  }

  function decorateAdminCalendar(){
    const box=visibleCalendarBox();
    if(!box || !activeDateInput) return;
    if(activeDateInput.id!=="id_deadline") return;

    const caption=box.querySelector("caption");
    const captionText=caption ? caption.textContent : "";
    const today=todayISO();

    // reset
    box.querySelectorAll("td").forEach(td=>{
      td.classList.remove("sf-cal-disabled");
      const a=td.querySelector("a");
      if(a){ a.style.pointerEvents=""; a.style.opacity=""; a.removeAttribute("aria-disabled"); }
    });
    box.querySelectorAll("td.nonday").forEach(td=>td.classList.add("sf-cal-disabled"));

    // block past days
    box.querySelectorAll("td a").forEach(a=>{
      const dayNum=parseInt(a.textContent,10);
      if(!dayNum) return;
      const iso=isoFromCaptionAndDay(captionText, dayNum);
      if(!iso) return;
      const ok = iso >= today; // deadline cannot be in the past
      if(!ok){
        const td=a.closest("td");
        if(td) td.classList.add("sf-cal-disabled");
        a.style.pointerEvents="none";
        a.style.opacity="0.35";
        a.setAttribute("aria-disabled","true");
      }
    });
  }

  function patchDateTimeShortcuts(){
    const D=window.DateTimeShortcuts;
    if(!D || D.__sf_goal_patched) return;
    D.__sf_goal_patched=true;

    const origHandle = D.handleCalendarCallback ? D.handleCalendarCallback.bind(D) : null;
    const origDismiss = D.dismissCalendar ? D.dismissCalendar.bind(D) : null;

    function afterPick(num){
      try{
        const input=(D.calendarInputs && D.calendarInputs[num]) || activeDateInput;
        if(!input) return;
        // enforce min=today (reject invalid picks)
        if(input.id==="id_deadline"){
          const iso=input.value || "";
          if(iso && iso < todayISO()) input.value="";
          clearFieldErrors(input);
        }
      }catch(e){}
      setTimeout(decorateAdminCalendar,0);
    }

    if(origHandle){
      D.handleCalendarCallback=function(num){ const r=origHandle(num); afterPick(num); return r; };
    }
    if(origDismiss){
      D.dismissCalendar=function(num){ const r=origDismiss(num); afterPick(num); return r; };
    }
  }

  // ----- RESET helpers
  function captureInitial(form){
    const elements=Array.from(form.querySelectorAll("input[id^='id_'], select[id^='id_'], textarea[id^='id_']"));
    elements.forEach(el=>{
      if(el.type==="checkbox"){
        el.dataset.sfInit=JSON.stringify({kind:"checkbox",checked:el.checked});
      }else if(el.type==="radio"){
        el.dataset.sfInit=JSON.stringify({kind:"radio",name:el.name,value:el.value,checked:el.checked});
      }else if(el.multiple){
        const vals=Array.from(el.options).filter(o=>o.selected).map(o=>o.value);
        el.dataset.sfInit=JSON.stringify({kind:"multi",values:vals});
      }else{
        el.dataset.sfInit=JSON.stringify({kind:"value",value:el.value});
      }
    });
  }
  function restoreInitialFor(el){
    if(!el || !el.dataset.sfInit) return;
    const init=JSON.parse(el.dataset.sfInit);
    if(init.kind==="checkbox"){
      el.checked=!!init.checked;
      el.dispatchEvent(new Event("change",{bubbles:true}));
    }else if(init.kind==="radio"){
      const group=document.querySelectorAll(`input[type="radio"][name="${CSS.escape(el.name)}"]`);
      group.forEach(r=>{ r.checked=false; });
      const initiallyChecked=Array.from(group).find(r=>{ try{return JSON.parse(r.dataset.sfInit||"{}").checked;}catch(_){return false;} });
      if(initiallyChecked) initiallyChecked.checked=true;
      (initiallyChecked||el).dispatchEvent(new Event("change",{bubbles:true}));
    }else if(init.kind==="multi"){
      Array.from(el.options).forEach(o=>{ o.selected = init.values.includes(o.value); });
      el.dispatchEvent(new Event("change",{bubbles:true}));
    }else{
      el.value=init.value || "";
      el.dispatchEvent(new Event("input",{bubbles:true}));
      el.dispatchEvent(new Event("change",{bubbles:true}));
    }
    clearFieldErrors(el);
  }
  function addResetLinkForField(fieldId,label){
    const input=document.getElementById("id_"+fieldId);
    if(!input) return;
    let a=document.createElement("a");
    a.href="#";
    a.className="sf-reset-link";
    a.textContent=label || "Reset";
    a.addEventListener("click",function(e){
      e.preventDefault();
      restoreInitialFor(input);
      input.focus();
    });
    const next=input.nextElementSibling;
    const help=(next && next.classList && next.classList.contains("sf-note")) ? next : null;
    (help||input).insertAdjacentElement("afterend", a);
  }
  function addResetAllButton(form){
    const submitRow=document.querySelector("#content-main .submit-row") || form;
    const btn=document.createElement("button");
    btn.type="button";
    btn.id="sf-reset-all";
    btn.className="sf-reset-all-button";
    btn.textContent="Reset all";
    btn.addEventListener("click",function(){
      if(!confirm("Reset the entire form back to the values from when this page loaded?")) return;
      const elements=Array.from(form.querySelectorAll("input[id^='id_'], select[id^='id_'], textarea[id^='id_']"));
      elements.forEach(restoreInitialFor);
      hideTopErrorNote();
      setTimeout(updateTopErrorNoteVisibility,0);
      const first=form.querySelector("input, select, textarea");
      if(first) first.focus();
    });
    submitRow.appendChild(btn);
  }

  onReady(function(){
    const form=document.querySelector("#content-main form");
    if(!form) return;

    // Fields we care about
    const deadline=document.getElementById("id_deadline");
    const target=document.getElementById("id_target_projects");
    const total=document.getElementById("id_total_steps");
    const done=document.getElementById("id_completed_steps");
    const title=document.getElementById("id_title");

    // Inside-input calendar + hide outside shortcuts
    if(deadline){
      setDateMode(deadline, true);
      deadline.min=todayISO();
      toggleShortcuts(deadline, false);

      // decorate calendar while open / navigating months
      deadline.addEventListener("focus", function(){ activeDateInput=deadline; setTimeout(decorateAdminCalendar,50); });
      document.addEventListener("click", function(ev){
        const box=visibleCalendarBox();
        if(!box) return;
        if(box.contains(ev.target)) setTimeout(decorateAdminCalendar,0);
      });
    }

    // Target projects: enforce HTML min=1, step=1 (defense in depth)
    if(target){
      target.setAttribute("min","1");
      target.setAttribute("step","1");
      // If it's a text input for some reason, keep it numeric-ish
      target.addEventListener("input", function(){
        const v=target.value;
        if(v && Number(v) < 1) target.value = "1";
      });
    }

    // Dynamic helper under Deadline
    if(deadline){
      const help=ensureHelpBelow(deadline, "sf-deadline-help");
      help.textContent="Choose today or a future date.";
    }

    // Error banner on load
    updateTopErrorNoteVisibility();
    (function wireFirstErrorDismiss(){
      const firstErrorList=document.querySelector("#content-main form .errorlist");
      if(!firstErrorList) return;
      const firstRow=firstErrorList.closest(".form-row") || firstErrorList.closest("div");
      if(!firstRow) return;
      const firstField=firstRow.querySelector("input, select, textarea, a, button");
      if(!firstField) return;
      const dismiss=()=>hideTopErrorNote();
      firstField.addEventListener("focus", dismiss, {once:true});
      firstRow.addEventListener("click", dismiss, {once:true});
    })();

    // Clear row errors on input/change/blur; hide banner when focusing an errored field
    form.querySelectorAll("input, select, textarea").forEach((el)=>{
      el.addEventListener("input", ()=>clearFieldErrors(el));
      el.addEventListener("change", ()=>clearFieldErrors(el));
      el.addEventListener("blur", ()=>clearFieldErrors(el));
      el.addEventListener("focus", ()=>{
        const row=el.closest(".form-row") || el.closest("div");
        if(row && row.querySelector(".errorlist")) hideTopErrorNote();
      });
    });

    // Capture initial values and add per-field reset links
    captureInitial(form);
    ["title","target_projects","deadline","total_steps","completed_steps"].forEach(fid=>{
      if(document.getElementById("id_"+fid)) addResetLinkForField(fid, "Reset");
    });
    addResetAllButton(form);

    // Patch Django date popup after the page is ready
    patchDateTimeShortcuts();
  });
})();
