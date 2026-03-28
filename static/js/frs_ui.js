document.addEventListener("DOMContentLoaded", function () {
    initNestedDropdowns();
    initLeaveFormUI();
});

function initNestedDropdowns() {
    const submenuToggles = document.querySelectorAll(".dropdown-submenu > .dropdown-toggle");

    submenuToggles.forEach(function (toggle) {
        toggle.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            const parentLi = this.parentElement;
            const submenu = parentLi.querySelector(".dropdown-menu");

            if (!submenu) {
                return;
            }

            const siblingSubmenus = parentLi.parentElement.querySelectorAll(":scope > .dropdown-submenu");
            siblingSubmenus.forEach(function (sibling) {
                if (sibling !== parentLi) {
                    sibling.classList.remove("show");
                    const siblingMenu = sibling.querySelector(":scope > .dropdown-menu");
                    if (siblingMenu) {
                        siblingMenu.classList.remove("show");
                    }
                }
            });

            parentLi.classList.toggle("show");
            submenu.classList.toggle("show");
        });
    });

    document.addEventListener("click", function () {
        document.querySelectorAll(".dropdown-submenu").forEach(function (submenuLi) {
            submenuLi.classList.remove("show");
            const submenu = submenuLi.querySelector(":scope > .dropdown-menu");
            if (submenu) {
                submenu.classList.remove("show");
            }
        });
    });

    document.querySelectorAll(".dropdown-menu").forEach(function (menu) {
        menu.addEventListener("click", function (event) {
            event.stopPropagation();
        });
    });

    document.querySelectorAll(".dropdown").forEach(function (dropdownRoot) {
        dropdownRoot.addEventListener("hidden.bs.dropdown", function () {
            this.querySelectorAll(".dropdown-submenu").forEach(function (submenuLi) {
                submenuLi.classList.remove("show");
                const submenu = submenuLi.querySelector(":scope > .dropdown-menu");
                if (submenu) {
                    submenu.classList.remove("show");
                }
            });
        });
    });
}

function initLeaveFormUI() {
    const form = document.querySelector(".js-leave-form");
    if (!form) {
        return;
    }

    const personSelect = form.querySelector("#id_person");
    const dateFromInput = form.querySelector("#id_date_from");
    const dateToInput = form.querySelector("#id_date_to");
    const positionBox = form.querySelector(".js-person-position-preview");
    const shiftBox = form.querySelector(".js-person-shift-preview");
    const previewUrl = form.dataset.personPreviewUrl || "";

    applyDateInputEnhancements(dateFromInput, dateToInput);

    if (!personSelect || !positionBox || !shiftBox || !previewUrl) {
        return;
    }

    let previewTimer = null;
    let activeController = null;

    function setPreview(positionText, shiftText) {
        positionBox.textContent = positionText || "—";
        shiftBox.textContent = shiftText || "—";
    }

    function loadPreview() {
        const personId = (personSelect.value || "").trim();
        const dateFrom = (dateFromInput?.value || "").trim();
        const dateTo = (dateToInput?.value || "").trim();

        if (!personId) {
            setPreview("—", "—");
            return;
        }

        const params = new URLSearchParams();
        params.set("person", personId);
        if (dateFrom) {
            params.set("date_from", dateFrom);
        }
        if (dateTo) {
            params.set("date_to", dateTo);
        }

        if (activeController) {
            activeController.abort();
        }

        activeController = new AbortController();

        fetch(`${previewUrl}?${params.toString()}`, {
            method: "GET",
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            },
            signal: activeController.signal
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Preview request failed.");
                }
                return response.json();
            })
            .then(function (data) {
                setPreview(data.position || "—", data.shift || "—");
            })
            .catch(function (error) {
                if (error.name === "AbortError") {
                    return;
                }
                setPreview("—", "—");
            });
    }

    function queuePreviewUpdate() {
        if (previewTimer) {
            clearTimeout(previewTimer);
        }
        previewTimer = setTimeout(loadPreview, 200);
    }

    personSelect.addEventListener("change", queuePreviewUpdate);

    if (dateFromInput) {
        dateFromInput.addEventListener("change", queuePreviewUpdate);
        dateFromInput.addEventListener("input", queuePreviewUpdate);
    }

    if (dateToInput) {
        dateToInput.addEventListener("change", queuePreviewUpdate);
        dateToInput.addEventListener("input", queuePreviewUpdate);
    }

    queuePreviewUpdate();
}

function applyDateInputEnhancements(dateFromInput, dateToInput) {
    [dateFromInput, dateToInput].forEach(function (input) {
        if (!input) {
            return;
        }

        if (!input.getAttribute("placeholder")) {
            input.setAttribute("placeholder", "YYYY-MM-DD");
        }

        input.setAttribute("autocomplete", "off");
    });

    if (!dateFromInput || !dateToInput) {
        return;
    }

    dateFromInput.addEventListener("change", function () {
        if (!dateToInput.value) {
            dateToInput.value = dateFromInput.value;
        }
    });
}


// ===== Cover form preview =====
document.addEventListener("DOMContentLoaded", function () {
    const absenceSelect = document.getElementById("id_absence");
    const dateFrom = document.getElementById("id_date_from");
    const dateTo = document.getElementById("id_date_to");
    const select = document.getElementById("id_covering_person");

    if (!absenceSelect || !dateFrom || !select) return;

    function updatePreview() {
        const absence = absenceSelect.value;
        const df = dateFrom.value;
        const dt = dateTo ? dateTo.value : "";

        if (!absence || !df) return;

        fetch(`/staff/cover/preview/?absence=${absence}&date_from=${df}&date_to=${dt}`)
            .then(r => r.json())
            .then(data => {
                const items = data.items || [];

                const current = select.value;

                select.innerHTML = "";

                const groupBest = document.createElement("optgroup");
                groupBest.label = "Recommended";

                const groupAll = document.createElement("optgroup");
                groupAll.label = "All";

                items.forEach(item => {
                    const opt = document.createElement("option");
                    opt.value = item.id;

                    let label = item.name;

                    if (item.position) {
                        label += ` (${item.position})`;
                    }

                    if (item.busy) {
                        label += " — busy";
                    }

                    opt.textContent = label;

                    if (item.score >= 3) {
                        groupBest.appendChild(opt);
                    } else {
                        groupAll.appendChild(opt);
                    }
                });

                if (groupBest.children.length) {
                    select.appendChild(groupBest);
                }

                select.appendChild(groupAll);

                select.value = current;
            });
    }

    absenceSelect.addEventListener("change", updatePreview);
    dateFrom.addEventListener("change", updatePreview);
    if (dateTo) {
        dateTo.addEventListener("change", updatePreview);
    }
});