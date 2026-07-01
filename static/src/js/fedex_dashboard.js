/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS, loadCSS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";

export class FedexDashboard extends Component {
    static template = "wbl_fedex_delivery.fedexDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            kpis: {
                total_shipments: 0,
                today_shipments: 0,
                labels_created: 0,
                delivered_shipments: 0,
                stats: {
                    total_charges: 0.00,
                    avg_cost: 0.00,
                    highest_cost: 0.00,
                    lowest_cost: 0.00,
                }
            },
            carrier_performance: [],
            latest_shipments: [],
            latest_labels: [],
            activities: [],
            status_chart_data: [],
            chart_data: [],
            delivery_carriers: [],
            map_data: [],
            gauges: {
                total: { value: 0, max: 100, percent: 0 },
                active: { value: 0, max: 100, percent: 0 },
                labels: { value: 0, max: 100, percent: 0 },
                today: { value: 0, max: 100, percent: 0 }
            },
            
            // UI state
            dateRange: "all",
            searchQuery: "",
            loading: true,
            activeTab: "dashboard", // 'dashboard', 'carriers', 'shipments', 'labels'
            is_empty: true,
            selectedMapLoc: null,
            showKeys: {},
            
            // Rates Calculator State
            ratesInput: {
                selected_order_id: null,
            },
            saleOrdersList: [],
            ratesList: [],
            ratesLoading: false,
            ratesError: null,
            packagesList: [],
            shipmentsList: [],
            filteredShipments: [],
            uniqueShipmentCountries: [],
            shipmentsFilterCountry: "all",
        });

        this.trendChartRef = useRef("trendChart");
        this.statusPieChartRef = useRef("statusPieChart");
        this.mapRef = useRef("leafletMap");

        this.trendChart = null;
        this.statusPieChart = null;
        this.map = null;
        this.refreshInterval = null;

        onWillStart(async () => {
            // Load Chart.js and Leaflet resources
            await Promise.all([
                loadJS("/web/static/lib/Chart/Chart.js"),
                loadJS("/wbl_fedex_delivery/static/lib/leaflet/leaflet.js"),
                loadCSS("/wbl_fedex_delivery/static/lib/leaflet/leaflet.css")
            ]).catch(err => {
                console.error("Failed to load dashboard resources", err);
            });
            await this.loadAllData();
        });

        onMounted(() => {
            this.renderCharts();
            this.initMap();
            // Start Auto refresh every 45 seconds
            this.refreshInterval = setInterval(() => {
                this.loadAllData(true); 
            }, 45000);
        });

        onWillUnmount(() => {
            this.destroyCharts();
            if (this.map) {
                this.map.remove();
                this.map = null;
            }
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
        });
    }

    async loadAllData(silent = false) {
        if (!silent) {
            this.state.loading = true;
        }

        try {
            // Fetch KPIs and performance
            const kpiData = await rpc("/dashboard/kpi", {
                date_range: this.state.dateRange,
                search_query: this.state.searchQuery,
            });
            
            // Fetch Trend Chart
            const chartData = await rpc("/dashboard/chart", {
                date_range: this.state.dateRange,
                search_query: this.state.searchQuery,
            });

            // Fetch latest shipments
            const latestShipments = await rpc("/dashboard/latest_shipments", {
                date_range: this.state.dateRange,
                search_query: this.state.searchQuery,
            });

            // Fetch latest labels
            const latestLabels = await rpc("/dashboard/latest_labels", {
                search_query: this.state.searchQuery,
            });

            // Fetch activities
            const activities = await rpc("/dashboard/activity", {
                search_query: this.state.searchQuery,
            });

            // Fetch status chart
            const statusChartData = await rpc("/dashboard/status_chart", {
                date_range: this.state.dateRange,
                search_query: this.state.searchQuery,
            });

            // Update state
            this.state.kpis = kpiData.kpis;
            this.state.carrier_performance = kpiData.carrier_performance;
            this.state.delivery_carriers = kpiData.delivery_carriers;
            this.state.map_data = kpiData.map_data || [];
            
            // Compute gauge values
            const total = kpiData.kpis.total_shipments || 0;
            const active = kpiData.kpis.delivered_shipments || 0;
            const labels = kpiData.kpis.labels_created || 0;
            const today = kpiData.kpis.today_shipments || 0;
            
            this.state.gauges = {
                total: {
                    value: total,
                    max: Math.max(total, 50),
                    percent: total > 0 ? 0.75 : 0
                },
                active: {
                    value: active,
                    max: total || 1,
                    percent: total > 0 ? (active / total) : 0
                },
                labels: {
                    value: labels,
                    max: Math.max(total, labels) || 1,
                    percent: Math.max(total, labels) > 0 ? (labels / Math.max(total, labels)) : 0
                },
                today: {
                    value: today,
                    max: active || 1,
                    percent: active > 0 ? Math.min(today / active, 1) : 0
                }
            };

            this.state.latest_shipments = latestShipments;
            this.state.latest_labels = latestLabels;
            this.state.activities = activities;
            this.state.status_chart_data = statusChartData;
            this.state.chart_data = chartData;
            this.state.is_empty = kpiData.is_empty;

        } catch (error) {
            console.error("Error loading FedEx Dashboard data:", error);
        } finally {
            this.state.loading = false;
        }

        // Wait 50ms for OWL to patch the DOM before drawing canvas charts or leaflet maps
        await new Promise(resolve => setTimeout(resolve, 50));
        this.renderCharts();
        this.initMap();
    }

    async triggerManualRefresh() {
        await this.loadAllData();
        this.notification.add("Dashboard data refreshed.", {
            type: "success",
            sticky: false,
        });
    }

    async changeDateRange(range) {
        this.state.dateRange = range;
        await this.loadAllData();
    }

    async onSearchInput(ev) {
        this.state.searchQuery = ev.target.value || "";
        await this.loadAllData(true); 
    }

    async onSearchClear() {
        this.state.searchQuery = "";
        await this.loadAllData();
    }

    switchTab(tabName) {
        this.state.activeTab = tabName;
        if (tabName === 'dashboard') {
            setTimeout(() => {
                this.renderCharts();
                this.initMap();
            }, 100);
        }
    }

    // Action clicks on KPI cards
    openFilteredShipments(stateFilter) {
        if (stateFilter === 'labels') {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                name: "FedEx Labels",
                res_model: "fedex.label",
                views: [[false, "list"], [false, "form"]],
                domain: [],
                target: "current",
            });
            return;
        }

        let domain = [];
        let name = "FedEx Shipments";
        if (stateFilter === 'today') {
            const today = new Date().toISOString().slice(0, 10);
            domain = [["create_date", ">=", today + " 00:00:00"]];
            name = "Today's FedEx Shipments";
        } else if (stateFilter === 'shipped') {
            domain = [["state", "=", "shipped"]];
            name = "Delivered FedEx Shipments";
        }

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: "fedex.shipping",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }

    // Quick Actions
    openCreateShipment() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "New Shipment",
            res_model: "fedex.shipping",
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openShipmentsMenu() {
        this.switchTab('shipments');
        await this.loadAllShipments();
    }

    async loadAllShipments() {
        this.state.loading = true;
        try {
            const shps = await rpc("/dashboard/get_all_shipments");
            this.state.shipmentsList = shps || [];
            
            // Extract unique countries
            const countries = this.state.shipmentsList.map(s => s.country).filter(Boolean);
            this.state.uniqueShipmentCountries = [...new Set(countries)].sort();
            
            this.updateFilteredShipments();
        } catch (error) {
            console.error("Failed to load shipments", error);
        } finally {
            this.state.loading = false;
        }
    }

    updateFilteredShipments() {
        let list = this.state.shipmentsList;
        if (this.state.shipmentsFilterCountry !== "all") {
            list = list.filter(s => s.country === this.state.shipmentsFilterCountry);
        }
        if (this.state.searchQuery) {
            const query = this.state.searchQuery.toLowerCase();
            list = list.filter(s => 
                s.name.toLowerCase().includes(query) || 
                (s.customer && s.customer.toLowerCase().includes(query)) || 
                (s.tracking_number && s.tracking_number.toLowerCase().includes(query))
            );
        }
        this.state.filteredShipments = list;
    }

    onShipmentSearch(ev) {
        this.state.searchQuery = ev.target.value || "";
        this.updateFilteredShipments();
    }

    onShipmentCountryChange(ev) {
        this.state.shipmentsFilterCountry = ev.target.value || "all";
        this.updateFilteredShipments();
    }

    openLabelsMenu() {
        this.actionService.doAction("wbl_fedex_delivery.action_fedex_labels");
    }

    async openRatesMenu() {
        this.switchTab('rates');
        await this.loadSaleOrders();
    }

    async loadSaleOrders() {
        this.state.ratesLoading = true;
        this.state.ratesError = null;
        try {
            const orders = await rpc("/dashboard/get_sale_orders");
            this.state.saleOrdersList = orders || [];
            if (orders && orders.length > 0) {
                await this.selectSaleOrder(orders[0].id);
            } else {
                this.state.ratesInput.selected_order_id = null;
                this.state.ratesList = [];
            }
        } catch (error) {
            console.error("Failed to load sale orders", error);
            this.state.ratesError = "Failed to load sale orders.";
        } finally {
            this.state.ratesLoading = false;
        }
    }

    async selectSaleOrder(orderId) {
        this.state.ratesInput.selected_order_id = orderId;
        this.state.ratesLoading = true;
        this.state.ratesError = null;
        this.state.ratesList = [];
        try {
            const result = await rpc("/dashboard/get_rates_for_order", {
                order_id: orderId,
            });
            if (result.success) {
                this.state.ratesList = result.rates;
            } else {
                this.state.ratesError = result.error;
            }
        } catch (error) {
            this.state.ratesError = "An unexpected error occurred while fetching rates.";
            console.error("Failed to fetch rates for order", error);
        } finally {
            this.state.ratesLoading = false;
        }
    }

    async selectRate(rate) {
        if (!this.state.ratesInput.selected_order_id) return;
        this.state.ratesLoading = true;
        try {
            const result = await rpc("/dashboard/select_rate_for_order", {
                order_id: this.state.ratesInput.selected_order_id,
                service_code: rate.service_code,
                service_name: rate.service_name,
                amount: rate.amount,
            });
            if (result.success) {
                const orders = await rpc("/dashboard/get_sale_orders");
                this.state.saleOrdersList = orders || [];
            } else {
                this.state.ratesError = result.error;
            }
        } catch (error) {
            console.error("Failed to select rate", error);
        } finally {
            this.state.ratesLoading = false;
        }
    }

    async openPickupsMenu() {
        this.switchTab('packages');
        await this.loadPackages();
    }

    async loadPackages() {
        this.state.loading = true;
        try {
            const pkgs = await rpc("/dashboard/get_packages");
            this.state.packagesList = pkgs || [];
        } catch (error) {
            console.error("Failed to load packages", error);
        } finally {
            this.state.loading = false;
        }
    }

    openManagePackages() {
        this.actionService.doAction("wbl_fedex_delivery.action_stock_package_type");
    }

    openAccountsMenu() {
        this.switchTab('accounts');
    }

    openSettingsMenu() {
        this.actionService.doAction("delivery.action_delivery_carrier_form");
    }

    toggleKeyVisibility(key) {
        this.state.showKeys[key] = !this.state.showKeys[key];
    }

    openRecord(model, id) {
        if (!id) return;
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openPDF(attachmentId) {
        if (!attachmentId) {
            this.notification.add("No PDF attachment found.", { type: "warning" });
            return;
        }
        window.open(`/web/content/${attachmentId}?download=false`, "_blank");
    }

    selectMapLocation(loc) {
        if (this.state.selectedMapLoc && this.state.selectedMapLoc.country === loc.country) {
            this.state.selectedMapLoc = null;
        } else {
            this.state.selectedMapLoc = loc;
        }
    }

    closeMapTooltip() {
        this.state.selectedMapLoc = null;
    }



    // Export CSV
    exportCSV() {
        const list = this.state.latest_shipments || [];
        if (!list.length) return;

        const headers = ["Tracking Number", "Customer", "Carrier", "Service", "Shipping Cost", "Status", "Date"];
        const rows = list.map(s => [
            s.tracking_number,
            s.customer,
            s.carrier,
            s.service_name,
            s.shipping_charge,
            s.state,
            s.create_date
        ]);

        const csvContent = "data:text/csv;charset=utf-8,\uFEFF"
            + [headers.join(","), ...rows.map(e => e.map(val => `"${String(val).replace(/"/g, '""')}"`).join(","))].join("\n");

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `fedex_shipments_${new Date().toISOString().slice(0, 10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // Chart.js Rendering
    destroyCharts() {
        if (this.trendChart) this.trendChart.destroy();
        if (this.statusPieChart) this.statusPieChart.destroy();
        this.trendChart = null;
        this.statusPieChart = null;
    }

    async renderCharts() {
        this.destroyCharts();

        if (typeof Chart === "undefined" || this.state.is_empty) {
            return;
        }

        const fedexPurple = "#4D148C";
        const fedexOrange = "#FF6200";
        const textDark = "#1c1c1e";

        // 1. Line Chart (Shipment Trend)
        const trendEl = this.trendChartRef.el;
        if (trendEl) {
            const labels = (this.state.chart_data || []).map(d => d.date);
            const data = (this.state.chart_data || []).map(d => d.count);

            this.trendChart = new Chart(trendEl, {
                type: "line",
                data: {
                    labels: labels,
                    datasets: [{
                        label: "Shipments",
                        data: data,
                        borderColor: fedexPurple,
                        backgroundColor: "rgba(77, 20, 140, 0.05)",
                        fill: true,
                        tension: 0.3,
                        borderWidth: 3,
                        pointBackgroundColor: fedexOrange,
                        pointBorderColor: "#FFFFFF",
                        pointRadius: 5,
                        pointHoverRadius: 7,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { color: "#8e8e93", font: { family: "Inter, sans-serif", size: 10 } }
                        },
                        y: {
                            grid: { color: "rgba(0, 0, 0, 0.05)" },
                            ticks: { 
                                stepSize: 1,
                                color: "#8e8e93", 
                                font: { family: "Inter, sans-serif", size: 10 } 
                            }
                        }
                    },
                    onClick: (evt, element) => {
                        if (element.length > 0) {
                            const index = element[0].index;
                            const date = labels[index];
                            this.actionService.doAction({
                                type: "ir.actions.act_window",
                                name: `Shipments on ${date}`,
                                res_model: "fedex.shipping",
                                views: [[false, "list"], [false, "form"]],
                                domain: [["create_date", ">=", date + " 00:00:00"], ["create_date", "<=", date + " 23:59:59"]],
                                target: "current",
                            });
                        }
                    }
                }
            });
        }

        // 2. Pie Chart (Shipment Status)
        const pieEl = this.statusPieChartRef.el;
        if (pieEl) {
            const statusLabels = (this.state.status_chart_data || []).map(d => d.status);
            const statusData = (this.state.status_chart_data || []).map(d => d.count);

            this.statusPieChart = new Chart(pieEl, {
                type: "pie",
                data: {
                    labels: statusLabels,
                    datasets: [{
                        data: statusData,
                        backgroundColor: [
                            "rgba(142, 142, 147, 0.85)", // Draft (Gray)
                            "rgba(77, 20, 140, 0.85)",  // Shipped (FedEx Purple)
                            "rgba(255, 98, 0, 0.85)", // Cancelled (FedEx Orange)
                        ],
                        hoverBackgroundColor: [
                            "#8e8e93",
                            fedexPurple,
                            fedexOrange,
                        ],
                        borderWidth: 2,
                        borderColor: "#FFFFFF"
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: {
                                color: textDark,
                                font: { family: "Inter, sans-serif", size: 11 }
                            }
                        }
                    },
                    onClick: (evt, element) => {
                        if (element.length > 0) {
                            const index = element[0].index;
                            const statusLabel = statusLabels[index];
                            let stateVal = 'draft';
                            if (statusLabel === 'Shipped') stateVal = 'shipped';
                            else if (statusLabel === 'Cancelled') stateVal = 'cancel';

                            this.actionService.doAction({
                                type: "ir.actions.act_window",
                                name: `${statusLabel} Shipments`,
                                res_model: "fedex.shipping",
                                views: [[false, "list"], [false, "form"]],
                                domain: [["state", "=", stateVal]],
                                target: "current",
                            });
                        }
                    }
                }
            });
        }
    }

    // ------------------------------------------------------
    // LEAFLET MAP DRAWING
    // ------------------------------------------------------
    initMap() {
        if (typeof L === "undefined") {
            return;
        }

        const container = this.mapRef.el;
        if (!container) return;

        try {
            // Destroy and recreate the map if container changed
            if (this.map && this.map.getContainer() !== container) {
                this.map.remove();
                this.map = null;
            }
            if (!this.map) {
                this.map = L.map(container, {
                    zoomControl: true,
                    attributionControl: false,
                    zoomAnimation: true,
                }).setView([20, 0], 2); // Center globally

                // Use CartoDB Positron Light minimalist tiles
                L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
                    maxZoom: 18,
                }).addTo(this.map);
            }

            // Clear old markers if any
            this.map.eachLayer((layer) => {
                if (layer instanceof L.Marker) {
                    this.map.removeLayer(layer);
                }
            });

            const mapData = this.state.map_data || [];
            mapData.forEach((loc) => {
                const isDomestic = loc.country === 'United States' || loc.country === 'Canada' || loc.country === 'Brazil';
                
                const truckHtml = `
                    <div class="leaflet-marker-truck-icon" style="transform: scale(0.85); cursor: pointer;">
                        <svg viewBox="0 0 36 28" width="36" height="28">
                            <rect x="0" y="0" width="36" height="20" rx="3" fill="#4D148C" />
                            <rect x="26" y="4" width="10" height="9" rx="1" fill="#FF6200" />
                            <circle cx="8" cy="20" r="4" fill="#1c1c1e" />
                            <circle cx="28" cy="20" r="4" fill="#1c1c1e" />
                            <text x="3" y="13" fill="#ffffff" font-size="9" font-weight="bold" font-family="Arial">Fed</text>
                            <text x="18" y="13" fill="#FF6200" font-size="9" font-weight="bold" font-family="Arial">Ex</text>
                        </svg>
                    </div>
                `;

                const planeHtml = `
                    <div class="leaflet-marker-plane-icon" style="transform: scale(0.85); cursor: pointer;">
                        <svg viewBox="0 0 36 36" width="36" height="36">
                            <circle cx="18" cy="18" r="16" fill="#ffffff" stroke="#4D148C" stroke-width="1.5" />
                            <path d="M18,6 L15,16 L5,18 L15,20 L18,29 L21,20 L31,18 L21,16 Z" fill="#4D148C" />
                            <circle cx="18" cy="18" r="2.5" fill="#FF6200" />
                        </svg>
                    </div>
                `;

                const truckIcon = L.divIcon({
                    html: truckHtml,
                    className: 'custom-fedex-truck-marker',
                    iconSize: [36, 28],
                    iconAnchor: [18, 14]
                });

                const planeIcon = L.divIcon({
                    html: planeHtml,
                    className: 'custom-fedex-plane-marker',
                    iconSize: [36, 36],
                    iconAnchor: [18, 18]
                });

                const popupContent = `
                    <div class="map-tooltip" style="min-width: 160px;">
                        <div class="d-flex justify-content-between align-items-center mb-1 pb-1 border-bottom" style="border-color: rgba(77,20,140,0.15) !important;">
                            <span class="tooltip-title fw-bold" style="color: #4D148C; font-size: 0.85rem; font-family: sans-serif;">${loc.order_name}</span>
                        </div>
                        <div class="tooltip-info small text-muted" style="font-size: 0.78rem; font-family: sans-serif;">Account: <span class="fw-semibold text-dark">${loc.account}</span></div>
                        <div class="tooltip-info small text-muted" style="font-size: 0.78rem; font-family: sans-serif; margin-top: 3px;">Balance: <span class="fw-semibold text-dark">${loc.balance}</span></div>
                    </div>
                `;

                L.marker([loc.lat, loc.lng], { icon: isDomestic ? truckIcon : planeIcon })
                    .addTo(this.map)
                    .bindPopup(popupContent, {
                        closeButton: true,
                        offset: L.point(0, -10),
                        className: 'fedex-leaflet-popup'
                    });
            });

        } catch (e) {
            console.error("Failed to initialize Leaflet Map:", e);
        }
    }
}

registry.category("actions").add("fedex_dashboard", FedexDashboard);
