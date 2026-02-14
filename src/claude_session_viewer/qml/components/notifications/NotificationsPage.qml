import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: notifPage
    title: "Notifications"

    property var notificationHistory: []
    property var triggers: []

    Component.onCompleted: refresh()

    function refresh() {
        notificationHistory = NotificationManager.get_history();
        triggers = NotificationManager.get_triggers();
    }

    Connections {
        target: NotificationManager
        function onHistory_changed() { notifPage.notificationHistory = NotificationManager.get_history(); }
        function onTriggers_changed() { notifPage.triggers = NotificationManager.get_triggers(); }
    }

    actions: [
        Kirigami.Action {
            text: "Clear All"
            icon.name: "edit-clear-history"
            onTriggered: NotificationManager.clear_history()
        },
        Kirigami.Action {
            text: "Add Trigger"
            icon.name: "list-add"
            onTriggered: addTriggerDialog.open()
        }
    ]

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        // --- Notification History ---
        Kirigami.Heading {
            text: "History"
            level: 3
        }

        Kirigami.PlaceholderMessage {
            Layout.fillWidth: true
            visible: notifPage.notificationHistory.length === 0
            text: "No notifications yet"
            icon.name: "notifications"
        }

        Repeater {
            model: notifPage.notificationHistory

            NotificationRow {
                Layout.fillWidth: true
                triggerName: modelData.trigger_name || ""
                triggerColor: modelData.trigger_color || "#3b82f6"
                matchedText: modelData.matched_text || ""
                timestamp: modelData.timestamp || ""
            }
        }

        // --- Trigger Editor ---
        Kirigami.Separator {
            Layout.fillWidth: true
            visible: notifPage.triggers.length > 0
        }

        Kirigami.Heading {
            text: "Triggers"
            level: 3
        }

        Repeater {
            model: notifPage.triggers

            QQC2.ItemDelegate {
                Layout.fillWidth: true

                contentItem: RowLayout {
                    spacing: Kirigami.Units.smallSpacing

                    // Color indicator
                    Rectangle {
                        width: 12
                        height: 12
                        radius: 6
                        color: modelData.color || "#3b82f6"
                    }

                    // Name and pattern
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        QQC2.Label {
                            text: modelData.name || ""
                            font.weight: Font.Bold
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        QQC2.Label {
                            text: modelData.pattern
                                ? "Pattern: " + modelData.pattern
                                : modelData.tokenThreshold > 0
                                    ? "Token threshold: " + modelData.tokenThreshold
                                    : "No pattern"
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                            opacity: 0.6
                            Layout.fillWidth: true
                        }
                    }

                    // Enabled switch
                    QQC2.Switch {
                        checked: modelData.enabled
                        onToggled: {
                            NotificationManager.set_trigger_enabled(modelData.id, checked);
                        }
                    }

                    // Remove button (only for non-builtin)
                    QQC2.ToolButton {
                        icon.name: "edit-delete"
                        visible: !modelData.id.startsWith("builtin-")
                        onClicked: NotificationManager.remove_trigger(modelData.id)
                    }
                }
            }
        }
    }

    // --- Add Trigger Dialog ---
    QQC2.Dialog {
        id: addTriggerDialog
        title: "Add Notification Trigger"
        standardButtons: QQC2.Dialog.Ok | QQC2.Dialog.Cancel
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: 400

        onAccepted: {
            if (triggerNameField.text && triggerPatternField.text) {
                NotificationManager.add_trigger(
                    triggerNameField.text,
                    triggerPatternField.text,
                    triggerColorField.text || "#3b82f6"
                );
                triggerNameField.text = "";
                triggerPatternField.text = "";
                triggerColorField.text = "#3b82f6";
            }
        }

        contentItem: ColumnLayout {
            spacing: Kirigami.Units.smallSpacing

            QQC2.Label { text: "Name:" }
            QQC2.TextField {
                id: triggerNameField
                Layout.fillWidth: true
                placeholderText: "Trigger name"
            }

            QQC2.Label { text: "Regex Pattern:" }
            QQC2.TextField {
                id: triggerPatternField
                Layout.fillWidth: true
                placeholderText: "e.g. \\.env|password"
            }

            QQC2.Label { text: "Color:" }
            QQC2.TextField {
                id: triggerColorField
                Layout.fillWidth: true
                text: "#3b82f6"
                placeholderText: "#hex color"
            }
        }
    }
}
