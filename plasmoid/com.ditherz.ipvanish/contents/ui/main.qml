import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.plasma.workspace.dbus as WorkspaceDbus

PlasmoidItem {
    id: root

    // Default / preferred size — user can resize freely on desktop
    implicitWidth:  320
    implicitHeight: 160

    // ── shared VPN state ─────────────────────────────────────────────────────
    property string vpnPublicIP:       "—"
    property string vpnServerLocation: "Not connected"
    property string vpnServerHost:     ""
    property bool   vpnConnected:      false
    property real   vpnDownBps:        0.0
    property real   vpnUpBps:          0.0
    property var    vpnDownHistory:    Array(20).fill(0.01)
    property var    vpnUpHistory:      Array(20).fill(0.01)

    // ── interaction state ────────────────────────────────────────────────────
    property bool showHostname: false
    property bool showBits:     false
    property bool isIdle:       false

    // ── layout state ─────────────────────────────────────────────────────────
    property string currentLayout: "card"

    function updateLayout() {
        if (root.height > root.width * 1.1) {
            currentLayout = "sidebar"
        } else if (root.height < 120) {
            currentLayout = "pill"
        } else {
            currentLayout = "card"
        }
    }

    onWidthChanged:        updateLayout()
    onHeightChanged:       updateLayout()
    Component.onCompleted: updateLayout()

    // ── idle timer ────────────────────────────────────────────────────────────
    Timer {
        id: idleTimer
        interval: 4000
        repeat:   false
        running:  true
        onTriggered: { root.isIdle = true }
    }

    function wake() {
        root.isIdle = false
        idleTimer.restart()
    }

    // ── speed formatter ───────────────────────────────────────────────────────
    function formatSpeed(bps) {
        if (root.showBits) {
            var bits = bps * 8
            if (bits >= 1000000) return (bits / 1000000).toFixed(1) + " Mb/s"
            if (bits >= 1000)    return (bits / 1000).toFixed(1) + " kb/s"
            return bits.toFixed(0) + " b/s"
        }
        if (bps >= 1048576) return (bps / 1048576).toFixed(1) + " MB/s"
        if (bps >= 1024)    return (bps / 1024).toFixed(1) + " KB/s"
        return bps.toFixed(0) + " B/s"
    }

    // ── data source: poll JSON every second ───────────────────────────────────
    Plasma5Support.DataSource {
        id: jsonSource
        engine:           "executable"
        connectedSources: ["cat /run/user/1000/ipvanish-widget.json 2>/dev/null"]
        interval:         1000

        onNewData: function(source, data) {
            var raw = data["stdout"]
            if (!raw || raw.length === 0) return
            try {
                var obj = JSON.parse(raw)
                var prevIP        = root.vpnPublicIP
                var prevConnected = root.vpnConnected

                root.vpnPublicIP       = obj.publicIP       || "—"
                root.vpnServerLocation = obj.serverLocation || "Not connected"
                root.vpnServerHost     = obj.serverHost     || ""
                root.vpnConnected      = obj.connected      || false
                root.vpnDownBps        = obj.downBps        || 0.0
                root.vpnUpBps          = obj.upBps          || 0.0
                root.vpnDownHistory    = obj.downHistory    || Array(20).fill(0.01)
                root.vpnUpHistory      = obj.upHistory      || Array(20).fill(0.01)

                if (prevIP !== root.vpnPublicIP || prevConnected !== root.vpnConnected) {
                    root.wake()
                }
            } catch(e) {}
        }
    }

    // ── D-Bus service watcher ─────────────────────────────────────────────────
    WorkspaceDbus.DBusServiceWatcher {
        id: daemonWatcher
        watchedService: "com.ditherz.IPVanishWidget"
        busType: WorkspaceDbus.BusType.Session
        onRegisteredChanged: {
            if (!registered) {
                console.log("[ipvanish] daemon D-Bus service disappeared")
            }
        }
    }

    // ── root mouse area (wake on hover/click) ─────────────────────────────────
    MouseArea {
        anchors.fill:            parent
        hoverEnabled:            true
        propagateComposedEvents: true
        onEntered:               root.wake()
        onPressed: function(mouse) { mouse.accepted = false }
    }

    // ── background ────────────────────────────────────────────────────────────
    GlassBackground {
        id: background
        isIdle: root.isIdle
    }

    // ── content with smooth idle fade ─────────────────────────────────────────
    Item {
        id: contentWrapper
        anchors.fill:    parent
        anchors.margins: 12
        opacity: background.contentOpacity

        Loader {
            id: layoutLoader
            anchors.fill: parent
            source: {
                if (root.currentLayout === "sidebar") return "SidebarLayout.qml"
                if (root.currentLayout === "pill")    return "PillLayout.qml"
                return "CardLayout.qml"
            }
        }
    }
}
