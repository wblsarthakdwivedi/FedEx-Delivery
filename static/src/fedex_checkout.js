/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { Checkout } from "@website_sale/interactions/checkout";

export class FedExCheckout extends Checkout {

    _toggleCheckoutButton(enable) {
        const button = document.querySelector(
            'a[name="website_sale_main_button"]'
        );

        if (!button) {
            return;
        }


        console.log("CLICKEDDDDDDDDDD")

        if (enable) {
            button.classList.remove("disabled");
            button.style.pointerEvents = "";
            button.removeAttribute("aria-disabled");
        } else {
            button.classList.add("disabled");
            button.style.pointerEvents = "none";
            button.setAttribute("aria-disabled", "true");
        }
    }

    _showAlert(message) {

        let alertBox = document.querySelector("#fedex_alert");

        if (!alertBox) {

            alertBox = document.createElement("div");
            alertBox.id = "fedex_alert";
            alertBox.className = "alert alert-warning mt-2";

            const container =
                document.querySelector(".oe_website_sale") || document.body;

            container.prepend(alertBox);
        }

        alertBox.innerHTML = message;

        clearTimeout(this._alertTimeout);

        this._alertTimeout = setTimeout(() => {
            alertBox.remove();
        }, 3000);
    }

    async selectDeliveryMethod(ev) {

        const radio = ev.currentTarget;

        const carrierId = parseInt(radio.dataset.dmId);
        const deliveryType = radio.dataset.deliveryType;

        const methodLi = radio.closest("li");
        const container = methodLi.querySelector(".fedex_rates_container");

        if (!container) {
            return;
        }

        // Normal carriers
        if (deliveryType !== "fedex") {
            this._toggleCheckoutButton(true);
            return super.selectDeliveryMethod(...arguments);
        }

        // Disable checkout until a service is selected
        this._toggleCheckoutButton(false);




        container.innerHTML = `
            <div class="text-center py-3">
                <span class="spinner-border spinner-border-sm me-2"></span>
                Loading FedEx rates...
            </div>
        `;

        try {

            const rates = await rpc("/fedex/rates", {
                carrier_id: carrierId,
            });

            console.log("carrierId",carrierId)

            if (!rates.length) {

                container.innerHTML = `
                    <div class="alert alert-warning mb-0">
                        No FedEx services available.
                    </div>
                `;
                return;
            }

            let html = '<div class="mt-2">';

            rates.forEach(rate => {

                html += `
                    <div class="d-flex justify-content-between align-items-center
                                border rounded px-3 py-2 mb-2 fedex-rate-card"
                         data-service-code="${rate.service_code}"
                         style="cursor:pointer;">

                        <div>

                            <strong>${rate.service_name}</strong>

                            ${rate.delivery_days ?
                                `<br>
                                 <small class="text-muted">
                                     ${rate.delivery_days} Business Day(s)
                                 </small>` : ""
                            }

                        </div>

                        <div>

                            <strong>${rate.currency} ${rate.amount}</strong>

                        </div>

                    </div>
                `;
            });

            html += "</div>";

            container.innerHTML = html;

            const deliveryMethodRadio = document.querySelector(
                `input[data-dm-id="${carrierId}"]`
            );

            container.querySelectorAll(".fedex-rate-card").forEach(card => {

                card.addEventListener("click", async () => {

                    try {

                        const result = await rpc("/fedex/select_rate", {

                            carrier_id: carrierId,
                            service_code: card.dataset.serviceCode,

                        });

                        if (!result.success) {

                            this._showAlert(
                                result.message ||
                                "Unable to select FedEx service."
                            );

                            return;
                        }

                        this._updateAmountBadge(
                            deliveryMethodRadio,
                            result
                        );

                        this._updateCartSummaries(result);

                        container.querySelectorAll(".fedex-rate-card")
                            .forEach(el => {

                                el.classList.remove(
                                    "border-primary",
                                    "bg-light"
                                );

                            });

                        card.classList.add(
                            "border-primary",
                            "bg-light"
                        );

                        this._toggleCheckoutButton(true);

                    } catch (error) {

                        console.error(error);

                        this._showAlert(
                            "Unable to select FedEx service."
                        );
                    }

                });

            });

        } catch (error) {

            console.error(error);

            container.innerHTML = `
                <div class="alert alert-danger mb-0">
                    Failed to load FedEx shipping rates.
                </div>
            `;
        }
    }

    _updateAmountBadge(radio, rateData) {

        if (radio.dataset.deliveryType !== "fedex") {
            return super._updateAmountBadge(...arguments);
        }

        const badge = this._getDeliveryPriceBadge(radio);

        if (rateData.success) {
            badge.innerHTML = rateData.amount_delivery;
        } else {
            badge.textContent = "Select Shipping Service";
        }

        this._toggleDeliveryMethodRadio(radio);
    }
}

registry
    .category("public.interactions")
    .add("fedex_checkout", FedExCheckout);