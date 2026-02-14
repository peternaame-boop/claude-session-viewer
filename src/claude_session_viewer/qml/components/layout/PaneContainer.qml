import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

SplitView {
    id: container
    orientation: Qt.Horizontal
    handle: Rectangle {
        implicitWidth: 4
        implicitHeight: 4
        color: SplitHandle.hovered || SplitHandle.pressed
            ? Kirigami.Theme.highlightColor
            : Kirigami.Theme.separatorColor

        // Larger hit area
        containmentMask: Item {
            x: -2
            y: 0
            width: 8
            height: parent.height
        }
    }

    property var layout: []

    function refresh() {
        layout = PaneManager.get_layout();
    }

    Connections {
        target: PaneManager
        function onLayout_changed() { container.refresh(); }
    }

    Component.onCompleted: refresh()

    Repeater {
        model: container.layout

        PaneView {
            SplitView.fillWidth: index === 0
            SplitView.minimumWidth: 360
            paneId: modelData.paneId
        }
    }
}
