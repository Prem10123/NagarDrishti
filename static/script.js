async function autoDetect() {
    const fileInput = document.getElementById('imageUpload');
    const categorySelect = document.getElementById('categoryId');
    const statusText = document.getElementById('aiStatus');

    if (fileInput.files.length === 0) return;

    statusText.innerText = "AI is analyzing image...";
    let formData = new FormData();
    formData.append("file", fileInput.files[0]);

    let response = await fetch("/detect-category", {
        method: "POST",
        body: formData
    });

    let result = await response.json();
    categorySelect.value = result.suggested_id;
    statusText.innerText = "Suggested Category: " + result.name;
}