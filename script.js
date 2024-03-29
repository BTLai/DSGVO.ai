document.getElementById("urlForm").addEventListener("submit", function (event) {
  event.preventDefault();
  showEmailForm();
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
    "https://europe-west3-coral-subject-307511.cloudfunctions.net/dsgvo_analyse"; // Replace with your actual GCP Function URL
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
