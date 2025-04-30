// club_meeting.js

// load the partial details template for the meeting details panel
function loadMeetingDetails(detailPanelUrl, detailPanelEl) {
    fetch(detailPanelUrl)
        .then(response => response.text())
        .then(html => {
            detailPanelEl.innerHTML = html;
        })
        .catch(error => console.error("Error loading meeting details:", error));
}


document.addEventListener("DOMContentLoaded", function () {
    // Get all the reading list links
    const clubMeetingLinks = document.querySelectorAll(".club-meeting-link");

    // Add event listener to each link
    clubMeetingLinks.forEach(link => {
        link.addEventListener("click", function (event) {
            event.preventDefault(); // Prevent default link action

            // Get the meeting details url from the clicked link
            const clubMeetingPartialDetailUrl = link.getAttribute("data-meeting-partial-details-url")

            // Show the club meeting panel
            const meetingDetailsPanelEl = document.getElementById("club-meeting-details-panel")
            meetingDetailsPanelEl.style.display = "block";

            // Loading meeting details template inside the panel
            loadMeetingDetails(clubMeetingPartialDetailUrl, meetingDetailsPanelEl)

        });
    });
});
