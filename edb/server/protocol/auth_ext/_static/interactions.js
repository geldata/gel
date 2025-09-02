document.addEventListener("DOMContentLoaded", () => {
  /** @type {HTMLElement | null} */
  const sliderContainer = /** @type {HTMLElement | null} */ (
    document.getElementById("slider-container")
  );

  if (!sliderContainer) {
    return;
  }

  /** @type {HTMLElement | null} */
  const tabsContainer = /** @type {HTMLElement | null} */ (
    document.getElementById("email-provider-tabs")
  );
  if (tabsContainer) {
    /** @type {HTMLElement[]} */
    const tabButtons = /** @type {HTMLElement[]} */ (
      Array.from(tabsContainer.children)
    );
    for (let i = 0; i < tabButtons.length; i++) {
      const tab = tabButtons[i];
      tab.addEventListener("click", () => {
        activateTab(i);
      });
      /** @param {KeyboardEvent} e */
      tab.addEventListener("keydown", (e) => {
        switch (e.key) {
          case "ArrowLeft":
            e.preventDefault();
            focusTab((i - 1 + tabButtons.length) % tabButtons.length);
            break;
          case "ArrowRight":
            e.preventDefault();
            focusTab((i + 1) % tabButtons.length);
            break;
          case "Home":
            e.preventDefault();
            focusTab(0);
            break;
          case "End":
            e.preventDefault();
            focusTab(tabButtons.length - 1);
            break;
          case "Enter":
          case " ":
            e.preventDefault();
            activateTab(i);
            break;
        }
      });
    }

    /** @param {number} index */
    function focusTab(index) {
      for (let j = 0; j < tabButtons.length; j++) {
        const t = tabButtons[j];
        const isActive = j === index;
        t.setAttribute("tabindex", isActive ? "0" : "-1");
      }
      tabButtons[index].focus();
    }

    /** @param {number} index */
    function activateTab(index) {
      const tabChildren = /** @type {HTMLCollection} */ (
        /** @type {HTMLElement} */ (tabsContainer).children
      );
      setActiveClass(tabChildren, index);
      syncAriaState(tabChildren, /** @type {HTMLElement} */ (sliderContainer), index);
      moveSliderToIndex(/** @type {HTMLElement} */ (sliderContainer), index);
    }
  } else {
    /** @type {HTMLFormElement | null} */
    const form = /** @type {HTMLFormElement | null} */ (
      document.getElementById("email-factor")
    );
    if (!form) {
      return;
    }
    let mainFormAction = form.action;

    /** @type {HTMLInputElement[]} */
    const hiddenInputs = /** @type {HTMLInputElement[]} */ (
      Array.from(form.querySelectorAll("input[type=hidden]"))
    ).filter((input) => !!input.dataset.secondaryValue);
    /** @type {string[]} */
    const hiddenInputValues = hiddenInputs.map((input) => input.value);

    if (!sliderContainer.children[0].classList.contains("active")) {
      form.action = /** @type {any} */ (form.dataset).secondaryAction;
      setInputValues(hiddenInputs);
    }

    /** @type {HTMLElement | null} */
    const showBtn = /** @type {HTMLElement | null} */ (
      document.getElementById("show-password-form")
    );
    showBtn?.setAttribute("aria-controls", "panel-password");
    showBtn?.setAttribute("aria-expanded", "false");
    document
      .getElementById("password-email")
      ?.setAttribute("aria-describedby", "show-password-form");

    document
      .getElementById("hide-password-form")
      ?.setAttribute("aria-controls", "panel-password");

    showBtn?.addEventListener("click", () => {
        moveSliderToIndex(/** @type {HTMLElement} */ (sliderContainer), 1);

        form.action = /** @type {any} */ (form.dataset).secondaryAction;
        setInputValues(hiddenInputs);

        document.getElementById("password")?.focus({ preventScroll: true });
        showBtn.setAttribute("aria-expanded", "true");
      });

    document.getElementById("hide-password-form")?.addEventListener("click", () => {
        moveSliderToIndex(/** @type {HTMLElement} */ (sliderContainer), 0);

        form.action = mainFormAction;
        setInputValues(hiddenInputs, hiddenInputValues);
        showBtn?.setAttribute("aria-expanded", "false");
      });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  /** @type {HTMLAnchorElement | null} */
  const forgotLink = /** @type {HTMLAnchorElement | null} */ (
    document.getElementById("forgot-password-link")
  );
  // Find the email input near the forgot link; fall back to a known id.
  /** @type {HTMLInputElement | null} */
  const emailInput =
    /** @type {HTMLInputElement | null} */ (
      forgotLink?.closest("form")?.querySelector('input[name="email"]')
    ) || /** @type {HTMLInputElement | null} */ (
      document.getElementById("password-email")
    );
  if (forgotLink && emailInput) {
    const href = forgotLink.href;
    emailInput.addEventListener("input", (e) => {
      const target = /** @type {HTMLInputElement} */ (e.target);
      forgotLink.href = `${href}&email=${encodeURIComponent(target.value)}`;
    });
    forgotLink.href = `${href}&email=${encodeURIComponent(emailInput.value)}`;
  }

  /** @type {NodeListOf<HTMLInputElement>} */
  const emailInputs = /** @type {NodeListOf<HTMLInputElement>} */ (
    document.querySelectorAll("input[name=email]")
  );
  for (const input of emailInputs) {
    input.addEventListener("input", (e) => {
      const target = /** @type {HTMLInputElement} */ (e.target);
      const val = target.value;
      for (const _input of emailInputs) {
        if (_input !== input) {
          _input.value = val;
        }
      }
    });
  }
});

/**
 * @param {HTMLInputElement[]} inputs
 * @param {string[]} [values]
 */
function setInputValues(inputs, values) {
  for (let i = 0; i < inputs.length; i++) {
    const input = inputs[i];
    const secondary = /** @type {any} */ (input.dataset).secondaryValue;
    input.value = values ? values[i] : secondary || "";
  }
}

let firstInteraction = true;

/**
 * @param {HTMLElement} sliderContainer
 * @param {number} index
 */
function moveSliderToIndex(sliderContainer, index) {
  if (firstInteraction) {
    firstInteraction = false;
    // Fix the height of the main form card wrapper so the layout doesn't shift
    // when tabs are clicked
    const containerWrapper = document.getElementById("container-wrapper");
    if (containerWrapper) {
      containerWrapper.style.height =
        containerWrapper.getElementsByClassName("container")[0].clientHeight +
        "px";
    }

    // Set the height for the first time as transition from 'auto' doesn't work
    sliderContainer.style.height = `${
      sliderContainer.getElementsByClassName("active")[0].scrollHeight
    }px`;
  }

  setActiveClass(sliderContainer.children, index);
  sliderContainer.style.transform = `translateX(${-100 * index}%)`;
  sliderContainer.style.height = `${sliderContainer.children[index].scrollHeight}px`;
}

/**
 * @param {HTMLCollection} tabButtons
 * @param {HTMLElement} sliderContainer
 * @param {number} index
 */
function syncAriaState(tabButtons, sliderContainer, index) {
  for (let i = 0; i < tabButtons.length; i++) {
    const tab = /** @type {HTMLElement} */ (tabButtons[i]);
    const isActive = i === index;
    tab.setAttribute("aria-selected", isActive ? "true" : "false");
    tab.setAttribute("tabindex", isActive ? "0" : "-1");
  }

  const panels = /** @type {HTMLCollectionOf<HTMLElement>} */ (sliderContainer.children);
  for (let i = 0; i < panels.length; i++) {
    const isActive = i === index;
    if (isActive) {
      panels[i].removeAttribute("hidden");
      panels[i].setAttribute("aria-hidden", "false");
    } else {
      panels[i].setAttribute("hidden", "");
      panels[i].setAttribute("aria-hidden", "true");
    }
  }
}

/**
 * @param {HTMLCollection} items
 * @param {number} index
 */
function setActiveClass(items, index) {
  for (let i = 0; i < items.length; i++) {
    if (i === index) {
      items[i].classList.add("active");
    } else {
      items[i].classList.remove("active");
    }
  }
}
