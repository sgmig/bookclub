import { bindBookRatingDeleteButtons, bindBookRatingModalButtons } from "./book_rating_list_buttons.js";

document.addEventListener("DOMContentLoaded", function () {
    bindBookRatingDeleteButtons(); // Activate remove and add book buttons on page load
    bindBookRatingModalButtons(); // Activate modal buttons on page load
});
