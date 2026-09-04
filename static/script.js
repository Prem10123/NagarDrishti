(function () {
    const fileInput = document.getElementById("imageUpload");
    const categorySelect = document.getElementById("categoryId");
    const statusText = document.getElementById("aiStatus");
    const gpsBtn = document.getElementById("gpsBtn");
    if (!fileInput || !categorySelect) return;

    let aiSuggestedId = null;

    fileInput.addEventListener("change", autoDetectCategory);
    categorySelect.addEventListener("change", checkOverride);
    if (gpsBtn) gpsBtn.addEventListener("click", getLocation);

    async function autoDetectCategory() {
        if (!fileInput.files.length) return;
        statusText.className = "form-text ai-thinking";
        statusText.innerText = "AI is analyzing image...";

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);

        try {
            const response = await fetch("/detect-category", { method: "POST", body: formData });
            const result = await response.json();
            if (result.suggested_id) {
                categorySelect.value = String(result.suggested_id);
                aiSuggestedId = String(result.suggested_id);
                statusText.className = "form-text ai-success";
                statusText.innerText = "AI detected: " + result.category_name;
                hideForce();
            } else {
                aiSuggestedId = null;
                statusText.className = "form-text ai-warning";
                statusText.innerText = "AI could not detect the issue. Please select a category.";
            }
        } catch (err) {
            statusText.className = "form-text ai-error";
            statusText.innerText = "AI service unavailable. Select a category manually.";
        }
    }

    function hideForce() {
        const box = document.getElementById("forceOption");
        const check = document.getElementById("forceCheck");
        if (box) box.classList.add("d-none");
        if (check) check.checked = false;
    }

    function checkOverride() {
        const box = document.getElementById("forceOption");
        const check = document.getElementById("forceCheck");
        if (!box) return;
        if (aiSuggestedId && categorySelect.value && categorySelect.value !== aiSuggestedId) {
            box.classList.remove("d-none");
            if (check) check.checked = false;
        } else {
            hideForce();
        }
    }

    function getLocation() {
        const status = document.getElementById("geo-status");
        if (!navigator.geolocation) {
            status.innerText = "Geolocation is not supported in this browser.";
            return;
        }
        status.className = "form-text";
        status.innerText = "Locating...";
        navigator.geolocation.getCurrentPosition(showPosition, showError, {
            enableHighAccuracy: true,
            timeout: 15000,
        });
    }

    async function showPosition(position) {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        document.getElementById("latitude").value = lat;
        document.getElementById("longitude").value = lon;
        const status = document.getElementById("geo-status");
        const address = document.getElementById("address");
        try {
            const response = await fetch("/api/reverse-geocode?lat=" + lat + "&lon=" + lon);
            const data = await response.json();
            if (data.address) {
                address.value = data.address;
                status.className = "form-text text-success";
                status.innerText = "Location locked.";
            } else {
                address.value = lat.toFixed(5) + ", " + lon.toFixed(5);
                status.innerText = "GPS saved. Add a street address if you can.";
            }
        } catch (err) {
            address.value = lat.toFixed(5) + ", " + lon.toFixed(5);
            status.innerText = "GPS saved. Add a street address if you can.";
        }
    }

    function showError() {
        const status = document.getElementById("geo-status");
        status.className = "form-text text-danger";
        status.innerText = "Could not read GPS. Type the address instead.";
    }
})();
