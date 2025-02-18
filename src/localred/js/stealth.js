// Improve stealth by overriding common detection methods
(() => {
    const override = (obj, prop, value) => {
        try {
            Object.defineProperty(obj, prop, {
                value,
                writable: false,
                configurable: false
            });
        } catch (e) {}
    };

    // Override navigator properties
    override(navigator, 'webdriver', false);
    override(navigator, 'headless', false);
    
    // More realistic plugins
    const plugins = [
        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
        {name: 'Chrome PDF Viewer', filename: 'chrome-pdf-viewer', description: 'Portable Document Format'},
        {name: 'Native Client', filename: 'native-client', description: ''}
    ];
    override(navigator, 'plugins', plugins);

    // Override languages
    override(navigator, 'languages', ['en-US', 'en']);

    // Override permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' 
            ? Promise.resolve({state: Notification.permission})
            : originalQuery(parameters)
    );

    // WebGL fingerprint randomization
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        // Randomize vendor and renderer info
        const vendors = ['Google Inc.', 'Apple Inc.', 'Intel Inc.'];
        const renderers = ['ANGLE (Intel, Intel(R) Iris(TM) Graphics 6100, OpenGL 4.1)', 'ANGLE (AMD Radeon)', 'ANGLE (NVIDIA GeForce)'];
        
        if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
            return vendors[Math.floor(Math.random() * vendors.length)];
        }
        if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
            return renderers[Math.floor(Math.random() * renderers.length)];
        }
        return getParameter.apply(this, [parameter]);
    };

    // Modify chrome object
    if (window.chrome) {
        const originalChrome = window.chrome;
        override(window, 'chrome', {
            ...originalChrome,
            runtime: undefined,
            csi: () => {},
            loadTimes: () => {}
        });
    }

    // Override screen resolution
    const commonResolutions = [
        {width: 1920, height: 1080},
        {width: 1366, height: 768},
        {width: 1440, height: 900},
        {width: 1536, height: 864}
    ];
    const randomResolution = commonResolutions[Math.floor(Math.random() * commonResolutions.length)];
    override(screen, 'width', randomResolution.width);
    override(screen, 'height', randomResolution.height);

    // Add noise to canvas fingerprinting
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type) {
        const context = originalGetContext.apply(this, arguments);
        if (type === '2d') {
            const originalFillText = context.fillText;
            context.fillText = function() {
                const args = [...arguments];
                args[0] = args[0] + ' ' + Math.random().toString(36).slice(-1);
                return originalFillText.apply(this, args);
            }
        }
        return context;
    };
})();
