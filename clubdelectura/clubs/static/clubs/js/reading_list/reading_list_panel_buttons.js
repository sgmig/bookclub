import { getCSRFToken } from "/static/js/utils/csrf.js";
import { showBootstrapToast } from "/static/js/utils/bootstrap_toast.js";

export function bindReadingListDetailsButtons() {
    bindBookSearchButton();
    bindRemoveButtons(); // Activate remove buttons on page load
};

function bindSearchFormSubmit() {
    const form = document.querySelector("#bookSearchModal form");
    if (!form) return;

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        const url = this.action;
        const params = new URLSearchParams(new FormData(this));

        fetch(url + "?" + params.toString())
            .then(response => response.text())
            .then(html => {
                document.getElementById("bookSearchModalContent").innerHTML = html;
                // Re-bind the form after replacing modal content
                bindSearchFormSubmit();
                bindAddBookButtons(); // Re-bind add book buttons
            });
    });
};

function bindBookSearchButton() {
    document.getElementById("openBookSearch").addEventListener("click", function () {
        const url = this.dataset.searchUrl;

        fetch(url)
            .then(response => response.text())
            .then(html => {
                document.getElementById("bookSearchModalContent").innerHTML = html;
                const modal = new bootstrap.Modal(document.getElementById("bookSearchModal"));
                modal.show();

                // Bind form submit after content is loaded
                bindSearchFormSubmit();
            });
    });
}


function addOrRetrieveBook(bookData, url) {
    // Call endpoint to add or retrieve book from search API results.
    // CSRF should be included in the bookData, which is gathered from the form. 
    return fetch(url, {
        method: "POST",
        body: bookData,
        headers: {
            "X-Requested-With": "XMLHttpRequest",
        },
        mode: "same-origin",
    }).then(response => {
        if (response.ok) {
            return response.json();
        } else {
            throw new Error(`Request failed with status ${response.status}`);
        }
    });
}

function addReadingListItem(bookId, readingListId, url) {
    // Call endpoint to add book to reading list.

    return fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCSRFToken(),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            book: bookId,
            reading_list: readingListId,
        }),
        mode: "same-origin",
    }).then(response => {
        if (response.ok) {
            return response.json();
        } else {
            throw new Error(`Request failed with status ${response.status}`);
        };
    });
};

function loadNewReadingListItem(itemId) {
    const ItemRowUrl = document.querySelector("#bookSearchModal").getAttribute("data-reading-list-item-row-url").replace("/0/", "/" + itemId + "/");

    const detailTableBodyEl = document.querySelector("#reading-list-items");

    fetch(ItemRowUrl)
        .then(response => response.text())
        .then(html => {
            const newRowEl = document.createElement("template")
            newRowEl.innerHTML = html.trim();
            detailTableBodyEl.appendChild(newRowEl.content.firstElementChild);
            bindRemoveButtons();
        })
        .catch(error => console.error("Error loading meeting details:", error));
};

function handleAddBookClick(event, readingListId, addReadingListItemUrl) {
    event.preventDefault();

    // Get the infromation from the clicked button.
    const button = event.currentTarget;
    // Get the hidden form that contains the book data.
    const bookForm = button.closest("form");
    const addBookUrl = bookForm.action;
    const formData = new FormData(bookForm);

    addOrRetrieveBook(formData, addBookUrl)
        .then(data => {
            return addReadingListItem(data.id, readingListId, addReadingListItemUrl);
        })
        .then(data => {
            loadNewReadingListItem(data.id);
            showBootstrapToast(`${data.book.title} added to your list!`);
        })
        .catch(error => {
            console.error("Error adding book to reading list:", error);
            showBootstrapToast("Something went wrong", true);
        });
};

function bindAddBookButtons() {
    // Get the modal and its reading-list attributes.
    const bookSearchModal = document.querySelector("#bookSearchModal");
    const addReadingListItemUrl = bookSearchModal.getAttribute("data-add-reading-list-item-url");
    const readingListId = bookSearchModal.getAttribute("data-reading-list-id");

    // Find all add book buttons from the search results.
    const addBookButtons = document.querySelectorAll(".book-result-card #add-book-button");

    addBookButtons.forEach(button => {
        button.addEventListener("click", (event) => { handleAddBookClick(event, readingListId, addReadingListItemUrl) });
    });
};

// TODO: catch errors deleting items.
function deleteReadingListItem(element) {
    // Construct the URL for the DELETE request
    const url = element.getAttribute("data-delete-item-url");

    // Create a new Request object with the DELETE method
    const request = new Request(url, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': getCSRFToken() },
        mode: 'same-origin' // Do not send CSRF token to another domain.
    });

    fetch(request).then(function (response) {
        if (response.ok) {
            // Handle successful deletion (e.g., remove item from UI)
            const itemElement = element.closest('.reading-list-item');
            itemElement.remove(); // Remove the item element from the DOM
        } else {
            console.error("Error removing item:", response.statusText);
        }
    });
}

function bindRemoveButtons() {
    // Get all the remove buttons
    const removeButtons = document.querySelectorAll(".remove-reading-list-item-button");

    // Add event listener to each button
    removeButtons.forEach(button => {
        button.addEventListener("click", function (event) {
            event.preventDefault(); // Prevent default button action

            // Call the delete function with the button element
            deleteReadingListItem(button);
        });
    });

}