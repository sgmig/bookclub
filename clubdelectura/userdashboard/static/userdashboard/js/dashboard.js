// dashboard.js
import { bindBookRatingModalButtons } from "/static/books/js/book_rating_list/book_rating_list_buttons.js";

function loadPanel(url, panelEl, afterLoad) {
    fetch(url)
        .then((response) => response.text())
        .then((html) => {
            panelEl.innerHTML = html;
            panelEl.style.display = "block";
            if (afterLoad) afterLoad();
        })
        .catch((error) => console.error("Error loading panel:", error));
}

function bindClubPreviewLinks() {
    const panelEl = document.getElementById("club-preview-panel");
    document.querySelectorAll(".club-preview-link").forEach((link) => {
        link.addEventListener("click", function (event) {
            event.preventDefault();
            loadPanel(this.getAttribute("data-club-preview-url"), panelEl);
        });
    });
}

function bindRatingPreviewLinks() {
    const panelEl = document.getElementById("rating-preview-panel");
    document.querySelectorAll(".rating-preview-link").forEach((link) => {
        link.addEventListener("click", function (event) {
            event.preventDefault();
            // bindBookRatingModalButtons re-wires the Edit button's modal
            // trigger every time the panel is reloaded.
            loadPanel(
                this.getAttribute("data-rating-preview-url"),
                panelEl,
                bindBookRatingModalButtons
            );
        });
    });
}

document.addEventListener("DOMContentLoaded", function () {
    bindClubPreviewLinks();
    bindRatingPreviewLinks();

    // Jump to a specific tab when the page loads, same pattern as
    // clubs/static/clubs/js/club_detail.js.
    let activeTab = null;
    if (window.location.hash) {
        activeTab = document.querySelector(
            `[data-bs-target="${window.location.hash}"]`
        );
    }
    if (!activeTab) {
        activeTab = document.querySelector('[data-bs-toggle="tab"]');
    }
    if (activeTab) {
        new bootstrap.Tab(activeTab).show();
    }
});
