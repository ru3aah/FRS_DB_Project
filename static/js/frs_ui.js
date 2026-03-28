document.addEventListener("DOMContentLoaded", function () {
    initNestedDropdowns();
    initLeaveFormUI();
    initCoverFormUI();
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

    const personMetaId = form.dataset.personMetaId;
    const metaNode = personMetaId ? document.getElementById(personMetaId) : null;

    let personMeta = {};
    if (metaNode) {
        try {
            personMeta = JSON.parse(metaNode.textContent);
        } catch (error) {
            personMeta = {};
        }
    }

    const personSelect = form.querySelector("#id_person");
    const positionBox = form.querySelector(".js-person-position-preview");
    const shiftBox = form.querySelector(".js-person-shift-preview");
    const dateFromInput = form.querySelector("#id_date_from");
    const dateToInput = form.querySelector("#id_date_to");

    applyDateInputEnhancements(dateFromInput, dateToInput);

    function updatePersonPreview() {
        if (!personSelect || !positionBox || !shiftBox) {
            return;
        }

        const selectedId = personSelect.value || "";
        const item = personMeta[selectedId] || {};

        positionBox.textContent = item.position || "—";
        shiftBox.textContent = item.shift || "—";
    }

    if (personSelect) {
        personSelect.addEventListener("change", updatePersonPreview);
        updatePersonPreview();
    }
}

function initCoverFormUI() {
    const form = document.querySelector(".js-cover-form");
    if (!form) {
        return;
    }

    const dateFromInput = form.querySelector("#id_date_from");
    const dateToInput = form.querySelector("#id_date_to");

    applyDateInputEnhancements(dateFromInput, dateToInput);
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
        input.classList.add("frs-date-input");
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