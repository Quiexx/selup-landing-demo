const sections = document.querySelectorAll("[data-animate]");
const form = document.getElementById("apply-form");
const contactInput = document.getElementById("contact");
const contactError = document.getElementById("contact-error");

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.2 }
  );

  sections.forEach((section) => observer.observe(section));
} else {
  sections.forEach((section) => section.classList.add("is-visible"));
}

if (form && contactInput && contactError) {
  const showError = () => {
    contactError.classList.add("is-visible");
    contactInput.setAttribute("aria-invalid", "true");
  };

  const hideError = () => {
    contactError.classList.remove("is-visible");
    contactInput.removeAttribute("aria-invalid");
  };

  form.addEventListener("submit", (event) => {
    if (!contactInput.value.trim()) {
      event.preventDefault();
      showError();
    }
  });

  contactInput.addEventListener("input", () => {
    if (contactInput.value.trim()) {
      hideError();
    }
  });
}
