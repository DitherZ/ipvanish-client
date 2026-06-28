import QtQuick
import QtQuick.Layouts

Item {
    anchors.fill: parent

    RowLayout {
        anchors.fill: parent
        spacing: 8

        // Status dot
        Item {
            width: 10; height: 10
            Layout.alignment: Qt.AlignVCenter

            Rectangle {
                anchors.centerIn: parent
                width: 6; height: 6; radius: 3
                color: root.vpnConnected ? "#00d4ff" : "#ff4646"
                Behavior on color { ColorAnimation { duration: 400 } }
            }
        }

        // Public IP
        Text {
            text:             root.vpnPublicIP
            color:            "#ffffff"
            font.pixelSize:   11
            font.weight:      Font.Medium
            font.letterSpacing: 0.2
            elide:            Text.ElideRight
            Layout.maximumWidth: 108
            Layout.alignment: Qt.AlignVCenter
        }

        // separator
        Rectangle { width: 1; height: 14; color: Qt.rgba(1,1,1,0.12); Layout.alignment: Qt.AlignVCenter }

        // Server location — clickable
        Text {
            text:             root.showHostname ? root.vpnServerHost : root.vpnServerLocation
            color:            Qt.rgba(0, 0.83, 1, 0.75)
            font.pixelSize:   10
            elide:            Text.ElideRight
            Layout.maximumWidth: 110
            Layout.alignment: Qt.AlignVCenter

            MouseArea {
                anchors.fill: parent
                cursorShape:  Qt.PointingHandCursor
                onClicked:    { root.showHostname = !root.showHostname; root.wake() }
            }
        }

        Item { Layout.fillWidth: true }

        // separator
        Rectangle { width: 1; height: 14; color: Qt.rgba(1,1,1,0.12); Layout.alignment: Qt.AlignVCenter }

        // DN + UP stacked compact
        ColumnLayout {
            spacing: 1
            Layout.alignment: Qt.AlignVCenter

            SpeedBars {
                width:   120
                height:  18
                history:    root.vpnDownHistory.filter(function(_, i){ return i % 2 === 0 })
                barColor:   "#00d4ff"
                label:      "▼"
                speedValue: root.formatSpeed(root.vpnDownBps)

                MouseArea {
                    anchors.fill: parent
                    cursorShape:  Qt.PointingHandCursor
                    onClicked:    { root.showBits = !root.showBits; root.wake() }
                }
            }

            SpeedBars {
                width:   120
                height:  18
                history:    root.vpnUpHistory.filter(function(_, i){ return i % 2 === 0 })
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
