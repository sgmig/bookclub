// book_rating.js

// load the partial details template for the book-rating details panel
function loadBookRatingDetails(detailPanelUrl, detailPanelEl) {
    fetch(detailPanelUrl)
        .then(response => response.text())
        .then(html => {
            detailPanelEl.innerHTML = html;
        })
        .catch(error => console.error("Error loading book-rating details:", error));
}


document.addEventListener("DOMContentLoaded", function () {
    // Get all the reading list links
    const bookRatingLinks = document.querySelectorAll(".book-rating-link");

    // Add event listener to each link
    bookRatingLinks.forEach(link => {
        link.addEventListener("click", function (event) {
            event.preventDefault(); // Prevent default link action

            // Get the book-rating details url from the clicked link
            const bookRatingPartialDetailUrl = link.getAttribute("data-book-rating-partial-details-url")

            // Show the club book-rating panel
            const bookRatingDetailsPanelEl = document.getElementById("book-rating-details-panel")
            bookRatingDetailsPanelEl.style.display = "block";

            // Loading book-rating details template inside the panel
            console.log(bookRatingPartialDetailUrl)
            loadBookRatingDetails(bookRatingPartialDetailUrl, bookRatingDetailsPanelEl)

        });
    });
});
