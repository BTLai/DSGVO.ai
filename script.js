document.getElementById("urlForm").addEventListener("submit", function (event) {
  event.preventDefault();
  showEmailForm();
});

document.querySelectorAll(".scrollTopBtn").forEach((btn) => {
  btn.addEventListener("click", function () {
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const faqQuestions = document.querySelectorAll(".faq-question");

  faqQuestions.forEach((question) => {
    question.addEventListener("click", () => {
      const answer = question.nextElementSibling;
      answer.style.display =
        answer.style.display === "block" ? "none" : "block";
    });
  });
});

document
  .getElementById("emailForm")
  .addEventListener("submit", function (event) {
    event.preventDefault();
    const websiteUrl = document.getElementById("websiteUrl").value;
    const emailAddress = document.getElementById("emailAddress").value;
    sendToGCPFunction(websiteUrl, emailAddress);
  });

function showEmailForm() {
  document.getElementById("websiteUrlDisplay").textContent =
    document.getElementById("websiteUrl").value;
  document.getElementById("urlForm").style.display = "none";
  document.getElementById("emailForm").style.display = "flex";
}

function sendToGCPFunction(websiteUrl, emailAddress) {
  const gcpFunctionUrl =
    "https://europe-west3-dsgvo-422512.cloudfunctions.net/dsgvo_analyse-1";
  console.log("Sending to GCP Function:", websiteUrl, emailAddress);
  const data = {
    url: websiteUrl,
    email: emailAddress,
  };
  fetch(gcpFunctionUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  showSuccessMessage();
}

function showSuccessMessage() {
  // You might want to adjust this part to fit your HTML structure or styling
  document.getElementById("emailForm").style.display = "none"; // Hide the email form
  document.getElementById("successMessage").style.display = "flex"; // Show the success message
}
