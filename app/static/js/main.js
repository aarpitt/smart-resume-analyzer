// Smart Resume Analyzer - Client Interactions

document.addEventListener("DOMContentLoaded", function () {
    // 1. File Upload Dropzone Handling
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("resume_file");
    const filePreview = document.getElementById("filePreview");
    const fileNameDisplay = document.getElementById("fileNameDisplay");
    const fileSizeDisplay = document.getElementById("fileSizeDisplay");
    const removeFileBtn = document.getElementById("removeFileBtn");
    const analyzeBtn = document.getElementById("analyzeBtn");
    const uploadForm = document.getElementById("uploadForm");
    const analyzeSpinner = document.getElementById("analyzeSpinner");
    const analyzeBtnText = document.getElementById("analyzeBtnText");
    const statusNotice = document.getElementById("statusNotice");

    if (dropzone && fileInput) {
        // Click dropzone to open file picker
        dropzone.addEventListener("click", () => fileInput.click());

        // Drag and drop events
        ["dragenter", "dragover"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add("drag-over");
            }, false);
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove("drag-over");
            }, false);
        });

        dropzone.addEventListener("drop", (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                fileInput.files = files;
                handleFileSelection(files[0]);
            }
        });

        fileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleFileSelection(e.target.files[0]);
            }
        });

        if (removeFileBtn) {
            removeFileBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                fileInput.value = "";
                if (filePreview) filePreview.classList.add("d-none");
                dropzone.classList.remove("d-none");
                if (analyzeBtn) analyzeBtn.disabled = true;
            });
        }
    }

    function handleFileSelection(file) {
        const allowedExts = [".pdf", ".docx"];
        const fileName = file.name;
        const fileExt = fileName.substring(fileName.lastIndexOf(".")).toLowerCase();
        const maxBytes = 5 * 1024 * 1024; // 5 MB

        if (!allowedExts.includes(fileExt)) {
            alert("Unsupported file format! Please upload a PDF (.pdf) or Word document (.docx).");
            fileInput.value = "";
            return;
        }

        if (file.size > maxBytes) {
            alert("File size exceeds 5MB limit. Please choose a smaller file.");
            fileInput.value = "";
            return;
        }

        if (fileNameDisplay) fileNameDisplay.textContent = fileName;
        if (fileSizeDisplay) {
            const kb = (file.size / 1024).toFixed(1);
            fileSizeDisplay.textContent = `${kb} KB`;
        }

        if (dropzone) dropzone.classList.add("d-none");
        if (filePreview) filePreview.classList.remove("d-none");
        if (analyzeBtn) analyzeBtn.disabled = false;
    }

    // 2. Form Submission Loading UI
    if (uploadForm && analyzeBtn) {
        uploadForm.addEventListener("submit", function () {
            analyzeBtn.disabled = true;
            if (analyzeSpinner) analyzeSpinner.classList.remove("d-none");
            if (analyzeBtnText) analyzeBtnText.textContent = "Analyzing Resume...";

            if (statusNotice) {
                statusNotice.classList.remove("d-none");
                const steps = [
                    "Extracting text & section hierarchy...",
                    "Matching keywords against role benchmarks...",
                    "Computing TF-IDF semantic profile similarity...",
                    "Generating actionable recommendations..."
                ];
                let stepIdx = 0;
                setInterval(() => {
                    stepIdx = (stepIdx + 1) % steps.length;
                    statusNotice.textContent = steps[stepIdx];
                }, 1200);
            }
        });
    }

    // 3. Custom Job Fields Toggle & Word Counter
    const roleRadios = document.querySelectorAll('input[name="target_role"]');
    const customJobFields = document.getElementById("customJobFields");
    const customTitleInput = document.getElementById("custom_job_title");
    const customJdInput = document.getElementById("custom_job_description");
    const jdWordCountBadge = document.getElementById("jdWordCountBadge");

    if (roleRadios.length > 0 && customJobFields) {
        roleRadios.forEach(radio => {
            radio.addEventListener("change", function () {
                if (this.value === "Custom Job Analysis") {
                    customJobFields.classList.remove("d-none");
                    if (customTitleInput) customTitleInput.required = true;
                    if (customJdInput) customJdInput.required = true;
                } else {
                    customJobFields.classList.add("d-none");
                    if (customTitleInput) customTitleInput.required = false;
                    if (customJdInput) customJdInput.required = false;
                }
            });
        });

        if (customJdInput && jdWordCountBadge) {
            customJdInput.addEventListener("input", function () {
                const text = this.value.trim();
                const words = text ? text.split(/\s+/).length : 0;
                if (words >= 30) {
                    jdWordCountBadge.textContent = `${words} words (Requirement met)`;
                    jdWordCountBadge.className = "badge bg-success-subtle text-success small";
                } else {
                    jdWordCountBadge.textContent = `${words} words (min. 30 recommended)`;
                    jdWordCountBadge.className = "badge bg-secondary-subtle text-secondary small";
                }
            });
        }
    }

    // 4. Recommendation Filter in Dashboard
    const filterButtons = document.querySelectorAll(".rec-filter-btn");
    const recCards = document.querySelectorAll(".rec-card-item");

    if (filterButtons.length > 0 && recCards.length > 0) {
        filterButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                filterButtons.forEach(b => b.classList.remove("active", "btn-dark"));
                filterButtons.forEach(b => b.classList.add("btn-outline-secondary"));

                btn.classList.add("active", "btn-dark");
                btn.classList.remove("btn-outline-secondary");

                const targetSeverity = btn.getAttribute("data-filter");

                recCards.forEach(card => {
                    if (targetSeverity === "all" || card.getAttribute("data-severity") === targetSeverity) {
                        card.style.display = "block";
                    } else {
                        card.style.display = "none";
                    }
                });
            });
        });
    }
});
