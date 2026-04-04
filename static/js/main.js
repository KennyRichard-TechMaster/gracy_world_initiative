document.addEventListener("DOMContentLoaded", function () {
  const menuToggle = document.getElementById("menuToggle");
  const siteNav = document.getElementById("siteNav");
  if (menuToggle && siteNav) {
    menuToggle.addEventListener("click", () =>
      siteNav.classList.toggle("show"),
    );
  }

  const reveals = document.querySelectorAll(".reveal");
  function revealOnScroll() {
    const trigger = window.innerHeight * 0.88;
    reveals.forEach((el) => {
      if (el.getBoundingClientRect().top < trigger) {
        el.classList.add("active");
      }
    });
  }
  window.addEventListener("scroll", revealOnScroll);
  window.addEventListener("load", revealOnScroll);

  const faqItems = document.querySelectorAll(".faq-item");
  faqItems.forEach((item) => {
    const button = item.querySelector(".faq-question");
    if (button) {
      button.addEventListener("click", () => {
        item.classList.toggle("active");
      });
    }
  });

  const cursorGlow = document.querySelector(".cursor-glow");
  window.addEventListener("mousemove", (e) => {
    if (!cursorGlow) return;
    cursorGlow.style.left = `${e.clientX}px`;
    cursorGlow.style.top = `${e.clientY}px`;
  });
});
