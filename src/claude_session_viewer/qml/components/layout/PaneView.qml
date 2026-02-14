import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "../layout" as Layout

ColumnLayout {
    id: paneRoot
    spacing: 0

    required property string paneId
    property var tabs: []
    property string activeSessionId: ""
    property bool isActivePane: PaneManager.activePaneId === paneId

    function refresh() {
        tabs = PaneManager.get_tabs(paneId);
        activeSessionId = PaneManager.get_active_session_id(paneId);
    }

    Connections {
        target: PaneManager
        function onLayout_changed() { paneRoot.refresh(); }
        function onActive_tab_changed(pid) {
            if (pid === paneRoot.paneId) paneRoot.refresh();
        }
    }

    Component.onCompleted: refresh()

    // Tab bar
    Layout.TabBarView {
        Layout.fillWidth: true
        Layout.preferredHeight: tabs.length > 0 ? 32 : 0
        visible: tabs.length > 0
        paneId: paneRoot.paneId
        tabs: paneRoot.tabs

        onTabActivated: function(tabId) {
            PaneManager.activate_tab(paneRoot.paneId, tabId);
        }
        onTabClosed: function(tabId) {
            PaneManager.close_tab(paneRoot.paneId, tabId);
        }
        onTabDropped: function(tabId, fromPaneId) {
            PaneManager.move_tab(fromPaneId, tabId, paneRoot.paneId);
        }
    }

    // Separator
    Kirigami.Separator {
        Layout.fillWidth: true
        visible: tabs.length > 0
    }

    // Content area
    Item {
        Layout.fillWidth: true
        Layout.fillHeight: true

        // Active session chat
        ChatHistoryView {
            anchors.fill: parent
            visible: paneRoot.activeSessionId !== ""
        }

        // Empty pane state
        Kirigami.PlaceholderMessage {
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.gridUnit * 4
            visible: paneRoot.activeSessionId === ""
            text: tabs.length === 0
                ? "Open a session to start"
                : "Select a tab"
            icon.name: "view-conversation-balloon"
        }
    }

    // Click to activate pane
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton
        propagateComposedEvents: true
        onPressed: function(mouse) {
            PaneManager.set_active_pane(paneRoot.paneId);
            mouse.accepted = false;
        }
    }

    // Active pane indicator
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 2
        color: Kirigami.Theme.highlightColor
        visible: paneRoot.isActivePane && PaneManager.paneCount > 1
    }
}
