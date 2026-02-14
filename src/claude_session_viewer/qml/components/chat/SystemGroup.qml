import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    id: systemRoot

    property string systemText: ""
    property string timestamp: ""

    implicitHeight: systemCard.height
    implicitWidth: parent ? parent.width : 400

    Rectangle {
        id: systemCard
        anchors.left: parent.left
        width: Math.min(systemLayout.implicitWidth + Kirigami.Units.gridUnit * 2,
                       parent.width * 0.75)
        height: systemLayout.implicitHeight + Kirigami.Units.smallSpacing * 2
        radius: Kirigami.Units.cornerRadius
        color: Kirigami.Theme.backgroundColor
        opacity: 0.7

        ColumnLayout {
            id: systemLayout
            anchors {
                fill: parent
                margins: Kirigami.Units.smallSpacing * 2
            }
            spacing: Kirigami.Units.smallSpacing

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Icon {
                    source: "dialog-information"
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: Kirigami.Units.iconSizes.small
                    opacity: 0.6
                }

                QQC2.Label {
                    text: "System"
                    font.weight: Font.Bold
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.6
                }

                Item { Layout.fillWidth: true }

                QQC2.Label {
                    text: systemRoot.timestamp ? new Date(systemRoot.timestamp).toLocaleTimeString(Qt.locale(), "HH:mm") : ""
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    opacity: 0.5
                    visible: systemRoot.timestamp !== ""
                }
            }

            QQC2.Label {
                Layout.fillWidth: true
                text: systemRoot.systemText
                wrapMode: Text.Wrap
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                opacity: 0.7
                maximumLineCount: 10
                elide: Text.ElideRight
            }
        }
    }
}
