const pages = document.querySelectorAll('.page');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
let currentPageIndex = 0;

function showPage(index) {
    pages.forEach((page, i) => {
        if (i === index) {
            page.style.display = 'block';
        } else {
            page.style.display = 'none';
        }
    });

    prevBtn.disabled = index === 0;

    // Modify the next button for the last page
    if (index === pages.length - 1 ) {
        nextBtn.textContent = 'Submit';
        nextBtn.type = 'submit';
        nextBtn.removeEventListener('click', navigateNext);
    } else {
        nextBtn.textContent = 'Next';
        nextBtn.addEventListener('click', navigateNext);
    }
}

function navigateNext() {
    if (currentPageIndex < pages.length - 1) {
        
        currentPageIndex++;
        showPage(currentPageIndex);
    }
}

prevBtn.addEventListener('click', () => {
    if (currentPageIndex > 0) {
        currentPageIndex--;
        showPage(currentPageIndex);
    }
});

nextBtn.addEventListener('click', (event) => {
    if (nextBtn.textContent === "Next") {
        event.preventDefault();  // prevent form submission

    } 
});

showPage(currentPageIndex);


