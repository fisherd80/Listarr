/**
 * Reusable on-brand confirm modal — replaces window.confirm() for destructive actions
 * so every page shows the same styled, dark-mode-aware dialog (UI-REVIEW 15, finding 1).
 * Lazily builds and appends its DOM to document.body on first use.
 */
(function () {
  var modalEl = null;
  var titleEl, bodyEl, confirmBtn, cancelBtn;
  var pendingResolve = null;

  function buildModal() {
    modalEl = document.createElement("div");
    modalEl.id = "confirm-modal";
    modalEl.className = "fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60";
    modalEl.style.display = "none";
    modalEl.innerHTML =
      '<div class="bg-bg-panel border border-border-subtle rounded p-6 w-full max-w-sm mx-4">' +
        '<h2 id="confirm-modal-title" class="text-lg font-semibold text-text-heading mb-2"></h2>' +
        '<p id="confirm-modal-body" class="text-sm text-text-muted mb-6"></p>' +
        '<div class="flex justify-end gap-3">' +
          '<button type="button" id="confirm-modal-cancel" ' +
          'class="px-4 py-2 text-sm font-medium text-text-muted hover:text-text-base focus:outline-none">Cancel</button>' +
          '<button type="button" id="confirm-modal-confirm" ' +
          'class="px-4 py-2 text-sm font-medium text-white bg-error hover:bg-error/90 rounded focus:outline-none focus:ring-2 focus:ring-error focus:ring-offset-2">Confirm</button>' +
        "</div>" +
      "</div>";
    document.body.appendChild(modalEl);

    titleEl = modalEl.querySelector("#confirm-modal-title");
    bodyEl = modalEl.querySelector("#confirm-modal-body");
    confirmBtn = modalEl.querySelector("#confirm-modal-confirm");
    cancelBtn = modalEl.querySelector("#confirm-modal-cancel");

    cancelBtn.addEventListener("click", function () {
      resolveAndClose(false);
    });
    modalEl.addEventListener("click", function (e) {
      if (e.target === modalEl) resolveAndClose(false);
    });
    confirmBtn.addEventListener("click", function () {
      resolveAndClose(true);
    });
  }

  function resolveAndClose(result) {
    if (modalEl) modalEl.style.display = "none";
    if (pendingResolve) {
      var resolve = pendingResolve;
      pendingResolve = null;
      resolve(result);
    }
  }

  /**
   * Show the on-brand confirm modal.
   * @param {{title: string, body: string, confirmLabel?: string, confirmClass?: string}} options
   * @returns {Promise<boolean>} resolves true on confirm, false on cancel/backdrop click.
   */
  window.showConfirmModal = function (options) {
    options = options || {};
    if (!modalEl) buildModal();

    titleEl.textContent = options.title || "Are you sure?";
    bodyEl.textContent = options.body || "";
    confirmBtn.textContent = options.confirmLabel || "Confirm";
    confirmBtn.className =
      "px-4 py-2 text-sm font-medium text-white rounded focus:outline-none focus:ring-2 focus:ring-offset-2 " +
      (options.confirmClass || "bg-error hover:bg-error/90 focus:ring-error");

    modalEl.style.display = "flex";

    return new Promise(function (resolve) {
      pendingResolve = resolve;
    });
  };
})();
