const scanButton = document.getElementById("scanButton");
const targetInput = document.getElementById("target");
const message = document.getElementById("message");
const results = document.getElementById("results");
const summary = document.getElementById("summary");

scanButton.addEventListener("click", async () => {

    message.textContent = "";
    message.className = "";
    results.innerHTML = "";

    const target = targetInput.value.trim();

    const ports = [
        ...document.querySelectorAll(
            ".port-item input:checked"
        )
    ].map(input => input.value);

    if (!target) {
        message.textContent = "Please enter a target.";
        message.className = "error";
        return;
    }

    if (ports.length === 0) {
        message.textContent = "Select at least one port.";
        message.className = "error";
        return;
    }

    scanButton.disabled = true;
    scanButton.textContent = "Scanning...";
    summary.textContent = "Scanning...";

    try {

        const response = await fetch("/api/scan", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                target: target,
                ports: ports
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "Scan failed."
            );
        }

        const openPorts = data.results.filter(
            item => item.status === "open"
        ).length;

        summary.textContent =
            `${openPorts} open / ${data.results.length} checked`;

        data.results.forEach(item => {

            const row = document.createElement("div");

            row.className = "result";

            row.innerHTML = `
                <span>
                    <strong>${item.port}</strong>
                    — ${item.service}
                </span>

                <span class="${item.status}">
                    ${item.status.toUpperCase()}
                </span>
            `;

            results.appendChild(row);
        });

    } catch (error) {

        message.textContent = error.message;
        message.className = "error";
        summary.textContent = "Scan failed.";

    } finally {

        scanButton.disabled = false;
        scanButton.textContent = "Start Port Scan";
    }
});
