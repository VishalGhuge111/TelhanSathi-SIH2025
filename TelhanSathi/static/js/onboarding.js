document.addEventListener("DOMContentLoaded", () => {

    const steps = document.querySelectorAll(".step");
    let currentStep = 0;

    function showStep(n) {
        steps.forEach(step => step.classList.remove("active"));
        const stepEl = document.querySelector(`.step[data-step="${n}"]`);
        if (stepEl) {
            stepEl.classList.add("active");
            currentStep = n;
        }
    }

    // -----------------------------
    // Step 0 → Start
    // -----------------------------
    const startBtn = document.getElementById("startBtn");
    if (startBtn) {
        startBtn.addEventListener("click", () => showStep(1));
    }

    // -----------------------------
    // Step 1 → Crop Selection
    // -----------------------------
    const cropCards = document.querySelectorAll(".crop-card");
    const cropInput = document.getElementById("cropInput");
    const nextFromCrop = document.getElementById("nextFromCrop");

    cropCards.forEach(card => {
        card.addEventListener("click", () => {
            cropCards.forEach(c => c.classList.remove("selected"));
            card.classList.add("selected");

            cropInput.value = card.dataset.crop;
            nextFromCrop.disabled = false;
        });
    });

    if (nextFromCrop) {
        nextFromCrop.addEventListener("click", () => {
            document.getElementById("cropHidden").value = cropInput.value;
            showStep(2);
        });
    }

    // -----------------------------
    // Step 2 → Land Size & Water Type
    // -----------------------------
    const acresRange = document.getElementById("acresRange");
    const acresValue = document.getElementById("acresValue");
    const waterTypeChips = document.querySelectorAll(".chip");
    const waterTypeInput = document.getElementById("waterTypeInput");

    const nextFromSize = document.getElementById("nextFromSize");
    const nextFromIrrigation = document.getElementById("nextFromIrrigation");
    const districtInput = document.getElementById("districtInput");

    acresRange?.addEventListener("input", () => {
        acresValue.textContent = `${acresRange.value} Acres`;
        nextFromSize.disabled = false;
    });

    waterTypeChips.forEach(chip => {
        chip.addEventListener("click", () => {
            waterTypeChips.forEach(c => c.classList.remove("active"));
            chip.classList.add("active");

            waterTypeInput.value = chip.dataset.waterType;
            nextFromIrrigation.disabled = false;
        });
    });

    nextFromSize?.addEventListener("click", () => {
        document.getElementById("acresHidden").value = acresRange.value;
        showStep(3);
    });

    nextFromIrrigation?.addEventListener("click", () => {
        document.getElementById("districtHidden").value = districtInput.value;
        document.getElementById("waterTypeHidden").value = waterTypeInput.value;
        showStep(3);
    });

    // -----------------------------
    // Step 3 → Harvest timing
    // -----------------------------
    const nextFromHarvest = document.getElementById("nextFromHarvest");

    nextFromHarvest?.addEventListener("click", () => {
        const m = document.getElementById("harvestMonth").value;
        const y = document.getElementById("harvestYear").value;

        document.getElementById("harvestHidden").value = `${m} ${y}`;
        showStep(4);
    });

    // -----------------------------
    // Step 4 → Soil selection
    // -----------------------------
    const soilCards = document.querySelectorAll(".soil-card");
    const soilInput = document.getElementById("soilInput");
    const doneBtn = document.getElementById("doneBtn");

    soilCards.forEach(card => {
        card.addEventListener("click", () => {
            soilCards.forEach(c => c.classList.remove("selected"));
            card.classList.add("selected");

            soilInput.value = card.dataset.soil;
            doneBtn.disabled = false;
        });
    });

    doneBtn?.addEventListener("click", () => {
        showStep(6);

        setTimeout(() => {
            document.getElementById("onboardHiddenForm").submit();
        }, 1500);
    });

});
