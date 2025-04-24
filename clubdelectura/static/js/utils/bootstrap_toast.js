export function showBootstrapToast(message, isError = false) {
    const toastEl = document.createElement("div");
    toastEl.className = "toast align-items-center border-0";
    // set color based on error or success
    if (isError) {
        toastEl.classList.add("text-bg-danger");
    } else {
        toastEl.classList.add("text-bg-success");
    }

    toastEl.setAttribute("role", "alert");
    toastEl.setAttribute("aria-live", "assertive");
    toastEl.setAttribute("aria-atomic", "true");

    const toastInner = document.createElement("div");
    toastInner.className = "d-flex";

    const toastBody = document.createElement("div");
    toastBody.className = "toast-body";
    toastBody.innerText = message;

    const closeButton = document.createElement("button");
    closeButton.className = "btn-close me-2 m-auto";
    closeButton.setAttribute("type", "button");
    closeButton.setAttribute("data-bs-dismiss", "toast");
    closeButton.setAttribute("aria-label", "Close");

    toastInner.appendChild(toastBody);
    toastInner.appendChild(closeButton);
    toastEl.appendChild(toastInner);

    // Adding to a container allows stacking messages vertically.
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container position-fixed bottom-0 end-0 p-3";
        document.body.appendChild(container);
    }

    container.appendChild(toastEl);

    // Initialize Bootstrap toast
    const bsToast = new bootstrap.Toast(toastEl, { delay: 3000 });
    bsToast.show();

    // Clean up after it hides
    toastEl.addEventListener("hidden.bs.toast", () => {
        toastEl.remove();
    });
}