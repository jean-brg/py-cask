document.addEventListener('DOMContentLoaded', () => {
    const button = document.getElementById('alertBtn');
    if (button) {
        button.addEventListener('click', () => {
            alert("Some JavaScript code!");
        });
    }
});