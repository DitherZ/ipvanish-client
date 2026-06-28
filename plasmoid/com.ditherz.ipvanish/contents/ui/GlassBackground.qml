import QtQuick

Item {
    id: glassRoot
    anchors.fill: parent

    property bool isIdle: false
    property real contentOpacity: 1.0

    Behavior on contentOpacity {
        NumberAnimation { duration: 500; easing.type: Easing.InOutCubic }
    }

    onIsIdleChanged: {
        contentOpacity = isIdle ? 0.12 : 1.0
    }

    // ── Layer 1: deep translucent base ────────────────────────────────────────
    Rectangle {
        id: baseLayer
        anchors.fill: parent
        radius: 14
        color: Qt.rgba(0.04, 0.04, 0.09, 0.78)

        Behavior on opacity { NumberAnimation { duration: 500 } }
    }

    // ── Layer 2: subtle noise/grain texture via gradient shimmer ─────────────
    Rectangle {
        anchors.fill: parent
        radius: 14
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0;  color: Qt.rgba(1, 1, 1, 0.06) }
            GradientStop { position: 0.35; color: Qt.rgba(1, 1, 1, 0.01) }
            GradientStop { position: 1.0;  color: Qt.rgba(0, 0, 0, 0.12) }
        }
    }

    // ── Layer 3: top highlight edge (glass refraction feel) ──────────────────
    Rectangle {
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: 1
        radius: 14
        color: Qt.rgba(1, 1, 1, 0.18)
    }

    // ── Layer 4: border glow ──────────────────────────────────────────────────
    Rectangle {
        anchors.fill: parent
        radius: 14
        color: "transparent"
        border.width: 1
        border.color: Qt.rgba(0.0, 0.83, 1.0, 0.20)
    }

    // ── Layer 5: corner accent dot (top-right) ────────────────────────────────
    Rectangle {
        anchors { right: parent.right; top: parent.top; margins: 10 }
        width: 4; height: 4; radius: 2
        color: Qt.rgba(0.0, 0.83, 1.0, 0.5)
        visible: !glassRoot.isIdle
        Behavior on opacity { NumberAnimation { duration: 300 } }
        opacity: glassRoot.contentOpacity > 0.5 ? 1.0 : 0.0
    }
}
