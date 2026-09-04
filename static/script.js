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
            toast.style.transform = "translateY(-8px)";
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
        if (form.id === "reportForm") return;
        form.addEventListener("submit", function () {
            var btn = form.querySelector("button[type=submit]");
            if (!btn || btn.dataset.busy) return;
            btn.dataset.busy = "1";
            btn.style.opacity = "0.72";
            btn.textContent = "Please wait…";
        });
    });

    var fileInput = document.getElementById("imageUpload");
    var categorySelect = document.getElementById("categoryId");
    var statusText = document.getElementById("aiStatus");
    var gpsBtn = document.getElementById("gpsBtn");
    var dropzone = document.getElementById("dropzone");
    var preview = document.getElementById("photoPreview");
    var dropUi = document.getElementById("dropzoneUi");
    var cameraBtn = document.getElementById("cameraBtn");
    var galleryBtn = document.getElementById("galleryBtn");
    var liveCamera = document.getElementById("liveCamera");
    var cameraBar = document.getElementById("cameraBar");
    var snapBtn = document.getElementById("snapBtn");
    var cancelCamBtn = document.getElementById("cancelCamBtn");
    var photoEditBar = document.getElementById("photoEditBar");
    var retakeBtn = document.getElementById("retakeBtn");
    var clearPhotoBtn = document.getElementById("clearPhotoBtn");
    if (!categorySelect) return;

    var aiSuggestedId = null;
    var evidenceBlob = null;
    var previewUrl = "";
    var cameraStream = null;
    var reportForm = document.getElementById("reportForm");
    var photoPipeline = Promise.resolve();

    if (cameraBtn) cameraBtn.addEventListener("click", startCamera);
    if (galleryBtn) galleryBtn.addEventListener("click", function () { fileInput.click(); });
    if (snapBtn) snapBtn.addEventListener("click", snapCamera);
    if (cancelCamBtn) cancelCamBtn.addEventListener("click", stopCamera);
    if (retakeBtn) retakeBtn.addEventListener("click", function () {
        clearPhoto(false);
        startCamera();
    });
    if (clearPhotoBtn) clearPhotoBtn.addEventListener("click", function () {
        clearPhoto(true);
    });
    if (fileInput) {
        fileInput.addEventListener("change", function () {
            var file = fileInput.files && fileInput.files[0];
            fileInput.value = "";
            if (!file) return;
            photoPipeline = useSmallPhoto(file);
        });
    }
    categorySelect.addEventListener("change", checkOverride);
    if (gpsBtn) gpsBtn.addEventListener("click", getLocation);

    if (reportForm) {
        reportForm.addEventListener("submit", function (e) {
            e.preventDefault();
            submitReport(reportForm);
        });
    }

    function setStatus(kind, text) {
        if (!statusText) return;
        statusText.className = "hint " + (kind || "");
        statusText.innerText = text;
    }

    function showSmallPreview(blob) {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = URL.createObjectURL(blob);
        if (dropUi) dropUi.classList.add("is-hidden");
        if (liveCamera) liveCamera.classList.add("is-hidden");
        if (cameraBar) cameraBar.classList.add("is-hidden");
        if (preview) {
            preview.src = previewUrl;
            preview.classList.remove("is-hidden");
        }
        if (photoEditBar) photoEditBar.classList.remove("is-hidden");
        dropzone.classList.add("has-photo");
    }

    function clearPhoto(resetStatus) {
        evidenceBlob = null;
        aiSuggestedId = null;
        hideForce();
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = "";
        }
        if (preview) {
            preview.removeAttribute("src");
            preview.classList.add("is-hidden");
        }
        if (photoEditBar) photoEditBar.classList.add("is-hidden");
        dropzone.classList.remove("has-photo");
        if (dropUi) dropUi.classList.remove("is-hidden");
        if (resetStatus) {
            setStatus("", "AI will suggest a category after you pick a photo.");
        }
    }

    function stopCamera() {
        if (cameraStream) {
            cameraStream.getTracks().forEach(function (t) { t.stop(); });
            cameraStream = null;
        }
        if (liveCamera) {
            liveCamera.srcObject = null;
            liveCamera.classList.add("is-hidden");
        }
        if (cameraBar) cameraBar.classList.add("is-hidden");
        if (dropUi && !evidenceBlob) dropUi.classList.remove("is-hidden");
    }

    async function startCamera() {
        stopCamera();
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            setStatus("ai-error", "This browser cannot open the in-app camera. Try Gallery with a small image.");
            return;
        }
        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({
                audio: false,
                video: {
                    facingMode: { ideal: "environment" },
                    width: { ideal: 1280, max: 1280 },
                    height: { ideal: 720, max: 720 }
                }
            });
            liveCamera.srcObject = cameraStream;
            liveCamera.classList.remove("is-hidden");
            cameraBar.classList.remove("is-hidden");
            dropUi.classList.add("is-hidden");
            if (preview) preview.classList.add("is-hidden");
            if (photoEditBar) photoEditBar.classList.add("is-hidden");
        } catch (err) {
            setStatus("ai-error", "Camera permission denied. Allow camera, or pick a small photo from Gallery.");
        }
    }

    function canvasToJpeg(canvas) {
        return new Promise(function (resolve, reject) {
            canvas.toBlob(function (blob) {
                if (blob) resolve(blob);
                else reject(new Error("jpeg"));
            }, "image/jpeg", 0.72);
        });
    }

    async function snapCamera() {
        if (!liveCamera || !liveCamera.videoWidth) {
            setStatus("ai-error", "Camera is still starting. Wait a second and tap Capture.");
            return;
        }
        var max = 960;
        var scale = Math.min(1, max / Math.max(liveCamera.videoWidth, liveCamera.videoHeight));
        var canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.round(liveCamera.videoWidth * scale));
        canvas.height = Math.max(1, Math.round(liveCamera.videoHeight * scale));
        var ctx = canvas.getContext("2d", { alpha: false });
        ctx.drawImage(liveCamera, 0, 0, canvas.width, canvas.height);
        try {
            var blob = await canvasToJpeg(canvas);
            stopCamera();
            await useEvidence(blob);
        } catch (err) {
            setStatus("ai-error", "Could not capture. Try again.");
        }
    }

    async function shrinkFile(file) {
        if (!file) throw new Error("no file");
        if (file.size < 220 * 1024 && file.type === "image/jpeg") return file;
        if (!window.createImageBitmap) throw new Error("no bitmap");
        var bmp = await createImageBitmap(file, {
            resizeWidth: 960,
            resizeQuality: "low"
        });
        var canvas = document.createElement("canvas");
        canvas.width = bmp.width;
        canvas.height = bmp.height;
        var ctx = canvas.getContext("2d", { alpha: false });
        ctx.drawImage(bmp, 0, 0);
        bmp.close();
        return canvasToJpeg(canvas);
    }

    async function useSmallPhoto(file) {
        setStatus("ai-thinking", "Shrinking photo…");
        try {
            var small = await shrinkFile(file);
            await useEvidence(small);
        } catch (err) {
            setStatus("ai-error", "That gallery photo is too large for this phone. Use Take photo instead.");
        }
    }

    async function useEvidence(blob) {
        evidenceBlob = blob;
        showSmallPreview(blob);
        await autoDetectCategory();
    }

    async function autoDetectCategory() {
        if (!evidenceBlob) return;
        setStatus("ai-thinking", "AI is reading the photo…");

        var formData = new FormData();
        formData.append("file", evidenceBlob, "evidence.jpg");

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

    async function submitReport(form) {
        var btn = document.getElementById("submitReport");
        if (btn && btn.dataset.busy) return;
        if (btn) {
            btn.dataset.busy = "1";
            btn.style.opacity = "0.72";
            btn.textContent = "Submitting…";
        }
        try {
            await photoPipeline;
            if (!evidenceBlob) {
                throw new Error("photo");
            }
            var body = new FormData(form);
            body.delete("file");
            var csrf = document.querySelector('meta[name="csrf-token"]');
            var headers = {};
            if (csrf && csrf.content) headers["X-CSRF-Token"] = csrf.content;
            var response = await fetch("/report", {
                method: "POST",
                body: body,
                headers: headers,
                credentials: "same-origin",
                redirect: "follow"
            });
            if (!response.ok && response.status >= 500) {
                throw new Error("server");
            }
            window.location.href = response.url || "/my-reports";
        } catch (err) {
            if (btn) {
                delete btn.dataset.busy;
                btn.style.opacity = "";
                btn.textContent = "Submit report";
            }
            if (statusText) {
                statusText.className = "hint ai-error";
                statusText.innerText = "Submit failed on this connection. Wait a few seconds and try again with the same photo.";
            }
        }
    }
})();
