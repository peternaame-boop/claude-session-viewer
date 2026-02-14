import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "../common" as Common

ColumnLayout {
    id: editRoot

    property string filePath: ""
    property string oldString: ""
    property string newString: ""
    property bool replaceAll: false
    property var diffLines: []
    property string resultData: ""

    spacing: Kirigami.Units.smallSpacing

    // File path header with badges
    RowLayout {
        Layout.fillWidth: true
        spacing: Kirigami.Units.smallSpacing

        Kirigami.Icon {
            source: "document-edit"
            implicitWidth: Kirigami.Units.iconSizes.small
            implicitHeight: Kirigami.Units.iconSizes.small
            opacity: 0.7
        }

        QQC2.Label {
            text: editRoot.filePath
            font.family: "monospace"
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            elide: Text.ElideMiddle
            Layout.fillWidth: true
            opacity: 0.7
        }

        // Replace all badge
        Rectangle {
            visible: editRoot.replaceAll
            width: replaceLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
            height: replaceLabel.implicitHeight + 4
            radius: height / 2
            color: Kirigami.Theme.neutralBackgroundColor

            QQC2.Label {
                id: replaceLabel
                anchors.centerIn: parent
                text: "replace all"
                font.pointSize: Kirigami.Theme.smallFont.pointSize
            }
        }

        Common.CopyButton {
            textToCopy: editRoot.newString
        }
    }

    // Diff view
    QQC2.ScrollView {
        Layout.fillWidth: true
        Layout.maximumHeight: 400

        ListView {
            id: diffList
            model: editRoot.diffLines || []
            clip: true
            spacing: 0

            delegate: Rectangle {
                required property var modelData
                required property int index

                width: diffList.width
                height: diffLine.implicitHeight + 4
                color: {
                    switch (modelData.type) {
                        case "removed": return Qt.rgba(1, 0, 0, 0.1);
                        case "added": return Qt.rgba(0, 0.7, 0, 0.1);
                        default: return "transparent";
                    }
                }

                QQC2.Label {
                    id: diffLine
                    anchors {
                        left: parent.left
                        right: parent.right
                        leftMargin: Kirigami.Units.smallSpacing
                        rightMargin: Kirigami.Units.smallSpacing
                        verticalCenter: parent.verticalCenter
                    }
                    text: modelData.text || ""
                    font.family: "monospace"
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    wrapMode: Text.NoWrap
                    color: {
                        switch (modelData.type) {
                            case "removed": return Kirigami.Theme.negativeTextColor;
                            case "added": return Kirigami.Theme.positiveTextColor;
                            default: return Kirigami.Theme.textColor;
                        }
                    }
                    opacity: modelData.type === "context" ? 0.6 : 1.0
                }
            }

            // Fallback if no diff lines (show old -> new as plain text)
            Kirigami.PlaceholderMessage {
                anchors.centerIn: parent
                width: parent.width - Kirigami.Units.gridUnit * 4
                visible: diffList.count === 0 && editRoot.oldString === "" && editRoot.newString === ""
                text: "No changes"
                icon.name: "dialog-ok"
            }
        }
    }
}
