import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import com.claude.viewer 1.0

RowLayout {
    id: tabBarRoot
    spacing: 0

    required property string paneId
    property var tabs: []

    signal tabActivated(string tabId)
    signal tabClosed(string tabId)
    signal tabDropped(string tabId, string fromPaneId)

    Repeater {
        model: tabBarRoot.tabs

        QQC2.AbstractButton {
            id: tabButton
            Layout.preferredHeight: 32
            Layout.minimumWidth: 80
            Layout.maximumWidth: 200
            Layout.fillWidth: true

            required property int index
            property string tabId: modelData.tabId || ""
            property string tabTitle: modelData.title || ""
            property bool isActive: modelData.active || false

            background: Rectangle {
                color: tabButton.isActive
                    ? Kirigami.Theme.backgroundColor
                    : tabButton.hovered
                        ? Kirigami.Theme.hoverColor
                        : "transparent"
                border.width: tabButton.isActive ? 0 : 0
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 2
                    color: Kirigami.Theme.highlightColor
                    visible: tabButton.isActive
                }
            }

            contentItem: RowLayout {
                spacing: 4

                QQC2.Label {
                    text: tabButton.tabTitle
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: tabButton.isActive ? 1.0 : 0.7
                }

                QQC2.ToolButton {
                    Layout.preferredWidth: 16
                    Layout.preferredHeight: 16
                    icon.name: "window-close"
                    icon.width: 12
                    icon.height: 12
                    onClicked: tabBarRoot.tabClosed(tabButton.tabId)
                    opacity: tabButton.hovered || tabButton.isActive ? 1.0 : 0.0
                }
            }

            onClicked: tabBarRoot.tabActivated(tabButton.tabId)

            // Drag support
            Drag.active: dragHandler.active
            Drag.hotSpot.x: width / 2
            Drag.hotSpot.y: height / 2
            Drag.mimeData: ({ "text/tab-id": tabButton.tabId, "text/pane-id": tabBarRoot.paneId })

            DragHandler {
                id: dragHandler
                target: null
            }
        }
    }

    // Drop area for receiving tabs from other panes
    DropArea {
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumWidth: 20
        keys: ["text/tab-id"]

        onDropped: function(drop) {
            let tabId = drop.getDataAsString("text/tab-id");
            let fromPaneId = drop.getDataAsString("text/pane-id");
            if (fromPaneId !== tabBarRoot.paneId) {
                tabBarRoot.tabDropped(tabId, fromPaneId);
            }
        }

        Rectangle {
            anchors.fill: parent
            color: Kirigami.Theme.highlightColor
            opacity: parent.containsDrag ? 0.2 : 0
        }
    }
}
