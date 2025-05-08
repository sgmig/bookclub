import { getCSRFToken } from "/static/js/utils/csrf.js";
import { showBootstrapToast } from "/static/js/utils/bootstrap_toast.js";

export function bindBookRatingDeleteButtons() {
    const openModalButtons = document.querySelectorAll(".open-delete-modal-btn");
    openModalButtons.forEach(button => {
        button.addEventListener("click", function () {
            const modalContentsUrl = this.getAttribute("data-delete-rating-modal-url");
    
            loadDeleteConfirmationModal(modalContentsUrl);
            });
});
}

function loadDeleteConfirmationModal(modalContententsUrl) {
    const modalContent = document.getElementById("deleteBookRatingModalContent");
    const modal = new bootstrap.Modal(document.getElementById("deleteBookRatingModal"));

    fetch(modalContententsUrl)
        .then(response => response.text())
        .then(html => {
            modalContent.innerHTML = html;

            bindBookRatingConfirmDeleteButton();

            modal.show();
    });
}


function bindBookRatingConfirmDeleteButton() {
    const confirmDeleteButton = document.getElementById("confirmDeleteRatingButton");

    if (!confirmDeleteButton) return;

    confirmDeleteButton.addEventListener("click", () => {
        handleBookRatingDelete(confirmDeleteButton);
    });
}

function handleBookRatingDelete(button) {
    // Get attributes from the button and call the API to delete the rating.
    // Remove the relevant rows after successful deletion.
    
    const deleteRatingApiUrl = button.getAttribute("data-delete-book-rating-api-url");
    const ratingId = button.getAttribute("data-book-rating-id");
        
    // Set the action for the delete button

    if (!deleteRatingApiUrl || !ratingId) {
        console.error("Missing data attributes for deletion.");
        return;
    }

    fetch(deleteRatingApiUrl, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCSRFToken(), // Include CSRF token in the headers
        },
        mode: "same-origin",
    }).then(response => {
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





    