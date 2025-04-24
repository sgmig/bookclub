// Jump to a specific tab when the page loads
document.addEventListener("DOMContentLoaded", function () {
    // If there's a hash in the URL, activate the corresponding tab
    let activeTab = null;
    if (window.location.hash) {
        const hash = window.location.hash;
        
        activeTab = document.querySelector((`[data-bs-target="${hash}"]`)); // Select the tab using the hash
    };
    
    if (!activeTab) {
        // If no hash, activate the first tab by default
        activeTab = document.querySelector('[data-bs-toggle="tab"]');
        }

    // Activating tab using bootstrap tab element
    if (activeTab) {
        const tab = new bootstrap.Tab(activeTab);
        tab.show();
    }
    }
)