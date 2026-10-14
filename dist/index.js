// Alienware Control - Decky Loader Plugin
const manifest = { "name": "Alienware-Control" };
const API_VERSION = 2;
const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;

let api;
try {
    api = internalAPIConnection.connect(API_VERSION, manifest.name);
} catch {
    api = internalAPIConnection.connect(1, manifest.name);
}
const call = api.call;

function AlienIcon() {
    return window.SP_REACT.createElement("svg", {
        viewBox: "0 0 24 24",
        width: "1.2em",
        height: "1.2em",
        fill: "currentColor"
    }, window.SP_REACT.createElement("path", {
        d: "M12 2C7.03 2 3 6.03 3 11c0 3.86 2.45 7.15 5.92 8.41L12 22l3.08-2.59C18.55 18.15 21 14.86 21 11c0-4.97-4.03-9-9-9zm-3 11.5c-1.38 0-2.5-1.12-2.5-2.5S7.62 8.5 9 8.5s2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5zm6 0c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"
    }));
}

const PROFILE_LABELS = {
    "performance": "Performance (Full Speed)",
    "balanced-performance": "Balanced Performance (Gaming)",
    "balanced": "Balanced",
    "quiet": "Quiet (Low Fan Noise)",
    "cool": "Cool (Aggressive Fans)",
    "power-saver": "Power Saver (Eco)",
    "custom": "Custom"
};

const Content = () => {
    const [status, setStatus] = window.SP_REACT.useState({
        turbo: false,
        profile: "balanced",
        choices: ["cool", "quiet", "balanced", "balanced-performance", "performance"],
        max_freq: "3.00 GHz",
        power_saver: false,
        power_profile: "balanced"
    });
    const [loading, setLoading] = window.SP_REACT.useState(false);
    const [msg, setMsg] = window.SP_REACT.useState("");

    const fetchStatus = async () => {
        try {
            const res = await call("get_status");
            if (res) {
                setStatus(res);
            }
        } catch (e) {
            console.error("[Alienware-Control] fetchStatus error:", e);
        }
    };

    window.SP_REACT.useEffect(() => {
        fetchStatus();
        const timer = setInterval(fetchStatus, 3000);
        return () => clearInterval(timer);
    }, []);

    const handleTurbo = async (val) => {
        setLoading(true);
        try {
            const res = await call("set_turbo", val);
            if (res) {
                setStatus(res);
                setMsg(val ? "Turbo Boost ENABLED (~5.47 GHz)" : "Turbo Boost DISABLED (3.00 GHz base clock)");
                setTimeout(() => setMsg(""), 3000);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handlePowerSaver = async (val) => {
        setLoading(true);
        try {
            const res = await call("set_power_saver", val);
            if (res) {
                setStatus(res);
                setMsg(val ? "Power Saver ENABLED (Eco / Cool mode active)" : "Power Saver DISABLED (Balanced mode active)");
                setTimeout(() => setMsg(""), 3000);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleProfile = async (prof) => {
        setLoading(true);
        try {
            const res = await call("set_profile", prof);
            if (res) {
                setStatus(res);
                setMsg(`Profile set: ${prof}`);
                setTimeout(() => setMsg(""), 3000);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const dropdownOptions = (status.choices || []).map((ch) => ({
        label: PROFILE_LABELS[ch] || ch,
        data: ch
    }));

    return window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        // Status notice banner
        msg && window.SP_REACT.createElement(window.DFL.PanelSectionRow, null,
            window.SP_REACT.createElement("div", {
                style: {
                    padding: "8px 12px",
                    background: "rgba(0, 150, 255, 0.2)",
                    borderRadius: "4px",
                    fontSize: "12px",
                    color: "#66c0f4",
                    textAlign: "center"
                }
            }, msg)
        ),

        // Controls Section
        window.SP_REACT.createElement(window.DFL.PanelSection, { title: "Hardware Power & Thermals" },
            // Power Saver Toggle
            window.SP_REACT.createElement(window.DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(window.DFL.ToggleField, {
                    label: "Power Saver (Eco Mode)",
                    description: status.power_saver
                        ? "Enabled (Limits EPP power & forces quiet thermals)"
                        : "Disabled (Standard power delivery)",
                    checked: !!status.power_saver,
                    disabled: loading,
                    onChange: (checked) => handlePowerSaver(checked)
                })
            ),

            // Turbo Switch
            window.SP_REACT.createElement(window.DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(window.DFL.ToggleField, {
                    label: "CPU Turbo Boost",
                    description: status.turbo
                        ? "Enabled (Unlocks up to 5.47 GHz boost)"
                        : "Disabled (Capped at 3.00 GHz base clock)",
                    checked: !!status.turbo,
                    disabled: loading,
                    onChange: (checked) => handleTurbo(checked)
                })
            ),

            // Power Profile Dropdown
            window.SP_REACT.createElement(window.DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(window.DFL.DropdownItem, {
                    label: "ACPI Platform Profile",
                    description: "Active mode: " + status.profile + " (System: " + (status.power_profile || "balanced") + ")",
                    rgOptions: dropdownOptions,
                    selectedOption: status.profile,
                    onChange: (item) => {
                        const target = item && item.data ? item.data : item;
                        if (target) handleProfile(target);
                    }
                })
            ),

            // Current Max Frequency Field
            window.SP_REACT.createElement(window.DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(window.DFL.Field, {
                    label: "Current CPU Clock Ceiling",
                    description: status.turbo ? "Full Dynamic Boost Active" : "Thermal Safe Mode Active"
                }, status.max_freq)
            )
        ),

        // Quick Preset Buttons
        window.SP_REACT.createElement(window.DFL.PanelSection, { title: "Quick Thermal Presets" },
            window.SP_REACT.createElement(window.DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(window.DFL.ButtonItem, {
                    layout: "below",
                    onClick: async () => {
                        await handlePowerSaver(true);
                        await handleTurbo(false);
                    }
                }, "Eco / Power Saver (Coolest & Quiet)")
            ),
            window.SP_REACT.createElement(window.DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(window.DFL.ButtonItem, {
                    layout: "below",
                    onClick: async () => {
                        await handlePowerSaver(false);
                        await handleProfile("balanced");
                        await handleTurbo(false);
                    }
                }, "Balanced Mode (Daily Use)")
            ),
            window.SP_REACT.createElement(window.DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(window.DFL.ButtonItem, {
                    layout: "below",
                    onClick: async () => {
                        await handlePowerSaver(false);
                        await handleProfile("performance");
                        await handleTurbo(true);
                    }
                }, "Max Performance / G-Mode (Turbo ON)")
            ),
            window.SP_REACT.createElement(window.DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(window.DFL.ButtonItem, {
                    layout: "below",
                    onClick: async () => {
                        await handleProfile("quiet");
                        await handleTurbo(false);
                    }
                }, "Quiet Acoustic Mode (Low Fans)")
            )
        )
    );
};

var index = window.DFL.definePlugin(() => {
    return {
        title: window.SP_REACT.createElement("div", { className: window.DFL.staticClasses.Title }, "Alienware Control"),
        content: window.SP_REACT.createElement(Content, null),
        icon: window.SP_REACT.createElement(AlienIcon, null),
        onDismount: () => {}
    };
});

export { index as default };
