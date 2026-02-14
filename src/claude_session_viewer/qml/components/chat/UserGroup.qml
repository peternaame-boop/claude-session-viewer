import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    id: userRoot

    property string userText: ""
    property string timestamp: ""
    property var commands: []
    property var fileRefs: []

    implicitHeight: userBubble.height
    implicitWidth: parent ? parent.width : 400

    // Right-aligned bubble
    Rectangle {
        id: userBubble
        anchors.right: parent.right
        width: Math.min(contentLayout.implicitWidth + Kirigami.Units.gridUnit * 2,
                       parent.width * 0.85)
        height: contentLayout.implicitHeight + Kirigami.Units.gridUnit

        radius: Kirigami.Units.cornerRadius
        color: Kirigami.Theme.highlightColor
        opacity: 0.9

        ColumnLayout {
            id: contentLayout
            anchors {
                fill: parent
                margins: Kirigami.Units.smallSpacing * 2
            }
            spacing: Kirigami.Units.smallSpacing

            // Commands (slash commands)
            Flow {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                visible: userRoot.commands && userRoot.commands.length > 0

                Repeater {
                    model: userRoot.commands || []
                    delegate: QQC2.Label {
                        required property var modelData
                        text: modelData
                        font.family: "monospace"
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        color: Kirigami.Theme.highlightedTextColor
                        opacity: 0.8
                        padding: 2
                        background: Rectangle {
                            radius: 2
                            color: Qt.darker(Kirigami.Theme.highlightColor, 1.2)
                        }
                    }
                }
            }

            // Message text
            QQC2.Label {
                Layout.fillWidth: true
                text: userRoot.userText
                wrapMode: Text.Wrap
                textFormat: Text.MarkdownText
                color: Kirigami.Theme.highlightedTextColor
            }

            // File references
            Flow {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                visible: userRoot.fileRefs && userRoot.fileRefs.length > 0

                Repeater {
                    model: userRoot.fileRefs || []
                    delegate: QQC2.Label {
                        required property var modelData
                        text: "@" + modelData
                        font.family: "monospace"
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        color: Kirigami.Theme.highlightedTextColor
                        opacity: 0.7
                    }
                }
            }

            // Timestamp
            QQC2.Label {
                Layout.alignment: Qt.AlignRight
                text: userRoot.timestamp ? new Date(userRoot.timestamp).toLocaleTimeString(Qt.locale(), "HH:mm") : ""
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                color: Kirigami.Theme.highlightedTextColor
                opacity: 0.6
                visible: userRoot.timestamp !== ""
            }
        }
    }
}
