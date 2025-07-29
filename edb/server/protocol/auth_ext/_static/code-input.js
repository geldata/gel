document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("code-input-container");
  const form = document.getElementById("code-form");
  const hiddenInput = document.getElementById("code-hidden-input");
  if (!container || !form || !hiddenInput) return;
  const inputs = Array.from(container.querySelectorAll("input"));
  inputs.forEach((input, index) => {
    input.addEventListener("input", (e) => {
      const value = e.target.value;
      if (/^\d$/.test(value)) {
        if (index < inputs.length - 1) {
          inputs[index + 1].focus();
        }
      } else {
        e.target.value = "";
      }

      updateHiddenInput();
      if (inputs.every((i) => i.value !== "")) {
        form.submit();
      }
    });

    // Backspace handling
    input.addEventListener("keydown", (e) => {
      if (e.key === "Backspace") {
        if (input.value === "" && index > 0) {
          // Move focus to previous input if current is empty
          inputs[index - 1].focus();
        } else {
          // Clear current input
          input.value = "";
          updateHiddenInput();
        }
      } else if (e.key === "ArrowLeft" && index > 0) {
        // Arrow key navigation
        inputs[index - 1].focus();
      } else if (e.key === "ArrowRight" && index < inputs.length - 1) {
        inputs[index + 1].focus();
      }
    });

    // Paste handling for complete codes
    input.addEventListener("paste", (e) => {
      e.preventDefault();
      const paste = e.clipboardData?.getData("text") || "";
      const digits = paste.replace(/\D/g, "").slice(0, 6);

      if (digits.length > 0) {
        inputs.forEach((inp, i) => {
          inp.value = digits[i] || "";
        });
        updateHiddenInput();

        // Focus the next empty input or the last one
        const nextEmpty = inputs.findIndex(inp => inp.value === "");
        if (nextEmpty !== -1) {
          inputs[nextEmpty].focus();
        } else {
          inputs[inputs.length - 1].focus();
          // Auto-submit if all filled
          if (inputs.every((i) => i.value !== "")) {
            form.submit();
          }
        }
      }
    });

    // Select all text on focus for easier editing
    input.addEventListener("focus", () => {
      input.select();
    });
  });

  function updateHiddenInput() {
    hiddenInput.value = inputs.map((i) => i.value).join("");
  }

  inputs[0].focus();
});
