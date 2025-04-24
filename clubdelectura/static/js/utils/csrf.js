// static/js/utils/csrf.js
export function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
}
