import QtQuick
import QtQuick.Layouts

Item {
    anchors.fill: parent

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Status dot + IP centered ──────────────────────────────────────────
        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 2
            spacing: 6

            Item {
                width: 12; height: 12
                Layout.alignment: Qt.AlignVCenter

                Rectangle {
                    anchors.centerIn: parent
                    width: 6; height: 6; radius: 3
                    color: root.vpnConnected ? "#00d4ff" : "#ff4646"
                    Behavior on color { ColorAnimation { duration: 400 } }
                }
            }

            Text {
                text:           root.vpnPublicIP
                color:          "#ffffff"
                font.pixelSize: 12
                font.weight:    Font.Medium
                font.letterSpacing: 0.3
                elide:          Text.ElideRight
                Layout.alignment: Qt.AlignVCenter
            }
        }

        Item { height: 4 }

        // ── Server location (clickable) ───────────────────────────────────────
        Text {
            Layout.fillWidth:    true
            Layout.alignment:    Qt.AlignHCenter
            horizontalAlignment: Text.AlignHCenter
            text:                root.showHostname ? root.vpnServerHost : root.vpnServerLocation
            color:               Qt.rgba(0, 0.83, 1, 0.75)
            font.pixelSize:      10
            font.letterSpacing:  0.2
            elide:               Text.ElideRight

            Behavior on opacity { NumberAnimation { duration: 200 } }

            MouseArea {
                anchors.fill: parent
                cursorShape:  Qt.PointingHandCursor
                onClicked:    { root.showHostname = !root.showHostname; root.wake() }
            }
        }

        // ── Gradient divider ──────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: 8
            Layout.bottomMargin: 8
            height: 1
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: Qt.rgba(0, 0.83, 1, 0.0) }
                GradientStop { position: 0.5; color: Qt.rgba(0, 0.83, 1, 0.3) }
                GradientStop { position: 1.0; color: Qt.rgba(0, 0.83, 1, 0.0) }
            }
        }

        // ── DN bars ───────────────────────────────────────────────────────────
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

        Item { height: 6 }

        // ── UP bars ───────────────────────────────────────────────────────────
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
