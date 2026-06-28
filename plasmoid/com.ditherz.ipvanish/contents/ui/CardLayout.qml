import QtQuick
import QtQuick.Layouts

Item {
    anchors.fill: parent

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Row 1: status indicator + IP ─────────────────────────────────────
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 2
            spacing: 7

            // Connection dot with pulse ring
            Item {
                width: 14; height: 14
                Layout.alignment: Qt.AlignVCenter

                // outer pulse ring — opacity only, no scale (prevents overflow)
                Rectangle {
                    id: pulseRing
                    anchors.centerIn: parent
                    width: 14; height: 14; radius: 7
                    color: "transparent"
                    border.width: 1
                    border.color: root.vpnConnected ? Qt.rgba(0, 0.83, 1, 0.5) : Qt.rgba(1, 0.27, 0.27, 0.5)
                    opacity: 0.0

                    SequentialAnimation on opacity {
                        running: root.vpnConnected
                        loops:   Animation.Infinite
                        NumberAnimation { to: 0.8; duration: 900; easing.type: Easing.OutQuad }
                        NumberAnimation { to: 0.0; duration: 900; easing.type: Easing.InQuad }
                        PauseAnimation  { duration: 600 }
                    }
                }

                // inner solid dot
                Rectangle {
                    anchors.centerIn: parent
                    width: 7; height: 7; radius: 3.5
                    color: root.vpnConnected ? "#00d4ff" : "#ff4646"

                    Behavior on color { ColorAnimation { duration: 400 } }
                }
            }

            // Public IP
            Text {
                text:           root.vpnPublicIP
                color:          "#ffffff"
                font.pixelSize: 13
                font.weight:    Font.Medium
                font.letterSpacing: 0.3
                elide:          Text.ElideRight
                Layout.fillWidth:  true
                Layout.alignment: Qt.AlignVCenter
            }

            // Shield icon placeholder — VPN branding mark
            Text {
                text:           "⬡"
                color:          root.vpnConnected ? Qt.rgba(0, 0.83, 1, 0.4) : Qt.rgba(1,1,1,0.1)
                font.pixelSize: 11
                Layout.alignment: Qt.AlignVCenter
                Behavior on color { ColorAnimation { duration: 400 } }
            }
        }

        // ── Thin divider ──────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: 5
            Layout.bottomMargin: 5
            height: 1
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: Qt.rgba(0, 0.83, 1, 0.0) }
                GradientStop { position: 0.3; color: Qt.rgba(0, 0.83, 1, 0.25) }
                GradientStop { position: 0.7; color: Qt.rgba(0, 0.83, 1, 0.25) }
                GradientStop { position: 1.0; color: Qt.rgba(0, 0.83, 1, 0.0) }
            }
        }

        // ── Row 2: server location (clickable) ────────────────────────────────
        RowLayout {
            Layout.fillWidth: true
            spacing: 5

            Text {
                text:           "via"
                color:          Qt.rgba(1, 1, 1, 0.25)
                font.pixelSize: 9
                font.letterSpacing: 0.5
                Layout.alignment: Qt.AlignVCenter
            }

            Text {
                id: locationText
                Layout.fillWidth: true
                text:             root.showHostname ? root.vpnServerHost : root.vpnServerLocation
                color:            "#00d4ff"
                font.pixelSize:   11
                font.letterSpacing: 0.2
                elide:            Text.ElideRight
                Layout.alignment: Qt.AlignVCenter

                Behavior on opacity { NumberAnimation { duration: 200 } }

                MouseArea {
                    anchors.fill: parent
                    cursorShape:  Qt.PointingHandCursor
                    onClicked:    { root.showHostname = !root.showHostname; root.wake() }
                }
            }
        }

        Item { Layout.fillHeight: true; Layout.minimumHeight: 6 }

        // ── Row 3: speed bars side by side ────────────────────────────────────
        RowLayout {
            Layout.fillWidth:  true
            Layout.fillHeight: true
            spacing: 10

            SpeedBars {
                Layout.fillWidth:  true
                Layout.fillHeight: true
                history:    root.vpnDownHistory
                barColor:   "#00d4ff"
                label:      "▼"
                speedValue: root.formatSpeed(root.vpnDownBps)

                MouseArea {
                    anchors.fill: parent
                    cursorShape:  Qt.PointingHandCursor
                    onClicked:    { root.showBits = !root.showBits; root.wake() }
                }
            }

            // vertical separator
            Rectangle {
                width: 1
                Layout.fillHeight: true
                color: Qt.rgba(1, 1, 1, 0.08)
            }

            SpeedBars {
                Layout.fillWidth:  true
                Layout.fillHeight: true
                history:    root.vpnUpHistory
                barColor:   "#ff6b35"
                label:      "▲"
                speedValue: root.formatSpeed(root.vpnUpBps)

                MouseArea {
                    anchors.fill: parent
                    cursorShape:  Qt.PointingHandCursor
                    onClicked:    { root.showBits = !root.showBits; root.wake() }
                }
            }
        }
    }
}
