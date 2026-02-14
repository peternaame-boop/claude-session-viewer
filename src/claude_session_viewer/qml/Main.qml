import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "components/search" as Search
import "components/notifications" as Notifications
import "components/settings" as Settings
import "components/layout" as AppLayout
import "components/common" as Common

Kirigami.ApplicationWindow {
    id: root

    title: "Claude Session Viewer"
    width: 1200
    height: 800
    minimumWidth: 600
    minimumHeight: 400

    // --- Keyboard Shortcuts ---
    Shortcut { sequence: "Ctrl+K"; onActivated: commandPalette.open() }
    Shortcut { sequence: "Ctrl+B"; onActivated: drawer.collapsed = !drawer.collapsed }
    Shortcut { sequence: "Ctrl+W"; onActivated: PaneManager.close_active_tab() }
    Shortcut { sequence: "Ctrl+Tab"; onActivated: PaneManager.next_tab() }
    Shortcut { sequence: "Ctrl+Shift+Tab"; onActivated: PaneManager.prev_tab() }
    Shortcut { sequence: "Ctrl+\\"; onActivated: PaneManager.split_pane() }
    Shortcut { sequence: "Ctrl+R"; onActivated: SessionManager.refresh_session(SessionManager.currentSessionId) }
    Shortcut { sequence: "F5"; onActivated: SessionManager.scan_projects() }
    Shortcut { sequence: "Ctrl+1"; onActivated: PaneManager.activate_tab_by_index(0) }
    Shortcut { sequence: "Ctrl+2"; onActivated: PaneManager.activate_tab_by_index(1) }
    Shortcut { sequence: "Ctrl+3"; onActivated: PaneManager.activate_tab_by_index(2) }
    Shortcut { sequence: "Ctrl+4"; onActivated: PaneManager.activate_tab_by_index(3) }
    Shortcut { sequence: "Ctrl+5"; onActivated: PaneManager.activate_tab_by_index(4) }
    Shortcut { sequence: "Ctrl+6"; onActivated: PaneManager.activate_tab_by_index(5) }
    Shortcut { sequence: "Ctrl+7"; onActivated: PaneManager.activate_tab_by_index(6) }
    Shortcut { sequence: "Ctrl+8"; onActivated: PaneManager.activate_tab_by_index(7) }
    Shortcut { sequence: "Ctrl+9"; onActivated: PaneManager.activate_tab_by_index(8) }

    // --- Popups ---
    Search.CommandPalette {
        id: commandPalette
    }

    // --- Sidebar ---
    globalDrawer: Kirigami.GlobalDrawer {
        id: drawer
        title: "Sessions"
        modal: false
        collapsible: true
        collapsed: false
        width: 320

        header: ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            // Toolbar row
            RowLayout {
                Layout.fillWidth: true
                Layout.margins: Kirigami.Units.smallSpacing

                QQC2.ToolButton {
                    icon.name: "search"
                    onClicked: commandPalette.open()
                    QQC2.ToolTip.text: "Search (Ctrl+K)"
                    QQC2.ToolTip.visible: hovered
                }

                QQC2.ToolButton {
                    icon.name: "view-split-left-right"
                    onClicked: PaneManager.split_pane()
                    enabled: PaneManager.paneCount < 4
                    QQC2.ToolTip.text: "Split Pane (Ctrl+\\)"
                    QQC2.ToolTip.visible: hovered
                }

                Item { Layout.fillWidth: true }

                // SSH connection indicator
                QQC2.ToolButton {
                    icon.name: SshManager.connected ? "network-connect" : "network-disconnect"
                    icon.color: SshManager.connected ? Kirigami.Theme.positiveTextColor : undefined
                    onClicked: {
                        if (SshManager.connected) {
                            SshManager.disconnect_ssh();
                        } else {
                            root.pageStack.push(settingsPageComponent);
                        }
                    }
                    QQC2.ToolTip.text: SshManager.connected
                        ? "Connected to " + SshManager.currentHost + " (click to disconnect)"
                        : "SSH not connected"
                    QQC2.ToolTip.visible: hovered
                }

                QQC2.ToolButton {
                    icon.name: "notifications"
                    onClicked: root.pageStack.push(notificationsPageComponent)
                    QQC2.ToolTip.text: "Notifications"
                    QQC2.ToolTip.visible: hovered
                }

                QQC2.ToolButton {
                    icon.name: "configure"
                    onClicked: root.pageStack.push(settingsPageComponent)
                    QQC2.ToolTip.text: "Settings"
                    QQC2.ToolTip.visible: hovered
                }
            }

            // Project selector
            QQC2.ComboBox {
                id: projectSelector
                Layout.fillWidth: true
                Layout.margins: Kirigami.Units.smallSpacing
                model: ProjectModel
                textRole: "projectName"
                displayText: currentIndex >= 0 ? currentText : "Select a project..."

                onActivated: function(index) {
                    let pid = ProjectModel.get_project_id(index);
                    if (pid !== "") {
                        SessionManager.select_project(pid);
                    }
                }

                delegate: QQC2.ItemDelegate {
                    width: projectSelector.width
                    contentItem: ColumnLayout {
                        spacing: 2
                        QQC2.Label {
                            text: model.projectName
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        QQC2.Label {
                            text: model.sessionCount + " sessions"
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                            opacity: 0.7
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }

        // Session list
        QQC2.ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: sessionList
                model: SessionModel
                clip: true

                section.property: "section"
                section.delegate: Kirigami.ListSectionHeader {
                    required property string section
                    text: section
                    width: sessionList.width
                }

                delegate: QQC2.ItemDelegate {
                    id: sessionDelegate
                    width: sessionList.width
                    highlighted: model.sessionId === SessionManager.currentSessionId

                    contentItem: ColumnLayout {
                        spacing: 2

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Rectangle {
                                width: 8
                                height: 8
                                radius: 4
                                color: Kirigami.Theme.positiveTextColor
                                visible: model.isOngoing
                                Layout.alignment: Qt.AlignVCenter
                            }

                            QQC2.Label {
                                text: model.firstMessage
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                                font.weight: sessionDelegate.highlighted ? Font.Bold : Font.Normal
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            QQC2.Label {
                                text: model.relativeTime
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                opacity: 0.7
                            }

                            QQC2.Label {
                                text: "\u00b7"
                                opacity: 0.5
                                visible: model.messageCount > 0
                            }

                            QQC2.Label {
                                text: model.messageCount + " msgs"
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                opacity: 0.7
                                visible: model.messageCount > 0
                            }

                            Item { Layout.fillWidth: true }

                            QQC2.Label {
                                text: model.gitBranch
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                opacity: 0.5
                                visible: model.gitBranch !== ""
                                elide: Text.ElideMiddle
                                Layout.maximumWidth: 100
                            }
                        }
                    }

                    onClicked: {
                        SessionManager.select_session(model.sessionId);
                        PaneManager.open_tab(model.sessionId, model.firstMessage, SessionManager.currentProjectId);
                    }
                }

                Kirigami.PlaceholderMessage {
                    anchors.centerIn: parent
                    width: parent.width - Kirigami.Units.gridUnit * 4
                    visible: sessionList.count === 0 && !SessionManager.loading
                    text: projectSelector.currentIndex >= 0
                        ? "No sessions found"
                        : "Select a project to browse sessions"
                    icon.name: "folder-open"
                }
            }
        }
    }

    // --- Main content area ---
    pageStack.initialPage: Kirigami.Page {
        id: mainPage
        title: "Conversation"
        padding: 0

        QQC2.BusyIndicator {
            anchors.centerIn: parent
            running: SessionManager.loading
            visible: SessionManager.loading
        }

        ChatHistoryView {
            id: chatHistoryView
            anchors.fill: parent
            visible: !SessionManager.loading && SessionManager.currentSessionId !== ""
        }

        Kirigami.PlaceholderMessage {
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.gridUnit * 4
            visible: !SessionManager.loading && SessionManager.currentSessionId === ""
            text: "Select a session to view the conversation"
            icon.name: "view-conversation-balloon"
        }
    }

    // --- Page components (pushed onto pageStack) ---
    Component {
        id: notificationsPageComponent
        Notifications.NotificationsPage {}
    }

    Component {
        id: settingsPageComponent
        Settings.SettingsPage {}
    }
}
