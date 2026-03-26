document.addEventListener("DOMContentLoaded", function () {
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
});