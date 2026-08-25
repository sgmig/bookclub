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
    const locationApiUrl = this.getAttribute("data-location-create-api-url");
    const clubLocationApiUrl = this.getAttribute(
      "data-club-location-create-api-url"
    );

    const form = document.getElementById("locationCreateForm");
    const clubId = form.elements["club"].value;

    // The Location itself and its link to the club are two separate
    // resources (Location lives in the locations app, ClubLocation in
    // clubs), so this is two calls: create the Location, then link it.
    const formData = new FormData(form);
    formData.delete("club");

    createLocation(locationApiUrl, formData)
      .then((location) =>
        linkLocationToClub(clubLocationApiUrl, clubId, location).then(
          () => location
        )
      )
      .then((location) => {
        addLocationToDropdown(location);
        showBootstrapToast("Location added successfully.");
      })
      .catch((error) => {
        console.error("Error adding location:", error);
        showBootstrapToast("An unexpected error occurred.", true);
      });
  });
}

function createLocation(locationApiUrl, formData) {
  // CSRF token is included in formData.
  return fetch(locationApiUrl, {
    method: "POST",
    body: formData,
    headers: {
      "X-Requested-With": "XMLHttpRequest",
      "X-CSRFToken": getCSRFToken(),
    },
    mode: "same-origin",
  }).then((response) => {
    if (!response.ok) {
      throw new Error(`Location creation failed with status ${response.status}`);
    }
    return response.json();
  });
}

function linkLocationToClub(clubLocationApiUrl, clubId, location) {
  return fetch(clubLocationApiUrl, {
    method: "POST",
    body: JSON.stringify({ club: clubId, location: location.id }),
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest",
      "X-CSRFToken": getCSRFToken(),
    },
    mode: "same-origin",
  }).then((response) => {
    if (!response.ok) {
      throw new Error(`Linking location to club failed with status ${response.status}`);
    }
    return response.json();
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
