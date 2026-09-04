(function () {
    document.querySelectorAll(".toast-close").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var toast = btn.closest(".toast");
            if (toast) toast.remove();
        });
    });
    var toast = document.querySelector(".toast");
    if (toast) {
        setTimeout(function () {
            toast.style.opacity = "0";
            toast.style.transform = "translate(-50%, -8px)";
            toast.style.transition = "opacity 280ms ease, transform 280ms ease";
            setTimeout(function () { toast.remove(); }, 300);
        }, 4200);
    }

    document.querySelectorAll("[data-tabs]").forEach(function (root) {
        var tabs = root.querySelectorAll(".tab");
        tabs.forEach(function (tab) {
            tab.addEventListener("click", function () {
                tabs.forEach(function (t) {
                    t.classList.toggle("is-active", t === tab);
                    t.setAttribute("aria-selected", t === tab ? "true" : "false");
                });
                root.querySelectorAll(".tab-panel").forEach(function (panel) {
                    var on = panel.id === "panel-" + tab.getAttribute("data-tab");
                    panel.classList.toggle("is-active", on);
                    panel.hidden = !on;
                });
            });
        });
    });

    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("submit", function () {
            var btn = form.querySelector("button[type=submit]");
            if (!btn || btn.dataset.busy) return;
            btn.dataset.busy = "1";
            btn.style.opacity = "0.72";
            btn.textContent = btn.id === "submitReport" ? "Submitting…" : "Please wait…";
        });
    });

    var fileInput = document.getElementById("imageUpload");
    var categorySelect = document.getElementById("categoryId");
    var statusText = document.getElementById("aiStatus");
    var gpsBtn = document.getElementById("gpsBtn");
    var dropzone = document.getElementById("dropzone");
    var preview = document.getElementById("photoPreview");
    var dropUi = document.getElementById("dropzoneUi");
    if (!fileInput || !categorySelect) return;

    var aiSuggestedId = null;

    fileInput.addEventListener("change", function () {
        showPreview();
        autoDetectCategory();
    });
    categorySelect.addEventListener("change", checkOverride);
    if (gpsBtn) gpsBtn.addEventListener("click", getLocation);

    ["dragenter", "dragover"].forEach(function (evt) {
        dropzone.addEventListener(evt, function (e) {
            e.preventDefault();
            dropzone.classList.add("is-hover");
        });
    });
    ["dragleave", "drop"].forEach(function (evt) {
        dropzone.addEventListener(evt, function (e) {
            e.preventDefault();
            dropzone.classList.remove("is-hover");
        });
    });
    dropzone.addEventListener("drop", function (e) {
        if (!e.dataTransfer.files.length) return;
        fileInput.files = e.dataTransfer.files;
        showPreview();
        autoDetectCategory();
    });

    function showPreview() {
        if (!fileInput.files.length || !preview) return;
        var url = URL.createObjectURL(fileInput.files[0]);
        preview.src = url;
        preview.classList.remove("is-hidden");
        if (dropUi) dropUi.classList.add("is-hidden");
        dropzone.classList.add("has-photo");
    }

    async function autoDetectCategory() {
        if (!fileInput.files.length) return;
        statusText.className = "hint ai-thinking";
        statusText.innerText = "AI is reading the photo…";

        var formData = new FormData();
        formData.append("file", fileInput.files[0]);

        try {
            var csrf = document.querySelector('meta[name="csrf-token"]');
            var headers = {};
            if (csrf && csrf.content) headers["X-CSRF-Token"] = csrf.content;
            var response = await fetch("/detect-category", {
                method: "POST",
                body: formData,
                headers: headers,
                credentials: "same-origin"
            });
            var result = await response.json();
            if (result.suggested_id) {
                categorySelect.value = String(result.suggested_id);
                aiSuggestedId = String(result.suggested_id);
                statusText.className = "hint ai-success";
                statusText.innerText = "AI detected: " + result.category_name;
                hideForce();
            } else {
                aiSuggestedId = null;
                statusText.className = "hint ai-warning";
                statusText.innerText = "AI could not detect the issue. Please select a category.";
            }
        } catch (err) {
            statusText.className = "hint ai-error";
            statusText.innerText = "AI service unavailable. Select a category manually.";
        }
    }

    function hideForce() {
        var box = document.getElementById("forceOption");
        var check = document.getElementById("forceCheck");
        if (box) box.classList.add("is-hidden");
        if (check) check.checked = false;
    }

    function checkOverride() {
        var box = document.getElementById("forceOption");
        var check = document.getElementById("forceCheck");
        if (!box) return;
        if (aiSuggestedId && categorySelect.value && categorySelect.value !== aiSuggestedId) {
            box.classList.remove("is-hidden");
            if (check) check.checked = false;
        } else {
            hideForce();
        }
    }

    function getLocation() {
        var status = document.getElementById("geo-status");
        if (!navigator.geolocation) {
            status.innerText = "Geolocation is not supported in this browser.";
            return;
        }
        status.className = "hint";
        status.innerText = "Locating…";
        gpsBtn.disabled = true;
        navigator.geolocation.getCurrentPosition(showPosition, showError, {
            enableHighAccuracy: true,
            timeout: 15000,
        });
    }

    async function showPosition(position) {
        var lat = position.coords.latitude;
        var lon = position.coords.longitude;
        document.getElementById("latitude").value = lat;
        document.getElementById("longitude").value = lon;
        var status = document.getElementById("geo-status");
        var address = document.getElementById("address");
        gpsBtn.disabled = false;
        try {
            var response = await fetch("/api/reverse-geocode?lat=" + lat + "&lon=" + lon, {
                credentials: "same-origin"
            });
            var data = await response.json();
            if (data.address) {
                address.value = data.address;
                status.className = "hint text-success";
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
        gpsBtn.disabled = false;
        var status = document.getElementById("geo-status");
        status.className = "hint text-danger";
        status.innerText = "Could not read GPS. Type the address instead.";
    }
})();
