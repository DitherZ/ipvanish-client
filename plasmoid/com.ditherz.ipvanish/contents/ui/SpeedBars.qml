import QtQuick

Item {
    id: barsRoot

    property var    history:    Array(20).fill(0.01)
    property color  barColor:   "#00d4ff"
    property color  barColorDim: Qt.rgba(barColor.r, barColor.g, barColor.b, 0.25)
    property string label:      ""
    property string speedValue: ""

    implicitWidth:  100
    implicitHeight: 48

    // ── label row ─────────────────────────────────────────────────────────────
    Row {
        id: labelRow
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 13
        spacing: 4

        Text {
            text:           barsRoot.label
            color:          Qt.rgba(1, 1, 1, 0.35)
            font.pixelSize: 9
            font.letterSpacing: 0.8
        }
        Text {
            text:           barsRoot.speedValue
            color:          barsRoot.barColor
            font.pixelSize: 10
            font.bold:      true
            font.letterSpacing: 0.3
        }
    }

    // ── bars area ─────────────────────────────────────────────────────────────
    Item {
        id: barsArea
        anchors {
            left: parent.left; right: parent.right
            top: parent.top
            bottom: labelRow.top; bottomMargin: 3
        }

        Repeater {
            model: 20

            Item {
                id: barWrapper
                readonly property real normVal: {
                    var h = barsRoot.history
                    return (h && index < h.length) ? Math.max(0.01, h[index]) : 0.01
                }
                readonly property bool isPeak: normVal >= 0.92
                readonly property real barW: Math.max(2, (barsArea.width - 19) / 20)

                width:  barW
                height: barsArea.height
                x:      index * (barW + 1)
                y:      0

                // dim background track
                Rectangle {
                    anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter }
                    width:  parent.barW
                    height: parent.height
                    radius: parent.barW / 2
                    color:  barsRoot.barColorDim
                    opacity: 0.4
                }

                // glow backing — wider semi-transparent rect, visible on peak only
                Rectangle {
                    anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter }
                    width:   parent.barW + 4
                    height:  Math.max(parent.barW, barsArea.height * parent.normVal) + 4
                    radius:  (parent.barW + 4) / 2
                    color:   Qt.rgba(barsRoot.barColor.r, barsRoot.barColor.g, barsRoot.barColor.b, 0.22)
                    visible: barWrapper.isPeak
                }

                // active bar
                Rectangle {
                    id: activeBar
                    anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter }
                    width:  parent.barW
                    radius: parent.barW / 2

                    height: Math.max(parent.barW, barsArea.height * parent.normVal)

                    gradient: Gradient {
                        orientation: Gradient.Vertical
                        GradientStop {
                            position: 0.0
                            color: barWrapper.isPeak
                                ? Qt.rgba(1, 1, 1, 0.95)
                                : Qt.rgba(barsRoot.barColor.r,
                                          barsRoot.barColor.g,
                                          barsRoot.barColor.b, 0.95)
                        }
                        GradientStop {
                            position: 1.0
                            color: Qt.rgba(barsRoot.barColor.r,
                                           barsRoot.barColor.g,
                                           barsRoot.barColor.b, 0.4)
                        }
                    }

                    Behavior on height {
                        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
                    }
                }
            }
        }
    }
}
