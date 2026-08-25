// location_create_modal.js
import { getCSRFToken } from "/static/js/utils/csrf.js";
import { showBootstrapToast } from "/static/js/utils/bootstrap_toast.js";

function loadLocationCreateModal(modalContentUrl) {
  const modalContent = document.getElementById("locationCreateModalContent");
  const modal = new bootstrap.Modal(
    document.getElementById("locationCreateModal")
  );

  fetch(modalContentUrl)
    .then((response) => response.text())
    .then((html) => {
      modalContent.innerHTML = html;

      modal.show();

      bindLocationCreateSubmitButton(); // Bind the submit button after loading the modal content
    });
}

function addLocationToDropdown(location) {
  const locationDropdown = document.getElementById("location-dropdown");
  if (!locationDropdown) return;

  const option = new Option(location.name, location.id, true, true);
  locationDropdown.appendChild(option);
}

function bindLocationCreateSubmitButton() {
  const submitButton = document.getElementById("submitLocationCreateButton");

  if (!submitButton) {
    console.error("Submit button not found in the location create modal.");
    return;
  }

  submitButton.addEventListener("click", function (e) {
    e.preventDefault();
    const submitUrl = this.getAttribute("data-location-create-api-url");

    const form = document.getElementById("locationCreateForm");
    const formData = new FormData(form);

    // Calling API. CSRF token is included in formData.
    fetch(submitUrl, {
      method: "POST",
      body: formData,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCSRFToken(),
      },
      mode: "same-origin",
    })
      .then((response) => {
        if (response.ok) {
          return response.json();
        } else {
          throw new Error(`Request failed with status ${response.status}`);
        }
      })
      .then((data) => {
        addLocationToDropdown(data);
        showBootstrapToast("Location added successfully.");
      })
      .catch((error) => {
        console.error("Error submitting location:", error);
        showBootstrapToast("An unexpected error occurred.", true);
      });
  });
}

export function bindLocationCreateModalButtons() {
  const openModalButtons = document.querySelectorAll(
    ".open-location-create-modal-btn"
  );
  openModalButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const modalContentUrl = this.getAttribute(
        "data-location-create-modal-url"
      );
      loadLocationCreateModal(modalContentUrl);
    });
  });
}

document.addEventListener("DOMContentLoaded", function () {
  bindLocationCreateModalButtons();
});
