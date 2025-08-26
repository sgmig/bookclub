import { getCSRFToken } from "/static/js/utils/csrf.js";
import { showBootstrapToast } from "/static/js/utils/bootstrap_toast.js";

export function bindBookRatingDeleteButtons() {
  const openModalButtons = document.querySelectorAll(".open-delete-modal-btn");
  openModalButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const modalContentsUrl = this.getAttribute(
        "data-delete-rating-modal-url"
      );

      loadDeleteConfirmationModal(modalContentsUrl);
    });
  });
}

export function bindBookRatingModalButtons() {
  const openModalButtons = document.querySelectorAll(
    ".open-book-rating-modal-btn"
  );
  openModalButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const modalContentsUrl = this.getAttribute("data-book-rating-modal-url");
      console.log("Opening book rating modal with URL:", modalContentsUrl);

      loadBookRatingModal(modalContentsUrl);
    });
  });
}

function loadDeleteConfirmationModal(modalContententsUrl) {
  const modalContent = document.getElementById("deleteBookRatingModalContent");
  const modal = new bootstrap.Modal(
    document.getElementById("deleteBookRatingModal")
  );

  fetch(modalContententsUrl)
    .then((response) => response.text())
    .then((html) => {
      modalContent.innerHTML = html;

      bindBookRatingConfirmDeleteButton();

      modal.show();
    });
}

function loadBookRatingModal(modalContententsUrl) {
  const modalContent = document.getElementById("bookRatingModalContent");
  const modal = new bootstrap.Modal(document.getElementById("bookRatingModal"));

  fetch(modalContententsUrl)
    .then((response) => response.text())
    .then((html) => {
      modalContent.innerHTML = html;

      modal.show();

      bindBookRatingSubmitButton(); // Bind the submit button after loading the modal content
    });
}

function refreshBookRatingList(bookId) {
  // Reload the ratings list by "clicking" the active tab again.
  const activeLink = document.querySelector(
    '.book-rating-link[data-book-id="' + bookId + '"]'
  );
  if (activeLink) {
    activeLink.click();
  }
}

function bindBookRatingSubmitButton() {
  console.log("Binding book rating submit button");
  const submitButton = document.getElementById("submitBookRatingButton");

  if (!submitButton) {
    console.error("Submit button not found in the book rating modal.");
    return;
  }

  submitButton.addEventListener("click", function (e) {
    e.preventDefault();
    const submitUrl = this.getAttribute("data-book-rating-api-url");
    const method = this.getAttribute("data-book-rating-api-method");

    const form = document.getElementById("bookRatingForm");
    const formData = new FormData(form);

    // Calling API. CSRF token is included in formData.
    fetch(submitUrl, {
      method: method,
      body: formData,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCSRFToken(),
      },
      mode: "same-origin",
    })
      .then((response) => {
        if (response.ok) {
          console.log("Book rating submitted successfully.");
          return response.json();
        } else {
          throw new Error(`Request failed with status ${response.status}`);
        }
      })
      .then((data) => {
        const bookId = data["book"]["id"];
        console.log("The book ID is:", bookId);
        refreshBookRatingList(bookId);
        showBootstrapToast("Rating saved successfully.");
      })
      .catch((error) => {
        console.error("Error submitting rating:", error);
        showBootstrapToast("An unexpected error occurred.", true);
      });
  });
}

function bindBookRatingConfirmDeleteButton() {
  const confirmDeleteButton = document.getElementById(
    "confirmDeleteRatingButton"
  );

  if (!confirmDeleteButton) return;

  confirmDeleteButton.addEventListener("click", () => {
    handleBookRatingDelete(confirmDeleteButton);
  });
}

function handleBookRatingDelete(button) {
  // Get attributes from the button and call the API to delete the rating.
  // Remove the relevant rows after successful deletion.

  const deleteRatingApiUrl = button.getAttribute(
    "data-delete-book-rating-api-url"
  );
  const ratingId = button.getAttribute("data-book-rating-id");

  // Set the action for the delete button

  if (!deleteRatingApiUrl || !ratingId) {
    console.error("Missing data attributes for deletion.");
    return;
  }

  fetch(deleteRatingApiUrl, {
    method: "DELETE",
    headers: {
      "X-CSRFToken": getCSRFToken(), // Include CSRF token in the headers
    },
    mode: "same-origin",
  }).then((response) => {
    if (response.ok) {
      showBootstrapToast("Rating deleted successfully.");
      console.log("Rating deleted successfully.");
      removeBookRatingRow(ratingId); // Remove the rating row from the DOM
    } else {
      showBootstrapToast("Failed to delete rating.", true);
    }
  });
}

function removeBookRatingRow(ratingId) {
  const ratingRow = document.getElementById(`book-rating-row-${ratingId}`);
  const commentRow = document.getElementById(`book-rating-comment-${ratingId}`);

  if (ratingRow) {
    ratingRow.remove();
  }

  if (commentRow) {
    commentRow.remove();
  }
}
