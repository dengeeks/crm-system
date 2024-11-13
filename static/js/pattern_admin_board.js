document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.getElementById('menu-toggle');
    const sideMenu = document.getElementById('side_menu');
    const dropdowns = document.querySelectorAll('.dropdown-toggle');

    menuToggle.addEventListener('click', () => {
        sideMenu.classList.toggle('open');
    });

    dropdowns.forEach(dropdown => {
        dropdown.addEventListener('click', (e) => {
            e.preventDefault();
            const parentLi = dropdown.parentElement;
            parentLi.classList.toggle('show');
        });
    });
});
