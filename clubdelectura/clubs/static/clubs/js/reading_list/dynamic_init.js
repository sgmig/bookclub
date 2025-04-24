import { bindReadingListDetailsButtons } from "./reading_list_panel_buttons.js";

function loadReadingListDetails(detailPanelUrl, detailPanelEl) {
    fetch(detailPanelUrl)
        .then(response => response.text())
        .then(html => {
            detailPanelEl.innerHTML = html;
        })
        .then(bindReadingListDetailsButtons) // Activate remove buttons after loading the details
        .catch(error => console.error("Error loading meeting details:", error));
}

document.addEventListener("DOMContentLoaded", function () {

    // Get all the reading list links
    const readingListLinks = document.querySelectorAll(".reading-list-link");

    // Add event listener to each link
    readingListLinks.forEach(link => {
        link.addEventListener("click", function (event) {
            event.preventDefault(); // Prevent default link action

            // Get the details partial template using the link.
            const readingListPartialDetailUrl = link.getAttribute("data-reading-list-partial-details-url");

            // Show the reading list items panel
            const readingListItemsPanelEl = document.getElementById("reading-list-items-panel");
            readingListItemsPanelEl.style.display = "block";

            loadReadingListDetails(readingListPartialDetailUrl, readingListItemsPanelEl)
        });
    });
});