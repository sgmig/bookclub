import { showBootstrapToast } from "/static/js/utils/bootstrap_toast.js";

document.addEventListener("DOMContentLoaded", function () {
    const addBookForms = document.querySelectorAll(".add-book-api-form");

    addBookForms.forEach(form => {
        form.addEventListener("submit", function (event) {
            event.preventDefault(); // Prevent full page reload

            const formData = new FormData(form);

            fetch(form.action, {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest", // Optional, but useful for distinguishing AJAX requests
                },
            })
                .then(response => response.json())
                .then(data => {
                    // Handle success or show a message
                    if (data.id) {
                        showBootstrapToast("Book added to your library!");
                        // Or update your page somehow
                    } else if (data.error) {
                        showBootstrapToast(`Error: ${data.error}`, true);
                    }
                })
                .catch(error => {
                    console.error("Error submitting form:", error);
                    showBootstrapToast("Something went wrong", true);
                });
        });
    });
});