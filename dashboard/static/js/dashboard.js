/* dashboard.js - Real-time client-side scripting for National Power Grid Monitor */

// Global Chart References
let charts = {};

// Default color palette used when station IDs are discovered dynamically
const defaultPalette = [
    { border: "#3b82f6", bg: "rgba(59, 130, 246, 0.1)" },
    { border: "#10b981", bg: "rgba(16, 185, 129, 0.1)" },
    { border: "#f59e0b", bg: "rgba(245, 158, 11, 0.1)" },
    { border: "#8b5cf6", bg: "rgba(139, 92, 246, 0.1)" },
    { border: "#ec4899", bg: "rgba(236, 72, 153, 0.1)" },
    { border: "#06b6d4", bg: "rgba(6, 182, 212, 0.08)" },
    { border: "#f97316", bg: "rgba(249, 115, 22, 0.08)" }
];

// Helper: deterministically pick a color for a station id
function colorForStation(stationId, index) {
    // Simple rotation through palette for predictable but distinct colors
    const pick = defaultPalette[index % defaultPalette.length];
    return pick;
}

// Main Entry Point
document.addEventListener("DOMContentLoaded", () => {
    const view = window.DASHBOARD_VIEW;
    
    if (view === "dashboard") {
        initOverviewDashboard();
    } else if (view === "station_details") {
        initStationDetails();
    }
});

// Helper to format ISO timestamp to readable GMT+1 locale format
function formatTime(isoString) {
    if (!isoString && isoString !== 0) {
        return "";
    }

    const raw = typeof isoString === "string" ? isoString.trim() : String(isoString);
    const normalized = raw
        .replace(/ /g, "T")
        .replace(/(\+00:00)?Z?$/, "Z")
        .replace(/\+00:00Z$/, "Z");
    const date = new Date(normalized);

    if (Number.isNaN(date.valueOf())) {
        // Fall back to the raw value instead of showing Invalid Date
        return raw;
    }

    return date.toLocaleTimeString('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
}

// Helper to construct a semantic status HTML badge
function getStatusBadge(status) {
    if (status === "NORMAL") return `<span class="badge badge-healthy"><i class="fa-solid fa-circle-check me-1"></i>NORMAL</span>`;
    // Multiple faults = critical (comma-separated), single fault = warning
    if (status && status.includes(",")) return `<span class="badge badge-critical"><i class="fa-solid fa-circle-exclamation me-1"></i>${status}</span>`;
    return `<span class="badge badge-warning"><i class="fa-solid fa-triangle-exclamation me-1"></i>${status || 'Warning'}</span>`;
}

// ============================================================================
// 1. OVERVIEW DASHBOARD ROUTINES
// ============================================================================

const KNOWN_STATION_IDS = ['PS001', 'PS002', 'PS003', 'PS004', 'PS005'];

function initOverviewDashboard() {
    // Build charts dynamically based on stations returned by the API.
    // This prevents mismatches when new stations are added or removed.
    fetch('/api/grid_status')
        .then(r => r.json())
        .then(status => {
            // Detect station IDs from the latest_readings map returned by the API
            let stationIds = Object.keys(status.latest_readings || {});
            stationIds = stationIds.filter(id => KNOWN_STATION_IDS.includes(id));
            if (stationIds.length === 0) {
                // Fallback to a small default set if API returned no stations
                stationIds = KNOWN_STATION_IDS.slice();
            }

            const chartConfigs = ["voltage", "current", "frequency", "temperature", "load"];

            chartConfigs.forEach(metric => {
                const ctx = document.getElementById(`chart-${metric}`).getContext('2d');

                const datasets = stationIds.map((stationId, idx) => {
                    const col = colorForStation(stationId, idx);
                    return {
                        label: stationId,
                        borderColor: col.border,
                        backgroundColor: col.bg,
                        data: [],
                        fill: false,
                        tension: 0.2,
                        borderWidth: 2,
                        pointRadius: 2
                    };
                });

                charts[metric] = new Chart(ctx, {
                    type: 'line',
                    data: { labels: [], datasets: datasets },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { display: true, grid: { display: false } },
                            y: { display: true, grid: { color: "#e2e8f0" } }
                        },
                        plugins: { legend: { position: 'top', labels: { boxWidth: 10, font: { size: 10 } } } }
                    }
                });
            });

            // Start periodic updates after charts are initialized
            updateOverviewData();
            setInterval(updateOverviewData, 5000);
        })
        .catch(err => {
            console.error('Failed to detect station IDs from API:', err);
            // Fallback: create charts with the default palette labels
            const fallbackIds = ['PS001','PS002','PS003','PS004','PS005'];
            const chartConfigs = ["voltage", "current", "frequency", "temperature", "load"];
            chartConfigs.forEach(metric => {
                const ctx = document.getElementById(`chart-${metric}`).getContext('2d');
                const datasets = fallbackIds.map((sid, idx) => {
                    const col = colorForStation(sid, idx);
                    return { label: sid, borderColor: col.border, backgroundColor: col.bg, data: [], fill: false, tension: 0.2, borderWidth: 2, pointRadius: 2 };
                });
                charts[metric] = new Chart(ctx, { type: 'line', data: { labels: [], datasets }, options: { responsive:true, maintainAspectRatio:false } });
            });
            updateOverviewData();
            setInterval(updateOverviewData, 5000);
        });
}

function updateOverviewData() {
    // A. Update Top Metrics Cards and Quicklist
    fetch('/api/grid_status')
        .then(response => response.json())
        .then(status => {
            console.debug('GRID_STATUS', status);
            document.getElementById("stat-total").innerText = status.total_stations;
            document.getElementById("stat-healthy").innerText = status.healthy;
            document.getElementById("stat-warning").innerText = status.warning;
            document.getElementById("stat-critical").innerText = status.critical;
            
            // Populate quicklist of stations on the side
            const quicklist = document.getElementById("stations-quicklist");
            quicklist.innerHTML = "";
            // Prefer the station list currently used to build the charts (if initialized)
            const stationIds = (charts && charts['voltage'] && charts['voltage'].data && charts['voltage'].data.datasets)
                ? charts['voltage'].data.datasets.map(d => d.label)
                : Object.keys(status.latest_readings || {});

            stationIds.forEach(sid => {
                const read = status.latest_readings ? status.latest_readings[sid] : null;
                const activeStatus = read ? read.status : "NORMAL";
                const temp = read ? `${read.temperature}°C` : "N/A";
                const load = read ? `${read.load}%` : "N/A";

                const item = document.createElement("li");
                item.className = "list-group-item d-flex justify-content-between align-items-center py-3 border-0 border-bottom";
                item.innerHTML = `
                    <div>
                        <a href="/stations?station_id=${sid}" class="fw-bold text-decoration-none text-primary">${sid}</a>
                        <div class="small text-muted">Temp: ${temp} | Load: ${load}</div>
                    </div>
                    <div>${getStatusBadge(activeStatus)}</div>
                `;
                quicklist.appendChild(item);
            });
        })
        .catch(err => console.error("Error fetching grid status summary:", err));
    // B. Fetch Telemetry History and Redraw Charts
    // API now returns ascending order (oldest -> newest) for correct left-to-right rendering
    fetch('/api/telemetry?limit=50&order=asc')
        .then(response => response.json())
        .then(telemetryData => {
            // Group records by station ID (API already sorted ascending)
            const grouped = {};
            const stationIds = (charts && charts['voltage'] && charts['voltage'].data && charts['voltage'].data.datasets)
                ? charts['voltage'].data.datasets.map(d => d.label)
                : [];

            stationIds.forEach(sid => {
                grouped[sid] = telemetryData.filter(d => d.station_id === sid).slice(-10);
            });

            const metrics = ["voltage", "current", "frequency", "temperature", "load"];

            metrics.forEach(metric => {
                const chart = charts[metric];
                if (!chart) return;

                chart.data.datasets.forEach(dataset => {
                    const stationId = dataset.label;
                    const stationRecords = grouped[stationId] || [];
                    dataset.data = stationRecords.map(r => r[metric] || 0);
                });

                const maxStation = Object.keys(grouped).reduce((a, b) => {
                    const lenA = grouped[a] ? grouped[a].length : 0;
                    const lenB = grouped[b] ? grouped[b].length : 0;
                    return lenA >= lenB ? a : b;
                }, KNOWN_STATION_IDS[0]);

                chart.data.labels = (grouped[maxStation] || []).map(r => formatTime(r.timestamp));
                if (chart.data.labels.length === 0) {
                    chart.data.labels = Array.from({ length: 10 }, (_, i) => `T-${10-i}`);
                }

                chart.update('none');
            });
        })
        .catch(err => console.error("Error fetching telemetry logs:", err));;

    // C. Update Recent Alerts Table — reads from status field, not faults array
    fetch('/api/alerts?limit=10')
        .then(response => response.json())
        .then(alerts => {
            const tableBody = document.getElementById("table-alerts-body");
            tableBody.innerHTML = "";

            if (alerts.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center py-4 text-success fw-medium">
                            <i class="fa-solid fa-circle-check me-2"></i>No faults detected in the grid.
                        </td>
                    </tr>
                `;
                return;
            }

            alerts.forEach(alert => {
                // Build fault badges from the status string (e.g. "HIGH_VOLTAGE,OVERHEATING")
                const statusStr = alert.status || "FAULT";
                const faultList = statusStr.split(",").map(f => f.trim()).filter(f => f && f !== "NORMAL");
                const badgeClass = faultList.length > 1 ? "bg-danger" : "bg-warning text-dark";
                const badges = faultList.map(f => `<span class="badge ${badgeClass} me-1">${f}</span>`).join(" ");

                const row = document.createElement("tr");
                row.innerHTML = `
                    <td class="ps-4 fw-bold">${alert.station_id}</td>
                    <td class="text-secondary">${new Date(alert.timestamp).toLocaleString()}</td>
                    <td>${badges}</td>
                    <td class="text-end pe-4">
                        <a href="/stations?station_id=${alert.station_id}" class="btn btn-sm btn-outline-primary py-1">
                            <i class="fa-solid fa-magnifying-glass-chart"></i> View
                        </a>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(err => console.error("Error fetching active alerts list:", err));
}

// ============================================================================
// 2. SUBSTATION DETAILS ROUTINES
// ============================================================================

function initStationDetails() {
    const stationId = window.SELECTED_STATION_ID;
    
    // Setup listener on change select dropdown
    const select = document.getElementById("stationSelect");
    select.addEventListener("change", (e) => {
        window.location.href = `/stations?station_id=${e.target.value}`;
    });

    // Define rules threshold limits for chart horizontal line guides
    const limits = {
        voltage: { min: 210, max: 250 },
        current: { max: 400 },
        frequency: { min: 49, max: 51 },
        temperature: { max: 90 },
        load: { max: 95 }
    };

    // 1. Initialize Single Station Line Charts with Red Threshold Limit Lines
    const metrics = ["voltage", "current", "frequency", "temperature", "load"];
    
    metrics.forEach(metric => {
        const ctx = document.getElementById(`station-${metric}-chart`).getContext('2d');
        
        // Define threshold plugin annotations (or draw manually via custom standard charts)
        // To keep this readable and without adding extra plugins,
        // we can add extra helper threshold data datasets as dashed lines!
        const datasets = [
            {
                label: `${metric.toUpperCase()} Reading`,
                borderColor: "#1e3a8a",
                backgroundColor: "rgba(30, 58, 138, 0.05)",
                data: [],
                fill: true,
                tension: 0.3,
                borderWidth: 3,
                pointRadius: 4,
                z: 10
            }
        ];

        // Add visual indicator thresholds inside chart datasets
        const limit = limits[metric];
        if (limit) {
            if (limit.max !== undefined) {
                datasets.push({
                    label: "Max Threshold Limit",
                    borderColor: "rgba(239, 68, 68, 0.6)",
                    borderDash: [6, 6],
                    data: [],
                    fill: false,
                    pointRadius: 0,
                    borderWidth: 1.5
                });
            }
            if (limit.min !== undefined) {
                datasets.push({
                    label: "Min Threshold Limit",
                    borderColor: "rgba(239, 68, 68, 0.6)",
                    borderDash: [6, 6],
                    data: [],
                    fill: false,
                    pointRadius: 0,
                    borderWidth: 1.5
                });
            }
        }

        charts[metric] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { grid: { display: false } },
                    y: { grid: { color: "#f1f5f9" } }
                },
                plugins: {
                    legend: { display: true, labels: { boxWidth: 12 } }
                }
            }
        });
    });

    // 2. Fetch and timer
    updateStationDetailsData(stationId, limits);
    setInterval(() => updateStationDetailsData(stationId, limits), 5000);
}

function updateStationDetailsData(stationId, limits) {
    fetch(`/api/telemetry?station_id=${stationId}&limit=12&order=desc`)
        .then(response => response.json())
        .then(history => {
            if (history.length === 0) return;
            
            const latest = history[0]; // Latest element (index 0 because descending)
            const chronological = [...history].reverse(); // Revert to chronological
            const timestamps = chronological.map(d => formatTime(d.timestamp));

            // A. Update KPI cards text
            document.getElementById("kpi-voltage").innerText = latest.voltage;
            document.getElementById("kpi-current").innerText = latest.current;
            document.getElementById("kpi-frequency").innerText = latest.frequency;
            document.getElementById("kpi-temperature").innerText = latest.temperature;
            document.getElementById("kpi-load").innerText = latest.load;
            document.getElementById("kpi-time").innerText = `As of ${formatTime(latest.timestamp)}`;

            const kpiStatus = document.getElementById("kpi-status");
            kpiStatus.innerText = latest.status;

            // B. Apply warning/critical borders dynamically to KPI cards
            const statusCard = document.getElementById("kpi-status-card");
            statusCard.className = "card card-kpi text-center border-0 shadow-sm h-100 py-2";
            
            if (latest.status === "NORMAL") {
                kpiStatus.className = "h3 fw-bold text-success mb-1";
                statusCard.classList.add("kpi-healthy-glow");
            } else if (latest.status === "Warning") {
                kpiStatus.className = "h3 fw-bold text-warning mb-1";
                statusCard.classList.add("kpi-warning-glow");
            } else {
                kpiStatus.className = "h3 fw-bold text-danger mb-1";
                statusCard.classList.add("kpi-critical-glow");
            }

            // Simple coloring of individual card indicators if they violate their limits
            const checkCardGlow = (cardId, val, limit) => {
                const card = document.getElementById(cardId);
                card.className = "card card-kpi text-center border-0 shadow-sm h-100 py-2";
                if (limit) {
                    if ((limit.max !== undefined && val > limit.max) || (limit.min !== undefined && val < limit.min)) {
                        card.classList.add("kpi-critical-glow");
                    }
                }
            };

            checkCardGlow("kpi-voltage-card", latest.voltage, limits.voltage);
            checkCardGlow("kpi-current-card", latest.current, limits.current);
            checkCardGlow("kpi-frequency-card", latest.frequency, limits.frequency);
            checkCardGlow("kpi-temperature-card", latest.temperature, limits.temperature);
            checkCardGlow("kpi-load-card", latest.load, limits.load);

            // C. Update Charts
            const metrics = ["voltage", "current", "frequency", "temperature", "load"];
            
            metrics.forEach(metric => {
                const chart = charts[metric];
                if (!chart) return;

                // Update Labels
                chart.data.labels = timestamps;

                // Update reading data
                chart.data.datasets[0].data = chronological.map(d => d[metric]);

                // Update thresholds
                const limit = limits[metric];
                if (limit) {
                    if (limit.max !== undefined) {
                        chart.data.datasets[1].data = Array(timestamps.length).fill(limit.max);
                    }
                    if (limit.min !== undefined) {
                        const index = limit.max !== undefined ? 2 : 1;
                        chart.data.datasets[index].data = Array(timestamps.length).fill(limit.min);
                    }
                }

                chart.update('none');
            });
        })
        .catch(err => console.error("Error fetching station details telemetry:", err));
}

// ============================================================================
// 3. ALERT LOGS HISTORY ROUTINES
// ============================================================================

function initAlertHistory() {
    // Connect refresh button
    document.getElementById("btn-refresh-alerts").addEventListener("click", () => {
        updateAlertHistoryData();
    });

    updateAlertHistoryData();
}

function updateAlertHistoryData() {
    const tableBody = document.getElementById("table-full-history-body");
    tableBody.innerHTML = `
        <tr>
            <td colspan="4" class="text-center py-5 text-muted">
                <i class="fa-solid fa-spinner fa-spin fa-2x mb-3 d-block"></i>
                Reloading database records...
            </td>
        </tr>
    `;

    fetch('/api/alerts?limit=50')
        .then(response => response.json())
        .then(alerts => {
            tableBody.innerHTML = "";
            
            if (alerts.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center py-5 text-success fs-5">
                            <i class="fa-solid fa-circle-check d-block text-success fa-3x mb-3"></i>
                            No faults are logged in the historical database.
                        </td>
                    </tr>
                `;
                return;
            }

            alerts.forEach(alert => {
                // Style the fault alerts badge list
                const badges = alert.faults.map(f => {
                    let badgeClass = "bg-warning-subtle text-warning border-warning";
                    if (["OVER_CURRENT", "OVERHEATING", "OVERLOAD"].includes(f.trim())) {
                        badgeClass = "bg-danger-subtle text-danger border-danger";
                    }
                    return `<span class="badge border ${badgeClass} px-2.5 py-1.5 me-1.5">${f.trim()}</span>`;
                }).join(" ");

                const row = document.createElement("tr");
                row.innerHTML = `
                    <td class="ps-4 text-secondary fw-semibold">${new Date(alert.timestamp).toLocaleString()}</td>
                    <td class="fw-bold text-primary">${alert.station_id}</td>
                    <td>${badges}</td>
                    <td class="pe-4 text-end text-muted small">
                        <i class="fa-solid fa-server me-1"></i>Processed by Fog Node
                    </td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(err => {
            console.error("Error loading full alert logs:", err);
            tableBody.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center py-5 text-danger">
                        <i class="fa-solid fa-triangle-exclamation fa-2x mb-3 d-block"></i>
                        Failed to connect to database. Check server logs.
                    </td>
                </tr>
            `;
        });
}
