import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

QQC2.ItemDelegate {
    id: notifRow

    required property string triggerName
    required property string triggerColor
    required property string matchedText
    required property string timestamp

    contentItem: RowLayout {
        spacing: Kirigami.Units.smallSpacing

        // Colored left indicator
        Rectangle {
            width: 4
            Layout.fillHeight: true
            color: notifRow.triggerColor
            radius: 2
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            // Trigger name
            QQC2.Label {
                text: notifRow.triggerName
                font.weight: Font.Bold
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            // Matched text
            QQC2.Label {
                text: notifRow.matchedText
                elide: Text.ElideRight
                Layout.fillWidth: true
                opacity: 0.8
                font.pointSize: Kirigami.Theme.smallFont.pointSize
            }

            // Timestamp
            QQC2.Label {
                text: notifRow.timestamp
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                opacity: 0.5
            }
        }
    }
}
