const fileInput = document.getElementById("fileInput");
const dropZone = document.getElementById("dropZone");
const uploadStatus = document.getElementById("uploadStatus");
const documentList = document.getElementById("documentList");
const messages = document.getElementById("messages");
const emptyState = document.getElementById("emptyState");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");
let currentUserId = "default_user";
let currentChatId = null;

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}


function addMessage(role, text) {
    if (emptyState) emptyState.remove();

    const row = document.createElement("div");
    row.className = `message ${role}`;

    row.innerHTML = `
        <div class="bubble">${escapeHtml(text)}</div>
    `;

    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;

    return row;
}


function showTyping() {
    const row = document.createElement("div");

    row.id = "typing";
    row.className = "message assistant";

    row.innerHTML = `
        <div class="bubble typing">
            Thinking from your documents…
        </div>
    `;

    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
}


function hideTyping() {
    document.getElementById("typing")?.remove();
}


function showSources(sources) {
    if (!sources || !sources.length) return;

    const wrap = document.createElement("div");
    wrap.className = "sources";

    sources.forEach(source => {
        const page = source.page ? ` · Page ${source.page}` : "";

        const card = document.createElement("span");
        card.className = "source-card";
        card.textContent = `${source.source}${page}`;

        wrap.appendChild(card);
    });

    messages.appendChild(wrap);
    messages.scrollTop = messages.scrollHeight;
}


/* =========================
   LOAD DOCUMENTS
========================= */

async function loadDocuments() {
    try {
        const res = await fetch("/documents");
        const data = await res.json();

        documentList.innerHTML = "";

        (data.documents || []).forEach(doc => {
            const card = document.createElement("div");
            card.className = "doc-card";

            card.innerHTML = `
                <div class="doc-name">
                    <strong title="${escapeHtml(doc.filename)}">
                        ${escapeHtml(doc.filename)}
                    </strong>

                    <div class="doc-meta">
                        ${doc.chunk_count} chunks · ${doc.file_type.toUpperCase()}
                    </div>
                </div>

                <button
                    class="delete-btn"
                    title="Delete document">
                    ✕
                </button>
            `;

            card.querySelector(".delete-btn").onclick = () => {
                deleteDocument(doc.document_id);
            };

            documentList.appendChild(card);
        });

    } catch (error) {
        console.error("Could not load documents:", error);
    }
}


/* =========================
   UPLOAD FILE
========================= */

async function uploadFile(file) {

    if (!file) return;

    console.log("Selected file:", file.name);
    console.log("File type:", file.type);

    /*
       Check extension.
       This supports:
       PDF
       DOCX
       TXT
    */

    const fileName = file.name || "";
    const dotIndex = fileName.lastIndexOf(".");

    const ext = dotIndex !== -1
        ? fileName.substring(dotIndex + 1).toLowerCase()
        : "";

    const allowedExtensions = ["pdf", "docx", "txt"];

    if (!allowedExtensions.includes(ext)) {
        uploadStatus.textContent =
            "Only PDF, DOCX and TXT files are allowed.";

        fileInput.value = "";
        return;
    }


    /* Create form data */

    const form = new FormData();
    form.append("file", file);


    /* Show upload status */

    uploadStatus.textContent = "Uploading and indexing document…";


    try {

        const res = await fetch("/upload", {
            method: "POST",
            body: form
        });


        const data = await res.json();


        if (!res.ok) {
            throw new Error(
                data.error || "Upload failed."
            );
        }


        /* Success message */

        if (data.duplicate) {

            uploadStatus.textContent =
                "This document is already indexed.";

        } else {

            uploadStatus.textContent =
                `${data.filename} indexed · ${data.chunks} chunks.`;
        }


        /* Refresh document list */

        await loadDocuments();


    } catch (error) {

        console.error("Upload error:", error);

        uploadStatus.textContent =
            error.message || "Upload failed.";

    } finally {

        fileInput.value = "";
    }
}


/* =========================
   DELETE DOCUMENT
========================= */

async function deleteDocument(id) {

    if (!confirm(
        "Delete this document from the vector database?"
    )) {
        return;
    }


    try {

        const res = await fetch(
            `/documents/${encodeURIComponent(id)}`,
            {
                method: "DELETE"
            }
        );


        const data = await res.json();


        if (!res.ok) {
            throw new Error(
                data.error || "Delete failed."
            );
        }


        await loadDocuments();


    } catch (error) {

        uploadStatus.textContent =
            error.message || "Delete failed.";
    }
}


/* =========================
   CHAT
========================= */

async function sendMessage() {

    const text = input.value.trim();

    if (!text || sendBtn.disabled) {
        return;
    }


    addMessage("user", text);

    input.value = "";
    input.style.height = "auto";

    sendBtn.disabled = true;

    showTyping();


    try {

        const res = await fetch("/chat", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: text
            })
        });


        const data = await res.json();


        if (!res.ok) {
            throw new Error(
                data.error || "Chat failed."
            );
        }


        hideTyping();

        addMessage(
            "assistant",
            data.answer
        );

        showSources(data.sources);


    } catch (error) {

        hideTyping();

        addMessage(
            "assistant",
            error.message || "Unable to generate the answer now."
        );

    } finally {

        sendBtn.disabled = false;

        input.focus();
    }
}


/* =========================
   FILE SELECT
========================= */

fileInput.addEventListener(
    "change",
    function (event) {
        console.log("FILE SELECTED");

        const files = event.target.files;

        if (!files || files.length === 0) {
            return;
        }

        uploadFile(files[0]);
    }
);


/* =========================
   DRAG & DROP
========================= */

["dragenter", "dragover"].forEach(type => {

    dropZone.addEventListener(type, event => {

        event.preventDefault();

        dropZone.classList.add("dragging");
    });
});


["dragleave", "drop"].forEach(type => {

    dropZone.addEventListener(type, event => {

        event.preventDefault();

        dropZone.classList.remove("dragging");
    });
});


dropZone.addEventListener("drop", event => {

    const files = event.dataTransfer.files;

    if (!files || files.length === 0) {
        return;
    }

    uploadFile(files[0]);
});


/* =========================
   SEND BUTTON
========================= */

sendBtn.addEventListener(
    "click",
    sendMessage
);


/* =========================
   ENTER TO SEND
========================= */

input.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();
        }
    }
);


/* =========================
   TEXTAREA RESIZE
========================= */

input.addEventListener(
    "input",
    () => {

        input.style.height = "auto";

        input.style.height =
            Math.min(
                input.scrollHeight,
                160
            ) + "px";
    }
);


/* =========================
   CLEAR CHAT
========================= */

clearBtn.addEventListener(
    "click",
    () => {

        messages.innerHTML = `
            <div class="empty-state" id="emptyState">

                <div class="empty-icon">
                    ✦
                </div>

                <h1>
                    Ask your documents
                </h1>

                <p>
                    Upload a PDF, DOCX, or TXT file,
                    then ask a question about its content.
                </p>

            </div>
        `;

        input.focus();
    }
);


/* =========================
   INITIAL LOAD
========================= */

loadDocuments();