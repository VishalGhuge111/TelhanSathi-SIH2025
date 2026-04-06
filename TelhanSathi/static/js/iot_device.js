/**
 * Smart Garden IoT Device Manager
 * Frontend code for ESP32 sensor data monitoring
 * ESP32 sends data directly to /field-monitoring/api/push
 */

class IoTDeviceManager {
    constructor() {
        this.sensorData = null;
        this.refreshInterval = null;
        this.isLoading = false;
        this.refreshRate = 3000; // 3 seconds for real-time updates
        this.lastUpdateTime = null;
    }

    // Initialize device manager
    async init() {
        this.setupEventListeners();
        await this.fetchSensorData();
        this.startAutoRefresh();
    }

    // Setup event listeners
    setupEventListeners() {
        document.getElementById('refreshDataBtn')?.addEventListener('click', () => this.refreshData());
    }

    // Fetch latest sensor data from Flask API
    async fetchSensorData() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        try {
            const response = await fetch('/field-monitoring/api/readings', {
                credentials: 'same-origin'
            });

            if (!response.ok) {
                this.updateStatus('Failed to fetch sensor data', 'error');
                this.isLoading = false;
                return;
            }

            const data = await response.json();
            if (data.readings && data.readings.length > 0) {
                const latestReading = data.readings[0]; // Latest reading
                
                // Check if data has actually changed
                if (this.sensorData) {
                    const timestamp = new Date(latestReading.received_at).getTime();
                    const lastTimestamp = new Date(this.sensorData.received_at).getTime();
                    
                    if (timestamp === lastTimestamp) {
                        console.log('⏳ Waiting for new data...');
                        this.isLoading = false;
                        return; // No new data yet
                    }
                }
                
                this.sensorData = latestReading;
                this.lastUpdateTime = new Date().toLocaleTimeString();
                
                console.log('✓ New data received at', this.lastUpdateTime, latestReading);
                
                this.displaySensorData(this.sensorData, data.readings);
                this.updateStatus(`Data updated ✅ @ ${this.lastUpdateTime}`, 'success');
            } else {
                this.updateStatus('Waiting for sensor data from ESP32...', 'warning');
                console.log('⏳ No readings in database yet');
                this.clearDisplay();
            }
        } catch (error) {
            this.updateStatus('Connection error', 'error');
            console.error('❌ Fetch error:', error);
        } finally {
            this.isLoading = false;
        }
    }

    // Clear sensor display values
    clearDisplay() {
        const displayElements = {
            'tempValue': '--',
            'humValue': '--',
            'soilValue': '--',
            'lightValue': '--',
            'probeTempValue': '--',
            'lastUpdateTime': '--:--:--'
        };

        for (const [id, value] of Object.entries(displayElements)) {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = value;
            }
        }
    }

    // Display sensor data on dashboard
    displaySensorData(latest, allReadings) {
        if (!latest) return;
        
        // Update latest readings
        const displayElements = {
            'tempValue': `${(latest.temperature || 0).toFixed(1)}°C`,
            'humValue': `${(latest.humidity || 0).toFixed(1)}%`,
            'soilValue': `${(latest.soil_moisture || 0).toFixed(1)}%`,
            'lightValue': `${(latest.light || 0).toFixed(0)} Lux`,
            'probeTempValue': `${(latest.soil_temp || 0).toFixed(1)}°C`,
            'lastUpdateTime': latest.received_at ? new Date(latest.received_at).toLocaleTimeString() : '--:--:--'
        };

        for (const [id, value] of Object.entries(displayElements)) {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = value;
                // Pulse animation
                el.style.animation = 'none';
                setTimeout(() => el.style.animation = 'pulse 0.6s ease-in-out', 10);
            }
        }

        // Update charts if available
        if (window.sensorCharts && allReadings) {
            this.updateCharts(allReadings);
        }
    }

    // Update charts with all readings
    updateCharts(readings) {
        if (!readings || readings.length === 0) return;

        try {
            // Prepare data for charts (reverse to show oldest to newest)
            const reversedReadings = [...readings].reverse();
            const labels = reversedReadings.map((r, i) => {
                const time = new Date(r.received_at);
                return time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            });

            const tempData = reversedReadings.map(r => parseFloat(r.temperature) || 0);
            const humData = reversedReadings.map(r => parseFloat(r.humidity) || 0);
            const soilData = reversedReadings.map(r => parseFloat(r.soil_moisture) || 0);
            const lightData = reversedReadings.map(r => parseFloat(r.light) || 0);

            // Update each chart if it exists
            if (window.sensorCharts && window.sensorCharts.temperature) {
                window.sensorCharts.temperature.data.labels = labels;
                window.sensorCharts.temperature.data.datasets[0].data = tempData;
                window.sensorCharts.temperature.update('none');
            }

            if (window.sensorCharts && window.sensorCharts.humidity) {
                window.sensorCharts.humidity.data.labels = labels;
                window.sensorCharts.humidity.data.datasets[0].data = humData;
                window.sensorCharts.humidity.update('none');
            }

            if (window.sensorCharts && window.sensorCharts.soil) {
                window.sensorCharts.soil.data.labels = labels;
                window.sensorCharts.soil.data.datasets[0].data = soilData;
                window.sensorCharts.soil.update('none');
            }

            if (window.sensorCharts && window.sensorCharts.light) {
                window.sensorCharts.light.data.labels = labels;
                window.sensorCharts.light.data.datasets[0].data = lightData;
                window.sensorCharts.light.update('none');
            }
        } catch (error) {
            console.error('Chart update error:', error);
        }
    }

    // Refresh data manually
    async refreshData() {
        const btn = document.getElementById('refreshDataBtn');
        if (btn) {
            btn.disabled = true;
            btn.textContent = '⟳ Refreshing...';
        }

        await this.fetchSensorData();

        if (btn) {
            btn.disabled = false;
            btn.textContent = '⟳ Refresh Now';
        }
    }

    // Update status message
    updateStatus(message, type) {
        const statusEl = document.getElementById('deviceStatus');
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.className = `status status-${type || 'info'}`;
        }
    }

    // Show notification
    showNotification(message, type = 'info') {
        const notif = document.createElement('div');
        notif.className = `notification notification-${type}`;
        notif.textContent = message;
        document.body.appendChild(notif);

        setTimeout(() => {
            notif.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notif.remove(), 300);
        }, 3000);
    }

    // Start auto-refresh
    startAutoRefresh() {
        console.log(`🔄 Starting auto-refresh every ${this.refreshRate}ms`);
        this.refreshInterval = setInterval(() => this.fetchSensorData(), this.refreshRate);
        // Initial fetch
        this.fetchSensorData();
    }

    // Stop auto-refresh
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            console.log('⏹️ Auto-refresh stopped');
        }
    }

    // Cleanup
    destroy() {
        this.stopAutoRefresh();
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.iotManager = new IoTDeviceManager();
    window.iotManager.init();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.iotManager) {
        window.iotManager.destroy();
    }
});
