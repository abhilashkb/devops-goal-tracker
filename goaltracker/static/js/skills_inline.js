document.addEventListener("DOMContentLoaded", function () {
  function showToast(el, msg, cls = "success") {
    const toast = document.createElement("div");
    toast.className = `inline-toast alert alert-${cls} py-1 px-2 small`;
    toast.textContent = msg;
    el.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
  }

  document.querySelectorAll("form.skill-form").forEach((form) => {
    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      const skillId = form.dataset.skillId;
      const name = form.querySelector("[name='name']").value;
      const confidence = form.querySelector("[name='confidence_level']").value;
      const statusEl = form.querySelector("[name='status']");
      const status = statusEl ? statusEl.value : "Not Started";
      const notesEl = form.querySelector("[name='notes']");
      const notes = notesEl ? notesEl.value : "";

      const payload = { name, confidence_level: confidence, status, notes };
      const submitBtn = form.querySelector("button[type='submit'], button.btn-primary") || null;
      if (submitBtn) submitBtn.disabled = true;

      try {
        const resp = await fetch(`/skills/${skillId}/update`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Accept": "application/json" },
          body: JSON.stringify(payload),
          credentials: "same-origin",
        });
        const data = await resp.json();
        if (resp.ok && data.success) {
          // update readiness display if present
          const readinessEl = form.querySelector(".text-secondary.w-100, .skill-readiness");
          if (readinessEl) readinessEl.textContent = `${data.skill.readiness}%`;
          showToast(form, "Saved", "success");
        } else {
          const err = (data && data.error) || "Save failed";
          showToast(form, err, "danger");
        }
      } catch (err) {
        showToast(form, "Network error", "danger");
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  });
});
